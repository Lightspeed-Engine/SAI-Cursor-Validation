#!/usr/bin/env python3
"""
Precision time keeper — standalone NTP anchor + monotonic extrapolation.

Use this module anywhere you need authoritative timestamps without Redis,
master elections, or cluster coordination. Typical consumers:

- Activity correlators / audit JSONL stamping
- Single-node SigChain services in local mode
- Scripts: ``python -m precision_timekeeper``

The distributed cluster layer (``time_authority.py``) composes this class
for masters (NTP sync) and followers (broadcast anchors).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

try:
    import ntplib

    NTP_AVAILABLE = True
except ImportError:
    NTP_AVAILABLE = False

logger = logging.getLogger(__name__)


class PrecisionTimeError(Exception):
    """Base error for precision time keeper failures."""


class PrecisionTimeSyncError(PrecisionTimeError):
    """Raised when authoritative time cannot be provided."""


@dataclass
class PrecisionTimeConfig:
    """Configuration for local precision time sync."""

    ntp_servers: List[str] = field(
        default_factory=lambda: [
            "pool.ntp.org",
            "0.pool.ntp.org",
            "1.pool.ntp.org",
            "time.google.com",
            "time.cloudflare.com",
        ]
    )
    max_time_variance: float = 0.001  # 1 ms default validation window
    variance_history_size: int = 100


@dataclass
class TimeAnchor:
    """Wall-clock anchor extrapolated via ``time.monotonic()``."""

    authoritative_time: float
    monotonic_base: float
    offset: float = 0.0
    last_sync_at: float = field(default_factory=time.time)
    ntp_variance: float = float("inf")


class PrecisionTimeKeeper:
    """
    NTP-synchronized clock with monotonic extrapolation between syncs.

    Thread-safe for synchronous ``get_authoritative_time()``; async helpers
    use the same lock via ``asyncio.to_thread`` where needed.
    """

    def __init__(
        self,
        config: Optional[PrecisionTimeConfig] = None,
        *,
        on_sync: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ):
        self.config = config or PrecisionTimeConfig()
        self._on_sync = on_sync
        self._lock = Lock()
        self._anchor: Optional[TimeAnchor] = None
        self._variance_history: List[float] = []
        self._ntp_client = ntplib.NTPClient() if NTP_AVAILABLE else None

    # ------------------------------------------------------------------ anchor

    def apply_anchor(
        self,
        authoritative_time: float,
        offset: float = 0.0,
        *,
        variance_sample: Optional[float] = None,
        last_sync_at: Optional[float] = None,
    ) -> None:
        """Set or refresh the time anchor (NTP sample or master broadcast)."""
        with self._lock:
            variance = self._anchor.ntp_variance if self._anchor else float("inf")
            if variance_sample is not None:
                self._record_variance(variance_sample)
                variance = self._average_variance()

            self._anchor = TimeAnchor(
                authoritative_time=authoritative_time,
                monotonic_base=time.monotonic(),
                offset=offset,
                last_sync_at=last_sync_at if last_sync_at is not None else time.time(),
                ntp_variance=variance,
            )

    def clear_anchor(self) -> None:
        with self._lock:
            self._anchor = None

    def is_synced(self) -> bool:
        with self._lock:
            return self._anchor is not None

    def is_stale(self, max_age_seconds: float) -> bool:
        with self._lock:
            if not self._anchor:
                return True
            return (time.time() - self._anchor.last_sync_at) > max_age_seconds

    @property
    def ntp_variance(self) -> float:
        with self._lock:
            if self._anchor:
                return self._anchor.ntp_variance
            return float("inf")

    @property
    def time_offset(self) -> float:
        with self._lock:
            return self._anchor.offset if self._anchor else 0.0

    @property
    def last_sync_at(self) -> Optional[float]:
        with self._lock:
            return self._anchor.last_sync_at if self._anchor else None

    # ------------------------------------------------------------------ clock

    def extrapolate_authoritative_time(self) -> float:
        """Return current authoritative time from the anchor + monotonic drift."""
        with self._lock:
            if not self._anchor:
                raise PrecisionTimeSyncError("No time anchor — sync required")
            elapsed = time.monotonic() - self._anchor.monotonic_base
            return self._anchor.authoritative_time + elapsed

    def get_authoritative_time(self) -> float:
        """Alias for :meth:`extrapolate_authoritative_time`."""
        return self.extrapolate_authoritative_time()

    def get_authoritative_time_ms(self) -> int:
        return int(self.get_authoritative_time() * 1000)

    async def get_authoritative_time_async(self) -> float:
        return await asyncio.to_thread(self.get_authoritative_time)

    def validate_timestamp(
        self, timestamp: float, max_variance: Optional[float] = None
    ) -> bool:
        if max_variance is None:
            max_variance = self.config.max_time_variance
        current = self.get_authoritative_time()
        return abs(timestamp - current) <= max_variance

    async def validate_timestamp_async(
        self, timestamp: float, max_variance: Optional[float] = None
    ) -> bool:
        return await asyncio.to_thread(
            self.validate_timestamp, timestamp, max_variance
        )

    # ------------------------------------------------------------------ NTP

    async def sync_with_ntp(self) -> bool:
        """Query NTP servers and apply a new anchor. Raises on total failure."""
        if not NTP_AVAILABLE or not self._ntp_client:
            raise PrecisionTimeSyncError("NTP client not available (install ntplib)")

        last_error: Optional[Exception] = None
        for server in self.config.ntp_servers:
            try:
                response = await asyncio.to_thread(
                    self._ntp_client.request, server, version=3
                )
                ntp_time = response.tx_time
                local_time = time.time()
                offset = ntp_time - local_time
                variance = abs(offset)

                self.apply_anchor(
                    ntp_time,
                    offset,
                    variance_sample=variance,
                    last_sync_at=local_time,
                )

                payload = {
                    "server": server,
                    "offset": offset,
                    "variance": variance,
                    "ntp_time": ntp_time,
                }
                logger.debug(
                    "NTP sync %s offset=%.2fms variance=%.2fms",
                    server,
                    offset * 1000,
                    variance * 1000,
                )
                if self._on_sync:
                    result = self._on_sync(payload)
                    if asyncio.iscoroutine(result):
                        await result
                return True
            except Exception as exc:
                last_error = exc
                logger.debug("NTP sync failed with %s: %s", server, exc)

        raise PrecisionTimeSyncError(
            f"All configured NTP servers failed: {last_error}"
        )

    # ------------------------------------------------------------------ meta

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "synced": self._anchor is not None,
                "last_sync_at": self._anchor.last_sync_at if self._anchor else None,
                "time_offset": self._anchor.offset if self._anchor else 0.0,
                "ntp_variance": self._anchor.ntp_variance if self._anchor else None,
            }

    def get_precision_metadata(self, *, node_id: Optional[str] = None) -> Dict[str, Any]:
        """Metadata shape compatible with SIGNET time responses."""
        status = self.get_status()
        return {
            "time_authority_mode": "precision_local",
            "time_authority_role": "LOCAL",
            "ntp_variance": status.get("ntp_variance") or 0.0,
            "last_sync": status.get("last_sync_at"),
            "master_node": node_id,
        }

    def _record_variance(self, sample: float) -> None:
        self._variance_history.append(sample)
        if len(self._variance_history) > self.config.variance_history_size:
            self._variance_history.pop(0)

    def _average_variance(self) -> float:
        if not self._variance_history:
            return float("inf")
        return sum(self._variance_history) / len(self._variance_history)


# ------------------------------------------------------------------ module API

_default_keeper: Optional[PrecisionTimeKeeper] = None


def get_keeper() -> PrecisionTimeKeeper:
    """Return the process-default keeper (lazy-created)."""
    global _default_keeper
    if _default_keeper is None:
        _default_keeper = PrecisionTimeKeeper()
    return _default_keeper


async def initialize_default(sync_ntp: bool = True) -> PrecisionTimeKeeper:
    keeper = get_keeper()
    if sync_ntp:
        await keeper.sync_with_ntp()
    return keeper


def now() -> float:
    """Authoritative time from the default keeper (must be initialized)."""
    return get_keeper().get_authoritative_time()


def now_ms() -> int:
    return int(now() * 1000)


async def now_async() -> float:
    return await get_keeper().get_authoritative_time_async()


if __name__ == "__main__":
    async def _demo() -> None:
        keeper = await initialize_default()
        local = time.time()
        auth = keeper.get_authoritative_time()
        print("authoritative:", auth)
        print("local:        ", local)
        print("delta_ms:     ", (auth - local) * 1000)
        print("metadata:     ", keeper.get_precision_metadata(node_id="demo"))
        print("valid self:   ", keeper.validate_timestamp(auth))

    asyncio.run(_demo())
