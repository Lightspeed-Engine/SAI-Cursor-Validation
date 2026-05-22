#!/usr/bin/env python3
"""Stdlib-only helpers for Shufti run diagram manifests (testable without Flask)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def parse_diagram_manifest_payload(raw: Any) -> list[dict[str, Any]]:
    """
    Normalize diagram_manifest.json payloads.

    Supports:
    - legacy: list of artifact dicts
    - envelope: {"artifacts": [...], "errors": [...]}

    Rejects mistaken shapes that caused TypeError (e.g. iterating a dict's keys
    or list() of a string path).
    """
    entries: Any
    if isinstance(raw, list):
        entries = raw
    elif isinstance(raw, dict):
        candidate = raw.get("artifacts")
        if not isinstance(candidate, list):
            return []
        entries = candidate
    else:
        return []

    result: list[dict[str, Any]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not isinstance(path, str) or not path.strip():
            continue
        result.append(item)
    return result


def load_diagram_manifest_entries(manifest_path: Path) -> list[dict[str, Any]]:
    if not manifest_path.is_file():
        return []
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return parse_diagram_manifest_payload(raw)


def build_artifact_payloads(
    runs_dir: Path,
    artifact_dir: Path | None,
    manifest_name: str = "diagram_manifest.json",
) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    if artifact_dir is None:
        return artifacts

    manifest_path = artifact_dir / manifest_name
    for item in load_diagram_manifest_entries(manifest_path):
        artifact_path = Path(item["path"])
        if not artifact_path.exists():
            continue
        rel = artifact_path.relative_to(runs_dir)
        enriched = dict(item)
        enriched["url"] = f"/artifacts/{rel.as_posix()}"
        artifacts.append(enriched)
    return artifacts
