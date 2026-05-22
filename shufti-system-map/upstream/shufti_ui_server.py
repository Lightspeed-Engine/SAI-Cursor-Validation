#!/usr/bin/env python3
"""
Shufti web UI server with Socket.IO support.

This server provides:
- HTTP endpoints for static file serving (HTML/JS/CSS for the UI)
- Socket.IO for real-time data and event-driven API calls

Socket.IO Events:
- areas:list -> areas:list:response
- scan:area -> scan:area:progress -> scan:area:complete
- scan:multi -> scan:area:progress (per area) -> scan:multi:complete
- map:generate -> map:progress -> map:complete

HTTP endpoints (for static files):
- GET / - index.html
- GET /static/* - static assets
- GET /artifacts/* - generated artifacts
"""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import shutil
import subprocess
import sys
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import socketio
from flask import Flask, jsonify, request, send_from_directory

REQUESTED_ASYNC_MODE = os.getenv("SHUFTI_UI_ASYNC_MODE", "threading").strip().lower()

if REQUESTED_ASYNC_MODE == "gevent":
    try:
        from gevent import pywsgi
        from geventwebsocket.handler import WebSocketHandler
        SOCKETIO_ASYNC_MODE = "gevent"
    except ImportError:
        pywsgi = None
        WebSocketHandler = None
        SOCKETIO_ASYNC_MODE = "threading"
else:
    pywsgi = None
    WebSocketHandler = None
    SOCKETIO_ASYNC_MODE = "threading"


# --- Configuration & Constants ---

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
UI_DIR = SCRIPT_DIR / "shufti_ui"
MAPPER_SCRIPT = SCRIPT_DIR / "shufti_code_mapper.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from shufti_compose_mapper import find_compose_file, is_compose_file, run_compose_map
from shufti_run_artifacts import build_artifact_payloads
RUNS_DIR = REPO_ROOT / "data" / "shufti_ui_runs"
APP_DATA_DIR = REPO_ROOT / "data" / "shufti_ui"
LOG_PATH = APP_DATA_DIR / "shufti_ui_server.log"
README_PATH = SCRIPT_DIR / "SHUFTI_CODE_MAPPER_README.md"

DEFAULT_HOST = "100.126.175.99"
DEFAULT_PORT = 3005
MAX_PREVIEW_BYTES = 200_000
MAX_MAP_RESPONSE_BYTES = 500_000
DEFAULT_MAPPER_TIMEOUT_SECONDS = 120
MAX_MAPPER_TIMEOUT_SECONDS = 900
DEFAULT_MAX_FILES = 250
DEFAULT_MAX_LINES = 100_000
DEFAULT_MAX_FILE_BYTES = 1_000_000

# Area scanning defaults
DEFAULT_AREA_MAX_LINES = 80_000
DEFAULT_AREA_MAX_FILES = 200
DEFAULT_AREA_MAX_FILE_BYTES = 1_000_000
MAX_PARALLEL_AREAS = 4

# Area discovery defaults
DEFAULT_MAX_AREAS = 12
DEFAULT_MAX_LINES_PER_AREA = 80_000

DEFAULT_MAX_BROWSE_ENTRIES = 200

# Setup logging
LOGGER = logging.getLogger("shufti_ui_server")
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s %(message)s",
)


# --- Data Structures ---


@dataclass
class AppConfig:
    host: str
    port: int
    repo_root: str
    mapper_script: str
    runs_dir: str
    dot_available: bool
    default_mapper_timeout_seconds: int
    max_mapper_timeout_seconds: int
    default_max_files: int
    default_max_lines: int
    default_max_file_bytes: int
    max_browse_entries: int
    log_path: str
    log_url: str
    readme_path: str
    readme_url: str
    aispy_url: str


@dataclass
class AreaScanConfig:
    """Configuration for scanning a single area."""
    area_id: str
    target_path: str
    max_lines: int = DEFAULT_AREA_MAX_LINES
    max_files: int = DEFAULT_AREA_MAX_FILES
    max_file_bytes: int = DEFAULT_AREA_MAX_FILE_BYTES
    mode: str = "app"
    generate_diagrams: bool = False
    diagram_format: str = "dot"
    timeout_seconds: int = DEFAULT_MAPPER_TIMEOUT_SECONDS


@dataclass
class AreaScanResult:
    """Result of scanning a single area."""
    area_id: str
    status: str  # "success", "partial", "failed"
    files_included: int = 0
    lines_reviewed: int = 0
    stubs_detected: int = 0
    analysis_errors: list[str] = field(default_factory=list)
    snapshot_path: Optional[str] = None
    map_path: Optional[str] = None
    error_message: Optional[str] = None
    run_id: Optional[str] = None


@dataclass
class AreaInfo:
    """Information about a discovered area."""
    id: str
    path: str
    estimated_files: int = 0
    estimated_lines: int = 0
    recommended_max_lines: int = DEFAULT_AREA_MAX_LINES
    recommended_max_files: int = DEFAULT_AREA_MAX_FILES
    last_scanned: Optional[str] = None
    scan_count: int = 0


@dataclass
class DiscoveredArea:
    """A discovered area with optional sub-areas."""
    path: str
    estimated_files: int = 0
    estimated_lines: int = 0
    sub_areas: list[dict] = field(default_factory=list)


# --- Logging ---


def append_log_line(message: str) -> None:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_message = f"[{timestamp}] {message}"
    LOGGER.info(message)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{log_message}\n")


# --- Area Discovery ---


IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".venv-tests",
    ".venv-tdd",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "site-packages",
    "dist",
    "build",
    "htmlcov",
}


def count_python_files_and_lines(path: Path) -> tuple[int, int]:
    """Count Python files and lines in a directory tree."""
    total_files = 0
    total_lines = 0
    if not path.exists() or not path.is_dir():
        return 0, 0
    
    for root, dirs, files in os.walk(path):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORED_DIR_NAMES and not d.endswith(".egg-info")]
        
        for filename in files:
            if filename.endswith(".py"):
                total_files += 1
                file_path = Path(root) / filename
                try:
                    total_lines += len(file_path.read_text(encoding="utf-8").splitlines())
                except Exception:
                    pass
    return total_files, total_lines


def discover_areas(root: Path, max_areas: int = DEFAULT_MAX_AREAS, max_lines_per_area: int = DEFAULT_MAX_LINES_PER_AREA) -> list[DiscoveredArea]:
    """Discover scannable areas in the repository."""
    areas: list[DiscoveredArea] = []
    
    if not root.exists():
        return areas
    
    # Get top-level directories
    top_level_dirs = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and entry.name not in IGNORED_DIR_NAMES and not entry.name.startswith("."):
            top_level_dirs.append(entry)
    
    # Also check for specific known areas in core/
    core_dir = root / "core"
    if core_dir.exists():
        core_subdirs = []
        for entry in sorted(core_dir.iterdir()):
            if entry.is_dir() and entry.name not in IGNORED_DIR_NAMES and not entry.name.startswith("."):
                core_subdirs.append(entry)
        
        for subdir in core_subdirs:
            files, lines = count_python_files_and_lines(subdir)
            if lines > 0:
                if lines > max_lines_per_area * 0.5:
                    if lines > max_lines_per_area:
                        sub_areas = _partition_large_area(subdir, max_lines_per_area)
                        areas.append(DiscoveredArea(
                            path=str(subdir.relative_to(root)),
                            estimated_files=files,
                            estimated_lines=lines,
                            sub_areas=sub_areas,
                        ))
                    else:
                        areas.append(DiscoveredArea(
                            path=str(subdir.relative_to(root)),
                            estimated_files=files,
                            estimated_lines=lines,
                        ))
    
    # Add remaining top-level directories
    for subdir in top_level_dirs:
        if any(subdir.name == a.path.split("/")[-1] for a in areas):
            continue
        
        files, lines = count_python_files_and_lines(subdir)
        if lines > 0:
            if lines > max_lines_per_area:
                sub_areas = _partition_large_area(subdir, max_lines_per_area)
                areas.append(DiscoveredArea(
                    path=str(subdir.relative_to(root)),
                    estimated_files=files,
                    estimated_lines=lines,
                    sub_areas=sub_areas,
                ))
            else:
                areas.append(DiscoveredArea(
                    path=str(subdir.relative_to(root)),
                    estimated_files=files,
                    estimated_lines=lines,
                ))
    
    areas.sort(key=lambda a: a.estimated_lines, reverse=True)
    return areas[:max_areas]


def _partition_large_area(path: Path, max_lines_per_area: int) -> list[dict]:
    """Partition a large area into smaller sub-areas."""
    sub_areas: list[dict] = []
    
    if not path.exists() or not path.is_dir():
        return sub_areas
    
    subdirs = []
    for entry in sorted(path.iterdir()):
        if entry.is_dir() and entry.name not in IGNORED_DIR_NAMES and not entry.name.startswith("."):
            subdirs.append(entry)
    
    if not subdirs:
        return sub_areas
    
    for subdir in subdirs:
        files, lines = count_python_files_and_lines(subdir)
        if lines > 0:
            sub_areas.append({
                "path": str(subdir.relative_to(path.parent)),
                "estimated_files": files,
                "estimated_lines": lines,
            })
    
    return sub_areas


def get_available_areas() -> list[AreaInfo]:
    """Get list of available areas with their estimated sizes."""
    areas: list[AreaInfo] = []
    root = REPO_ROOT
    
    area_configs = [
        ("core_services", "core/services", 80_000, 200),
        ("core_configs", "core/configs", 20_000, 100),
        ("scripts", "scripts", 60_000, 150),
        ("deployment", "deployment", 50_000, 150),
        ("containers", "containers", 25_000, 100),
        ("tests", "tests", 80_000, 200),
        ("src", "src", 60_000, 150),
        ("configs", "configs", 15_000, 100),
        ("tools", "tools", 20_000, 100),
        ("environments", "environments", 35_000, 100),
    ]
    
    for area_id, path, recommended_lines, recommended_files in area_configs:
        area_path = root / path
        files, lines = count_python_files_and_lines(area_path)
        
        if files > 0:
            areas.append(AreaInfo(
                id=area_id,
                path=path,
                estimated_files=files,
                estimated_lines=lines,
                recommended_max_lines=recommended_lines,
                recommended_max_files=recommended_files,
            ))
    
    return areas


# --- Area Scanning Functions ---


def scan_single_area(config: AreaScanConfig, runs_dir: Path, repo_root: Path) -> AreaScanResult:
    """Scan a single area with the given configuration."""
    result = AreaScanResult(area_id=config.area_id, status="failed")
    
    try:
        target_path = repo_root / config.target_path
        if not target_path.exists():
            result.error_message = f"target path does not exist: {config.target_path}"
            return result
        
        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        output_format = "json"
        output_path = run_dir / f"code-map.json"
        snapshot_output_path = run_dir / "snapshot.json"
        
        command = build_run_command(
            sys.executable,
            {
                "targets": [str(target_path)],
                "mode": config.mode,
                "format": output_format,
                "max_files": config.max_files,
                "max_lines": config.max_lines,
                "max_file_bytes": config.max_file_bytes,
            },
            output_path,
            snapshot_output_path,
            None,
        )
        
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
            cwd=str(repo_root),
        )
        
        if completed.returncode != 0:
            result.error_message = f"mapper failed: {completed.stderr}"
            result.status = "failed"
            return result
        
        if snapshot_output_path.exists():
            snapshot = json.loads(snapshot_output_path.read_text(encoding="utf-8"))
            header = snapshot.get("header", {})
            result.files_included = header.get("files_included", 0)
            result.lines_reviewed = header.get("lines_reviewed", 0)
            result.stubs_detected = header.get("stubs_detected", 0)
            result.analysis_errors = snapshot.get("analysis_errors", [])
            result.snapshot_path = str(snapshot_output_path)
        
        result.map_path = str(output_path)
        result.run_id = run_id
        result.status = "success"
        
    except subprocess.TimeoutExpired as exc:
        result.error_message = f"timeout after {config.timeout_seconds}s"
        result.status = "failed"
    except Exception as exc:
        result.error_message = str(exc)
        result.status = "failed"
    
    return result


def scan_multiple_areas(
    configs: list[AreaScanConfig],
    runs_dir: Path,
    repo_root: Path,
    parallel: bool = False,
) -> list[AreaScanResult]:
    """Scan multiple areas, optionally in parallel."""
    results: list[AreaScanResult] = []
    
    if parallel and len(configs) > 1:
        with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_AREAS, len(configs))) as executor:
            futures = {
                executor.submit(scan_single_area, config, runs_dir, repo_root): config
                for config in configs
            }
            for future in as_completed(futures):
                results.append(future.result())
    else:
        for config in configs:
            results.append(scan_single_area(config, runs_dir, repo_root))
    
    results.sort(key=lambda r: r.area_id)
    return results


# --- Helper Functions ---


def clamp_int(value: object, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def build_run_command(
    python_executable: str,
    request: dict,
    output_path: Path,
    snapshot_output_path: Path,
    diagram_dir: Path | None,
) -> list[str]:
    targets = request.get("targets") or []
    command = [
        python_executable,
        str(MAPPER_SCRIPT),
        "--mode",
        str(request.get("mode") or "auto"),
        "--format",
        str(request.get("format") or "markdown"),
        "--output",
        str(output_path),
        "--snapshot-output",
        str(snapshot_output_path),
        "--max-files",
        str(request.get("max_files")),
        "--max-lines",
        str(request.get("max_lines")),
        "--max-file-bytes",
        str(request.get("max_file_bytes")),
    ]
    if diagram_dir is not None:
        command.extend(["--diagram-dir", str(diagram_dir)])
        command.extend(
            ["--diagram-format", str(request.get("diagram_format") or "dot")]
        )
        command.extend(
            ["--diagram-profile", str(request.get("diagram_profile") or "filesystem")]
        )
        if bool(request.get("render_svg")):
            command.append("--render-svg")
    skip_diagrams = request.get("skip_diagrams") or []
    if skip_diagrams:
        command.append("--skip-diagrams")
        command.extend(str(name) for name in skip_diagrams)
    command.extend(str(target) for target in targets)
    return command


RECOVERY_HEAVY_DIAGRAMS = ("interaction_map", "class_map")


def run_mapper_subprocess(
    command: list[str],
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        cwd=str(REPO_ROOT),
    )


def write_mapper_failure_artifact(
    run_dir: Path,
    *,
    error: str,
    completed: subprocess.CompletedProcess[str] | None = None,
    timeout_details: str | None = None,
    recovery_attempts: list[dict] | None = None,
) -> Path:
    payload = {
        "error": error,
        "created_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "recovery_attempts": recovery_attempts or [],
    }
    if completed is not None:
        payload.update({
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        })
    if timeout_details:
        payload["timeout_details"] = timeout_details
    failure_path = run_dir / "mapper_failure.json"
    failure_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return failure_path


def build_recovery_plan(
    base_request: dict,
    *,
    generate_diagrams: bool,
) -> list[tuple[str, dict]]:
    """Ordered recovery attempts after mapper failure or timeout."""
    plan: list[tuple[str, dict]] = []
    if generate_diagrams:
        plan.append((
            "skip_heavy_diagrams_dot",
            {
                **base_request,
                "diagram_format": "dot",
                "skip_diagrams": list(RECOVERY_HEAVY_DIAGRAMS),
            },
        ))
        plan.append((
            "map_only_no_diagrams",
            {**base_request, "generate_diagrams": False},
        ))
    reduced_limits = {
        **base_request,
        "max_files": max(50, int(base_request["max_files"]) // 2),
        "max_lines": max(5_000, int(base_request["max_lines"]) // 2),
        "generate_diagrams": False,
    }
    if not any(step_name == "reduced_scope_map_only" for step_name, _ in plan):
        plan.append(("reduced_scope_map_only", reduced_limits))
    return plan


def attempt_mapper_recovery(
    *,
    python_executable: str,
    run_dir: Path,
    output_path: Path,
    snapshot_output_path: Path,
    base_request: dict,
    mapper_timeout: int,
    generate_diagrams: bool,
    initial_error: str,
    initial_completed: subprocess.CompletedProcess[str] | None = None,
    timeout_details: str | None = None,
    progress_callback: Optional[callable] = None,
) -> tuple[subprocess.CompletedProcess[str] | None, list[dict], str | None]:
    recovery_log: list[dict] = []
    last_completed = initial_completed

    for step_name, recovery_request in build_recovery_plan(
        base_request,
        generate_diagrams=generate_diagrams,
    ):
        if progress_callback:
            progress_callback({
                "status": "recovering",
                "message": f"Recovery attempt: {step_name}",
                "run_id": run_dir.name,
            })
        diagram_dir = run_dir / "diagrams" if recovery_request.get("generate_diagrams") else None
        command = build_run_command(
            python_executable,
            recovery_request,
            output_path,
            snapshot_output_path,
            diagram_dir,
        )
        try:
            completed = run_mapper_subprocess(command, mapper_timeout)
        except subprocess.TimeoutExpired as exc:
            recovery_log.append({
                "step": step_name,
                "ok": False,
                "error": "mapper_timeout",
                "details": str(exc),
            })
            last_completed = None
            timeout_details = str(exc)
            continue

        entry = {
            "step": step_name,
            "ok": completed.returncode == 0 and output_path.exists(),
            "returncode": completed.returncode,
        }
        if completed.returncode != 0:
            entry["stderr_tail"] = (completed.stderr or "")[-2000:]
        recovery_log.append(entry)
        last_completed = completed
        if entry["ok"]:
            append_log_line(
                f"run_recovered run_id={run_dir.name} step={step_name} "
                f"after={initial_error}"
            )
            return completed, recovery_log, step_name

    write_mapper_failure_artifact(
        run_dir,
        error=initial_error,
        completed=last_completed,
        timeout_details=timeout_details,
        recovery_attempts=recovery_log,
    )
    (run_dir / "run.json").write_text(
        json.dumps({
            "run_id": run_dir.name,
            "status": "failed",
            "error": initial_error,
            "created_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "recovery_attempts": recovery_log,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    return None, recovery_log, None


def finalize_map_success_payload(
    *,
    run_id: str,
    run_dir: Path,
    runs_dir: Path,
    output_path: Path,
    snapshot_output_path: Path,
    output_format: str,
    normalized_targets: list[str],
    data: dict,
    mapper_timeout: int,
    max_files: int,
    max_lines: int,
    max_file_bytes: int,
    completed: subprocess.CompletedProcess[str],
    recovered: bool = False,
    recovery_step: str | None = None,
    recovery_attempts: list[dict] | None = None,
) -> dict:
    full_map_text = output_path.read_text(encoding="utf-8")
    map_truncated = len(full_map_text.encode("utf-8")) > MAX_MAP_RESPONSE_BYTES
    map_text = full_map_text[:MAX_MAP_RESPONSE_BYTES]
    artifacts = build_artifact_payloads(
        runs_dir,
        (run_dir / "diagrams") if (run_dir / "diagrams").exists() else None,
    )
    topology_path = run_dir / "diagrams" / "code_topology.json"
    system_map_path = run_dir / "diagrams" / "system_map.json"
    topology = {}
    topology_fingerprint = None
    if topology_path.exists():
        try:
            topology = json.loads(topology_path.read_text(encoding="utf-8"))
            topology_fingerprint = (topology.get("summary") or {}).get("topology_fingerprint")
        except Exception:
            topology = {}
    payload = {
        "ok": True,
        "run_id": run_id,
        "map_format": output_format,
        "map_path": str(output_path),
        "map_url": f"/artifacts/{output_path.relative_to(runs_dir).as_posix()}",
        "map_text": map_text,
        "map_truncated": map_truncated,
        "timeout_seconds": mapper_timeout,
        "limits": {
            "max_files": max_files,
            "max_lines": max_lines,
            "max_file_bytes": max_file_bytes,
        },
        "artifacts": artifacts,
        "topology_url": (
            f"/artifacts/{topology_path.relative_to(runs_dir).as_posix()}"
            if topology_path.exists()
            else None
        ),
        "system_map_url": (
            f"/artifacts/{system_map_path.relative_to(runs_dir).as_posix()}"
            if system_map_path.exists()
            else None
        ),
        "topology_api_url": f"/api/topology/latest?run_id={run_id}",
        "topology_map_viewer_url": (
            f"/static/topology-map-viewer.html?run_id={run_id}"
            if topology_path.exists()
            else None
        ),
        "topology_fingerprint": topology_fingerprint,
        "aispy_live_url": f"{get_config().aispy_url}/?map=live",
        "aispy_architecture_url": f"{get_config().aispy_url}/?map=architecture",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "command": completed.args if hasattr(completed, "args") else None,
        "recovered": recovered,
    }
    if recovered:
        payload["recovery_step"] = recovery_step
        payload["recovery_attempts"] = recovery_attempts or []
        payload["warning"] = (
            f"Initial mapper run failed; recovered via {recovery_step}. "
            "Some diagrams may be omitted or truncated."
        )
    (run_dir / "run.json").write_text(
        json.dumps({
            "run_id": run_id,
            "status": "completed",
            "recovered": recovered,
            "recovery_step": recovery_step,
            "created_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "targets": normalized_targets,
            "mode": data.get("mode", "auto"),
            "format": output_format,
            "diagram_profile": data.get("diagram_profile", "filesystem"),
            "diagram_format": data.get("diagram_format", "dot"),
            "timeout_seconds": mapper_timeout,
            "limits": payload["limits"],
            "artifact_count": len(artifacts),
            "map_path": str(output_path),
            "snapshot_path": str(snapshot_output_path),
            "topology_path": str(topology_path) if topology_path.exists() else None,
            "system_map_path": str(system_map_path) if system_map_path.exists() else None,
            "topology_fingerprint": topology_fingerprint,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    append_log_line(
        f"run_completed run_id={run_id} artifact_count={len(artifacts)} "
        f"recovered={recovered}"
    )
    return payload


# --- Flask + Socket.IO Application ---

# Create Flask app and Socket.IO server
flask_app = Flask(__name__, static_folder=str(UI_DIR), static_url_path="/static")
sio = socketio.Server(cors_allowed_origins="*", async_mode=SOCKETIO_ASYNC_MODE)
app = socketio.WSGIApp(sio, flask_app)

# Store app_config globally for access in Socket.IO handlers
_app_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _app_config
    if _app_config is None:
        raise RuntimeError("App config not initialized")
    return _app_config


def get_repo_root() -> Path:
    return Path(get_config().repo_root)


def get_runs_dir() -> Path:
    return Path(get_config().runs_dir)


def find_latest_compose_run(runs_dir: Path, run_id: Optional[str] = None) -> Optional[Path]:
    if run_id:
        candidate = runs_dir / run_id
        snapshot = candidate / "snapshot.json"
        if snapshot.exists():
            try:
                payload = json.loads(snapshot.read_text(encoding="utf-8"))
            except Exception:
                return None
            if payload.get("mode") == "compose":
                return candidate
        return None

    for candidate in sorted(runs_dir.iterdir(), reverse=True):
        if not candidate.is_dir():
            continue
        snapshot = candidate / "snapshot.json"
        if not snapshot.exists():
            continue
        try:
            payload = json.loads(snapshot.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("mode") == "compose":
            return candidate
    return None


def build_compose_diagram_payloads(run_dir: Path, runs_dir: Path) -> dict[str, dict]:
    diagrams: dict[str, dict] = {}
    diagram_dir = run_dir / "diagrams"
    for name in ("high_level_overview", "component_coupling", "coupling_summary"):
        path = diagram_dir / f"{name}.mmd"
        if not path.exists():
            continue
        rel = path.relative_to(runs_dir)
        diagrams[name] = {
            "name": name,
            "format": "mermaid",
            "url": f"/artifacts/{rel.as_posix()}",
            "text": path.read_text(encoding="utf-8"),
        }
    return diagrams


def find_latest_code_topology_run(runs_dir: Path, run_id: Optional[str] = None) -> Optional[Path]:
    if run_id:
        candidate = runs_dir / run_id
        if (candidate / "diagrams" / "code_topology.json").exists():
            return candidate
        return None

    for candidate in sorted(runs_dir.iterdir(), reverse=True):
        if not candidate.is_dir():
            continue
        if (candidate / "diagrams" / "code_topology.json").exists():
            return candidate
    return None


def _artifact_url_for(path: Path, runs_dir: Path) -> str:
    return f"/artifacts/{path.relative_to(runs_dir).as_posix()}"


def execute_compose_map_request(
    data: dict,
    compose_path: Path,
    progress_callback: Optional[callable] = None,
) -> dict:
    output_format = str(data.get("format") or "markdown")
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    runs_dir = get_runs_dir()
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if progress_callback:
        progress_callback({
            "status": "running",
            "message": f"Mapping compose topology: {compose_path.name}",
            "run_id": run_id,
        })

    diagram_profile = str(data.get("diagram_profile") or "demo")
    result = run_compose_map(compose_path, run_dir, output_format, diagram_profile)
    artifacts = build_artifact_payloads(runs_dir, run_dir / "diagrams")
    output_path = Path(result["map_path"])
    full_map_text = output_path.read_text(encoding="utf-8")
    map_truncated = len(full_map_text.encode("utf-8")) > MAX_MAP_RESPONSE_BYTES
    map_text = full_map_text[:MAX_MAP_RESPONSE_BYTES]

    payload = {
        "ok": True,
        "run_id": run_id,
        "mode": "compose",
        "map_format": output_format,
        "map_path": str(output_path),
        "map_url": f"/artifacts/{output_path.relative_to(runs_dir).as_posix()}",
        "map_text": map_text,
        "map_truncated": map_truncated,
        "compose_path": result.get("compose_path"),
        "service_count": result.get("service_count"),
        "edge_count": result.get("edge_count"),
        "artifacts": artifacts,
        "architecture_viewer_url": f"/static/architecture-viewer.html?run_id={run_id}",
    }

    (run_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "created_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "targets": [str(compose_path)],
                "mode": "compose",
                "format": output_format,
                "compose_path": str(compose_path),
                "artifact_count": len(artifacts),
                "map_path": str(output_path),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    append_log_line(
        f"compose_run_completed run_id={run_id} services={result.get('service_count')} edges={result.get('edge_count')}"
    )
    return payload


def execute_map_request(
    data: dict,
    progress_callback: Optional[callable] = None,
) -> dict:
    """Run the code mapper and return the HTTP/Socket payload."""
    targets = data.get("targets") or []
    if not targets:
        raise ValueError("at least one target is required")

    repo_root = get_repo_root()
    normalized_targets = []
    for raw_target in targets:
        candidate = Path(raw_target)
        if not candidate.is_absolute():
            candidate = repo_root / raw_target
        if not candidate.exists():
            raise FileNotFoundError(f"target does not exist: {candidate}")
        normalized_targets.append(str(candidate))

    mode = str(data.get("mode") or "auto")
    compose_path: Optional[Path] = None
    if mode == "compose":
        compose_path = find_compose_file(normalized_targets, repo_root)
        if compose_path is None:
            raise ValueError("compose mode requires a docker-compose target")
    else:
        for target in normalized_targets:
            candidate = Path(target)
            if is_compose_file(candidate):
                compose_path = candidate
                break

    if compose_path is not None:
        return execute_compose_map_request(data, compose_path, progress_callback)

    max_files = clamp_int(
        data.get("max_files"),
        get_config().default_max_files,
        1,
        20_000,
    )
    max_lines = clamp_int(
        data.get("max_lines"),
        get_config().default_max_lines,
        100,
        5_000_000,
    )
    max_file_bytes = clamp_int(
        data.get("max_file_bytes"),
        get_config().default_max_file_bytes,
        1_024,
        50_000_000,
    )
    mapper_timeout = clamp_int(
        data.get("timeout_seconds"),
        get_config().default_mapper_timeout_seconds,
        5,
        get_config().max_mapper_timeout_seconds,
    )

    output_format = str(data.get("format") or "markdown")
    generate_diagrams = bool(data.get("generate_diagrams", True))

    if progress_callback:
        progress_callback({
            "status": "starting",
            "message": "Initializing code map generation",
            "targets": normalized_targets,
        })

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    runs_dir = get_runs_dir()
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    append_log_line(f"run_started run_id={run_id} targets={normalized_targets}")

    output_ext = "json" if output_format == "json" else "md"
    output_path = run_dir / f"code-map.{output_ext}"
    snapshot_output_path = run_dir / "snapshot.json"

    command = build_run_command(
        sys.executable,
        {
            "targets": normalized_targets,
            "mode": data.get("mode", "auto"),
            "format": output_format,
            "max_files": max_files,
            "max_lines": max_lines,
            "max_file_bytes": max_file_bytes,
            "generate_diagrams": generate_diagrams,
            "diagram_format": str(data.get("diagram_format") or "dot"),
            "diagram_profile": str(data.get("diagram_profile") or "filesystem"),
            "render_svg": bool(data.get("render_svg")),
        },
        output_path,
        snapshot_output_path,
        run_dir / "diagrams" if generate_diagrams else None,
    )

    if progress_callback:
        progress_callback({
            "status": "running",
            "message": "Running code mapper",
            "run_id": run_id,
        })

    base_request = {
        "targets": normalized_targets,
        "mode": data.get("mode", "auto"),
        "format": output_format,
        "max_files": max_files,
        "max_lines": max_lines,
        "max_file_bytes": max_file_bytes,
        "generate_diagrams": generate_diagrams,
        "diagram_format": str(data.get("diagram_format") or "dot"),
        "diagram_profile": str(data.get("diagram_profile") or "filesystem"),
        "render_svg": bool(data.get("render_svg")),
    }

    recovered = False
    recovery_step: str | None = None
    recovery_attempts: list[dict] = []
    initial_error = "mapper_failed"
    timeout_details: str | None = None

    try:
        completed = run_mapper_subprocess(command, mapper_timeout)
    except subprocess.TimeoutExpired as exc:
        initial_error = "mapper_timeout"
        timeout_details = str(exc)
        append_log_line(f"mapper_timeout run_id={run_id} details={exc}")
        completed = None
    else:
        if completed.returncode != 0:
            append_log_line(
                f"mapper_failed run_id={run_id} returncode={completed.returncode}"
            )

    needs_recovery = (
        completed is None
        or completed.returncode != 0
        or not output_path.exists()
    )

    if needs_recovery:
        recovered_completed, recovery_attempts, recovery_step = attempt_mapper_recovery(
            python_executable=sys.executable,
            run_dir=run_dir,
            output_path=output_path,
            snapshot_output_path=snapshot_output_path,
            base_request=base_request,
            mapper_timeout=mapper_timeout,
            generate_diagrams=generate_diagrams,
            initial_error=initial_error,
            initial_completed=completed,
            timeout_details=timeout_details,
            progress_callback=progress_callback,
        )
        if recovered_completed is None:
            failure_path = run_dir / "mapper_failure.json"
            return {
                "ok": False,
                "error": initial_error,
                "run_id": run_id,
                "returncode": completed.returncode if completed else None,
                "stdout": completed.stdout if completed else "",
                "stderr": completed.stderr if completed else "",
                "command": command,
                "recovery_attempts": recovery_attempts,
                "failure_url": (
                    f"/artifacts/{failure_path.relative_to(runs_dir).as_posix()}"
                    if failure_path.exists()
                    else None
                ),
                "hint": (
                    "Recovery exhausted. Narrow the target, lower max_files/max_lines, "
                    "or disable diagrams."
                ),
            }
        completed = recovered_completed
        recovered = True

    return finalize_map_success_payload(
        run_id=run_id,
        run_dir=run_dir,
        runs_dir=runs_dir,
        output_path=output_path,
        snapshot_output_path=snapshot_output_path,
        output_format=output_format,
        normalized_targets=normalized_targets,
        data=data,
        mapper_timeout=mapper_timeout,
        max_files=max_files,
        max_lines=max_lines,
        max_file_bytes=max_file_bytes,
        completed=completed,
        recovered=recovered,
        recovery_step=recovery_step,
        recovery_attempts=recovery_attempts,
    )


# --- HTTP Routes (Flask) ---


@flask_app.route("/")
def index():
    """Serve the main UI page."""
    return send_from_directory(str(UI_DIR), "index.html")


@flask_app.route("/api/config")
def get_config_http():
    """HTTP endpoint to get app configuration."""
    return jsonify(asdict(get_config()))


@flask_app.route("/api/map", methods=["POST"])
def generate_map_http():
    """HTTP endpoint used by the SHUFTI browser UI to generate a code map."""
    try:
        data = request.get_json(silent=True) or {}
        payload = execute_map_request(data)
        status = 200 if payload.get("ok") else 400
        return jsonify(payload), status
    except subprocess.TimeoutExpired as exc:
        append_log_line(f"mapper_timeout details={exc}")
        return jsonify({
            "ok": False,
            "error": "mapper_timeout",
            "details": str(exc),
            "hint": "narrow the target scope or lower diagram/render options",
        }), 408
    except Exception as exc:
        append_log_line(f"api:map:error {exc}\n{traceback.format_exc()}")
        return jsonify({
            "ok": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }), 500


@flask_app.route("/api/compose/latest")
def compose_latest_http():
    """Return the latest compose architecture diagrams for demo viewers."""
    try:
        run_id = request.args.get("run_id")
        runs_dir = get_runs_dir()
        run_dir = find_latest_compose_run(runs_dir, run_id)
        if run_dir is None:
            return jsonify({
                "ok": False,
                "error": "no_compose_run",
                "hint": "Generate a map with mode=compose against standalone-deployment-docker-compose.yml",
            }), 404

        snapshot_path = run_dir / "snapshot.json"
        snapshot = {}
        if snapshot_path.exists():
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

        diagrams = build_compose_diagram_payloads(run_dir, runs_dir)
        return jsonify({
            "ok": True,
            "run_id": run_dir.name,
            "compose_path": snapshot.get("source_path"),
            "service_count": snapshot.get("service_count"),
            "edge_count": snapshot.get("edge_count"),
            "diagrams": diagrams,
            "architecture_viewer_url": f"/static/architecture-viewer.html?run_id={run_dir.name}",
        })
    except Exception as exc:
        append_log_line(f"api:compose:latest:error {exc}\n{traceback.format_exc()}")
        return jsonify({"ok": False, "error": str(exc)}), 500


@flask_app.route("/api/topology/latest")
def topology_latest_http():
    """Return the latest generated Shufti code topology and system-map view."""
    try:
        run_id = request.args.get("run_id")
        runs_dir = get_runs_dir()
        run_dir = find_latest_code_topology_run(runs_dir, run_id)
        if run_dir is None:
            return jsonify({
                "ok": False,
                "error": "no_code_topology_run",
                "hint": "Generate a code map with diagrams enabled; Shufti emits code_topology.json and system_map.json.",
            }), 404

        diagram_dir = run_dir / "diagrams"
        topology_path = diagram_dir / "code_topology.json"
        system_map_path = diagram_dir / "system_map.json"
        topology = json.loads(topology_path.read_text(encoding="utf-8"))
        system_map = {}
        if system_map_path.exists():
            system_map = json.loads(system_map_path.read_text(encoding="utf-8"))
        else:
            system_map = (topology.get("views") or {}).get("system_overview") or {}

        return jsonify({
            "ok": True,
            "run_id": run_dir.name,
            "schema_version": topology.get("schema_version"),
            "generated_at_utc": topology.get("generated_at_utc"),
            "analysis_root": topology.get("analysis_root"),
            "summary": topology.get("summary") or {},
            "topology_fingerprint": (topology.get("summary") or {}).get("topology_fingerprint"),
            "code_topology_url": _artifact_url_for(topology_path, runs_dir),
            "system_map_url": (
                _artifact_url_for(system_map_path, runs_dir)
                if system_map_path.exists()
                else None
            ),
            "topology": topology,
            "system_map": system_map,
            "webview_contract": {
                "entry_view": "system_overview",
                "component_drilldown": "component_detail",
                "agent_drilldown": "agent_card",
                "live_streams": ["braid.events", "aispy.agents", "aispy.area_update"],
                "incremental_update": "segment_fingerprint",
            },
        })
    except Exception as exc:
        append_log_line(f"api:topology:latest:error {exc}\n{traceback.format_exc()}")
        return jsonify({"ok": False, "error": str(exc)}), 500


@flask_app.route("/logs/shufti-ui")
def get_logs():
    """Serve the log file."""
    log_path = Path(get_config().log_path)
    if not log_path.exists():
        return jsonify({"ok": False, "error": "log not found"}), 404
    content = log_path.read_text(encoding="utf-8")
    return content, 200, {"Content-Type": "text/plain; charset=utf-8"}


@flask_app.route("/docs/shufti-readme")
def get_readme():
    """Serve the README file."""
    readme_path = Path(get_config().readme_path)
    if not readme_path.exists():
        return jsonify({"ok": False, "error": "readme not found"}), 404
    content = readme_path.read_text(encoding="utf-8")
    return content, 200, {"Content-Type": "text/markdown; charset=utf-8"}


@flask_app.route("/artifacts/<path:filename>")
def serve_artifact(filename):
    """Serve generated artifacts."""
    try:
        safe_filename = filename.replace("..", "").replace("//", "")
        return send_from_directory(str(get_runs_dir()), safe_filename)
    except Exception:
        return jsonify({"ok": False, "error": "artifact not found"}), 404


@flask_app.route("/api/browse")
def browse():
    """Browse directory contents via HTTP."""
    from urllib.parse import parse_qs
    
    params = parse_qs(request.query_string.decode())
    raw_path = (params.get("path") or [""])[0]
    
    try:
        if not raw_path:
            root = get_repo_root()
        else:
            candidate = get_repo_root() / raw_path
            if not candidate.exists():
                raise FileNotFoundError(f"path does not exist: {candidate}")
            root = candidate
        
        entries = []
        max_entries = get_config().max_browse_entries
        
        for index, child in enumerate(
            sorted(root.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())),
            start=1,
        ):
            if max_entries > 0 and index > max_entries:
                break
            entries.append({
                "name": child.name,
                "path": str(child),
                "relative_path": safe_relative(child, get_repo_root()),
                "kind": "directory" if child.is_dir() else "file",
                "size": child.stat().st_size if child.is_file() else None,
            })
        
        return jsonify({
            "ok": True,
            "path": str(root),
            "relative_path": safe_relative(root, get_repo_root()),
            "entries": entries,
            "truncated": index > max_entries,
            "max_entries": max_entries,
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@flask_app.route("/api/file")
def file_preview():
    """Preview a file via HTTP."""
    from urllib.parse import parse_qs
    
    params = parse_qs(request.query_string.decode())
    raw_path = (params.get("path") or [""])[0]
    
    try:
        if not raw_path:
            raise ValueError("path parameter required")
        
        candidate = get_repo_root() / raw_path
        if not candidate.exists():
            raise FileNotFoundError(f"file does not exist: {candidate}")
        if not candidate.is_file():
            raise IsADirectoryError(f"not a file: {candidate}")
        
        raw = candidate.read_bytes()
        truncated = len(raw) > MAX_PREVIEW_BYTES
        sample = raw[:MAX_PREVIEW_BYTES]
        binary = b"\x00" in sample
        
        if binary:
            text = ""
        else:
            text = sample.decode("utf-8", errors="replace")
        
        return jsonify({
            "ok": True,
            "path": str(candidate),
            "relative_path": safe_relative(candidate, get_repo_root()),
            "size": len(raw),
            "truncated": truncated,
            "binary": binary,
            "content": text,
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@flask_app.route("/api/runs")
def list_runs():
    """List all runs via HTTP."""
    runs = []
    runs_dir = get_runs_dir()
    
    if runs_dir.exists():
        for run_dir in sorted(runs_dir.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue
            
            metadata_path = run_dir / "run.json"
            if not metadata_path.exists():
                continue
            
            try:
                run = json.loads(metadata_path.read_text(encoding="utf-8"))
                
                map_path_value = run.get("map_path")
                if map_path_value and Path(map_path_value).exists():
                    run["map_url"] = f"/artifacts/{Path(map_path_value).relative_to(runs_dir).as_posix()}"
                
                snapshot_path_value = run.get("snapshot_path")
                if snapshot_path_value and Path(snapshot_path_value).exists():
                    run["snapshot_url"] = f"/artifacts/{Path(snapshot_path_value).relative_to(runs_dir).as_posix()}"

                topology_path_value = run.get("topology_path")
                if topology_path_value and Path(topology_path_value).exists():
                    run["topology_url"] = f"/artifacts/{Path(topology_path_value).relative_to(runs_dir).as_posix()}"
                    run["topology_api_url"] = f"/api/topology/latest?run_id={run_dir.name}"

                system_map_path_value = run.get("system_map_path")
                if system_map_path_value and Path(system_map_path_value).exists():
                    run["system_map_url"] = f"/artifacts/{Path(system_map_path_value).relative_to(runs_dir).as_posix()}"
                
                diagram_dir = run_dir / "diagrams"
                run["artifacts"] = build_artifact_payloads(runs_dir, diagram_dir if diagram_dir.exists() else None)
                
                diff_dir = run_dir / "diff"
                run["diff_artifacts"] = build_artifact_payloads(
                    runs_dir,
                    diff_dir if diff_dir.exists() else None,
                    manifest_name="diff_manifest.json",
                )
                
                runs.append(run)
            except Exception:
                continue
    
    return jsonify({"ok": True, "runs": runs[:25]})


# --- Socket.IO Event Handlers ---


@sio.on("connect")
def handle_connect(sid, environ):
    """Handle client connection."""
    append_log_line(f"socketio_client_connected sid={sid}")
    return True


@sio.on("disconnect")
def handle_disconnect(sid):
    """Handle client disconnection."""
    append_log_line(f"socketio_client_disconnected sid={sid}")


@sio.on("areas:list")
def handle_areas_list(sid, data):
    """List available areas via Socket.IO."""
    try:
        areas = get_available_areas()
        sio.emit("areas:list:response", {
            "ok": True,
            "areas": [asdict(area) for area in areas],
        }, room=sid)
    except Exception as exc:
        append_log_line(f"areas:list:error {exc}")
        sio.emit("areas:list:response", {
            "ok": False,
            "error": str(exc),
        }, room=sid)


@sio.on("scan:area")
def handle_scan_area(sid, data):
    """Scan a specific area via Socket.IO with progress events."""
    try:
        area_id = str(data.get("area_id") or "").strip()
        target_path = str(data.get("path") or "").strip()
        
        if not area_id and not target_path:
            raise ValueError("area_id or path is required")
        
        if not area_id:
            area_id = target_path.replace("/", "_").replace("\\", "_")
        
        config = AreaScanConfig(
            area_id=area_id,
            target_path=target_path,
            max_lines=clamp_int(
                data.get("max_lines"),
                DEFAULT_AREA_MAX_LINES,
                100,
                5_000_000,
            ),
            max_files=clamp_int(
                data.get("max_files"),
                DEFAULT_AREA_MAX_FILES,
                1,
                20_000,
            ),
            max_file_bytes=clamp_int(
                data.get("max_file_bytes"),
                DEFAULT_AREA_MAX_FILE_BYTES,
                1_024,
                50_000_000,
            ),
            mode=str(data.get("mode") or "app"),
            timeout_seconds=clamp_int(
                data.get("timeout_seconds"),
                DEFAULT_MAPPER_TIMEOUT_SECONDS,
                5,
                MAX_MAPPER_TIMEOUT_SECONDS,
            ),
        )
        
        append_log_line(f"area_scan_started area_id={area_id} path={target_path}")
        
        # Emit progress event - scan started
        sio.emit("scan:area:progress", {
            "area_id": area_id,
            "status": "started",
            "message": f"Starting scan of {target_path}",
        }, room=sid)
        
        # Perform the scan
        result = scan_single_area(config, get_runs_dir(), get_repo_root())
        
        # Emit completion event with result
        sio.emit("scan:area:complete", {
            "ok": result.status == "success",
            "area_id": result.area_id,
            "status": result.status,
            "files_included": result.files_included,
            "lines_reviewed": result.lines_reviewed,
            "stubs_detected": result.stubs_detected,
            "analysis_errors": result.analysis_errors,
            "snapshot_path": result.snapshot_path,
            "map_path": result.map_path,
            "run_id": result.run_id,
            "error_message": result.error_message,
        }, room=sid)
        
        append_log_line(
            f"area_scan_completed area_id={area_id} status={result.status} "
            f"files={result.files_included} lines={result.lines_reviewed}"
        )
        
    except Exception as exc:
        append_log_line(f"scan:area:error {exc}")
        sio.emit("scan:area:complete", {
            "ok": False,
            "error": str(exc),
        }, room=sid)


@sio.on("scan:multi")
def handle_scan_multi(sid, data):
    """Scan multiple areas via Socket.IO with per-area progress events."""
    try:
        areas = data.get("areas") or []
        
        if not areas:
            raise ValueError("at least one area is required")
        
        configs: list[AreaScanConfig] = []
        for area in areas:
            area_id = str(area.get("id") or area.get("area_id") or "").strip()
            target_path = str(area.get("path") or "").strip()
            
            if not target_path:
                continue
            
            if not area_id:
                area_id = target_path.replace("/", "_").replace("\\", "_")
            
            configs.append(AreaScanConfig(
                area_id=area_id,
                target_path=target_path,
                max_lines=clamp_int(
                    area.get("max_lines"),
                    DEFAULT_AREA_MAX_LINES,
                    100,
                    5_000_000,
                ),
                max_files=clamp_int(
                    area.get("max_files"),
                    DEFAULT_AREA_MAX_FILES,
                    1,
                    20_000,
                ),
                max_file_bytes=clamp_int(
                    area.get("max_file_bytes"),
                    DEFAULT_AREA_MAX_FILE_BYTES,
                    1_024,
                    50_000_000,
                ),
                mode=str(area.get("mode") or "app"),
                timeout_seconds=clamp_int(
                    area.get("timeout_seconds"),
                    DEFAULT_MAPPER_TIMEOUT_SECONDS,
                    5,
                    MAX_MAPPER_TIMEOUT_SECONDS,
                ),
            ))
        
        if not configs:
            raise ValueError("no valid areas provided")
        
        parallel = bool(data.get("parallel", False))
        
        append_log_line(f"multi_area_scan_started area_count={len(configs)} parallel={parallel}")
        
        # Run scans and emit progress per area
        results: list[AreaScanResult] = []
        
        if parallel and len(configs) > 1:
            # Parallel execution with progress events
            with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_AREAS, len(configs))) as executor:
                futures = {
                    executor.submit(scan_single_area, config, get_runs_dir(), get_repo_root()): config
                    for config in configs
                }
                
                # Emit initial status
                sio.emit("scan:multi:progress", {
                    "status": "started",
                    "total_areas": len(configs),
                    "completed": 0,
                    "message": f"Starting parallel scan of {len(configs)} areas",
                }, room=sid)
                
                completed_count = 0
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    completed_count += 1
                    
                    # Emit per-area progress
                    sio.emit("scan:area:progress", {
                        "area_id": result.area_id,
                        "status": "completed",
                        "files_included": result.files_included,
                        "lines_reviewed": result.lines_reviewed,
                        "run_id": result.run_id,
                    }, room=sid)
                    
                    # Update overall progress
                    sio.emit("scan:multi:progress", {
                        "status": "in_progress",
                        "total_areas": len(configs),
                        "completed": completed_count,
                        "current_area": result.area_id,
                    }, room=sid)
        else:
            # Sequential execution
            for i, config in enumerate(configs):
                sio.emit("scan:multi:progress", {
                    "status": "in_progress",
                    "total_areas": len(configs),
                    "completed": i,
                    "current_area": config.area_id,
                    "message": f"Scanning area {i + 1}/{len(configs)}: {config.area_id}",
                }, room=sid)
                
                result = scan_single_area(config, get_runs_dir(), get_repo_root())
                results.append(result)
                
                # Emit per-area progress
                sio.emit("scan:area:progress", {
                    "area_id": result.area_id,
                    "status": "completed",
                    "files_included": result.files_included,
                    "lines_reviewed": result.lines_reviewed,
                    "run_id": result.run_id,
                }, room=sid)
        
        # Calculate aggregated statistics
        total_files = sum(r.files_included for r in results)
        total_lines = sum(r.lines_reviewed for r in results)
        total_stubs = sum(r.stubs_detected for r in results)
        successful = sum(1 for r in results if r.status == "success")
        
        # Emit final aggregation
        sio.emit("scan:multi:complete", {
            "ok": True,
            "run_id": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8],
            "area_results": [
                {
                    "area_id": r.area_id,
                    "status": r.status,
                    "files_included": r.files_included,
                    "lines_reviewed": r.lines_reviewed,
                    "stubs_detected": r.stubs_detected,
                    "snapshot_path": r.snapshot_path,
                    "map_path": r.map_path,
                    "run_id": r.run_id,
                    "error_message": r.error_message,
                }
                for r in results
            ],
            "aggregated": {
                "total_areas": len(configs),
                "successful_areas": successful,
                "total_files": total_files,
                "total_lines": total_lines,
                "total_stubs": total_stubs,
            },
        }, room=sid)
        
        append_log_line(
            f"multi_area_scan_completed area_count={len(configs)} successful={successful} "
            f"total_files={total_files} total_lines={total_lines}"
        )
        
    except Exception as exc:
        append_log_line(f"scan:multi:error {exc}\n{traceback.format_exc()}")
        sio.emit("scan:multi:complete", {
            "ok": False,
            "error": str(exc),
        }, room=sid)


@sio.on("map:generate")
def handle_map_generate(sid, data):
    """Generate code map via Socket.IO with streaming progress."""
    try:
        payload = execute_map_request(
            data,
            progress_callback=lambda event: sio.emit("map:progress", event, room=sid),
        )
        sio.emit("map:complete", payload, room=sid)
    except subprocess.TimeoutExpired as exc:
        append_log_line(f"mapper_timeout details={exc}")
        sio.emit("map:complete", {
            "ok": False,
            "error": "mapper_timeout",
            "details": str(exc),
            "hint": "narrow the target scope or lower diagram/render options",
        }, room=sid)
    except Exception as exc:
        append_log_line(f"map:generate:error {exc}\n{traceback.format_exc()}")
        sio.emit("map:complete", {
            "ok": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }, room=sid)


@sio.on("discover:areas")
def handle_discover_areas(sid, data):
    """Discover scannable areas via Socket.IO."""
    try:
        repo_root = get_repo_root()
        custom_root = data.get("root")
        
        if custom_root:
            candidate = repo_root / custom_root
            if candidate.exists() and candidate.is_dir():
                repo_root = candidate
        
        max_areas = clamp_int(
            data.get("max_areas"),
            DEFAULT_MAX_AREAS,
            1,
            50,
        )
        max_lines_per_area = clamp_int(
            data.get("max_lines_per_area"),
            DEFAULT_MAX_LINES_PER_AREA,
            10_000,
            500_000,
        )

        def _run_discovery(target_sid: str, target_root: Path, target_max_areas: int, target_max_lines: int) -> None:
            try:
                append_log_line(f"area_discovery_started root={target_root} max_areas={target_max_areas}")
                discovered = discover_areas(target_root, target_max_areas, target_max_lines)
                total_lines = sum(a.estimated_lines for a in discovered)
                sio.emit("discover:areas:response", {
                    "ok": True,
                    "proposed_areas": [asdict(area) for area in discovered],
                    "total_estimated_lines": total_lines,
                }, room=target_sid)
                append_log_line(f"area_discovery_completed area_count={len(discovered)} total_lines={total_lines}")
            except Exception as exc:
                append_log_line(f"discover:areas:error {exc}")
                sio.emit("discover:areas:response", {
                    "ok": False,
                    "error": str(exc),
                }, room=target_sid)

        sio.start_background_task(_run_discovery, sid, repo_root, max_areas, max_lines_per_area)
        sio.emit("discover:areas:queued", {
            "ok": True,
            "status": "queued",
            "root": str(repo_root),
            "max_areas": max_areas,
            "max_lines_per_area": max_lines_per_area,
        }, room=sid)
    except Exception as exc:
        append_log_line(f"discover:areas:error {exc}")
        sio.emit("discover:areas:response", {
            "ok": False,
            "error": str(exc),
        }, room=sid)


# --- Main Entry Point ---


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve the Shufti web UI with Socket.IO.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind host.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Bind port.")
    return parser


def main() -> int:
    global _app_config
    
    args = build_parser().parse_args()
    
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    aispy_url = os.environ.get("SHUFTI_AISPY_URL", "").strip()
    if not aispy_url:
        aispy_url = f"http://{args.host}:8887"

    _app_config = AppConfig(
        host=args.host,
        port=args.port,
        repo_root=str(REPO_ROOT),
        mapper_script=str(MAPPER_SCRIPT),
        runs_dir=str(RUNS_DIR),
        dot_available=shutil.which("dot") is not None,
        aispy_url=aispy_url,
        default_mapper_timeout_seconds=DEFAULT_MAPPER_TIMEOUT_SECONDS,
        max_mapper_timeout_seconds=MAX_MAPPER_TIMEOUT_SECONDS,
        default_max_files=DEFAULT_MAX_FILES,
        default_max_lines=DEFAULT_MAX_LINES,
        default_max_file_bytes=DEFAULT_MAX_FILE_BYTES,
        max_browse_entries=DEFAULT_MAX_BROWSE_ENTRIES,
        log_path=str(LOG_PATH),
        log_url="/logs/shufti-ui",
        readme_path=str(README_PATH),
        readme_url="/docs/shufti-readme",
    )
    
    append_log_line(
        f"startup host={args.host} port={args.port} repo_root={_app_config.repo_root}"
    )
    
    print(
        f"Shufti UI listening on http://{args.host}:{args.port} "
        f"(repo root: {_app_config.repo_root})"
    )
    print(f"Socket.IO enabled at ws://{args.host}:{args.port}/socket.io/")
    
    # Use a server implementation that matches the selected Socket.IO async mode.
    if SOCKETIO_ASYNC_MODE == "gevent" and pywsgi is not None and WebSocketHandler is not None:
        server = pywsgi.WSGIServer(
            (args.host, args.port),
            app,
            handler_class=WebSocketHandler,
        )
        server.serve_forever()
    else:
        from werkzeug.serving import run_simple
        run_simple(args.host, args.port, app, threaded=True)


if __name__ == "__main__":
    raise SystemExit(main())
