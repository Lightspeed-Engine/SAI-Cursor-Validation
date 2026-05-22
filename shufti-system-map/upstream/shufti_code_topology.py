#!/usr/bin/env python3
"""
Canonical filesystem / package topology export for Shufti code maps.

Produces code_topology.json consumed by filesystem-map.html and (later) AI-Spy harvest.
"""

from __future__ import annotations

import json
import hashlib
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shufti_diagram_theme import wrap_mermaid_diagram

TOPOLOGY_SCHEMA_VERSION = "1.1.0"
MAX_SECTOR_FILES_LISTED = 12
MAX_PACKAGE_EDGES = 120
ROLE_ORDER = ("gateway", "service", "core", "data", "integration", "support")
ROLE_HINTS = {
    "gateway": ("gateway", "api", "route", "server", "entry", "cli"),
    "core": ("core", "engine", "orchestr", "manager", "scheduler", "workflow"),
    "data": ("store", "db", "data", "schema", "model", "repo", "state"),
    "integration": ("mcp", "client", "adapter", "bridge", "socket", "bus", "queue"),
    "support": ("test", "docs", "scripts", "tool", "util", "config"),
}


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value) or "node"


def sector_key_for_module(module_name: str, relative_path: str) -> str:
    """Group files into product-meaningful components (not mount-path blobs)."""
    path_norm = (relative_path or "").replace("\\", "/")
    path_lower = path_norm.lower()
    module_lower = (module_name or "").lower()

    services_idx = path_lower.find("/core/services/")
    if services_idx >= 0:
        rest = path_lower[services_idx + len("/core/services/") :].split("/")
        if rest and rest[0]:
            return f"core.services.{rest[0]}"

    if "/core/common/" in path_lower or module_lower.endswith(".core.common"):
        return "core.common"

    scripts_idx = path_lower.find("/scripts/")
    if scripts_idx >= 0:
        return "scripts"

    if "sai-cursor-validation" in path_lower:
        if "/tests/" in path_lower:
            return "sai.tests"
        if "/cursor/" in path_lower:
            return "sai.cursor"
        if "/core/" in path_lower:
            return "sai.core"
        return "sai.validation"

    if ".core.services." in module_lower:
        tail = module_lower.split(".core.services.", 1)[1]
        service = tail.split(".", 1)[0]
        if service:
            return f"core.services.{service}"

    parts = [part for part in (module_name or "").split(".") if part]
    if "core" in parts:
        core_idx = parts.index("core")
        if core_idx + 1 < len(parts) and parts[core_idx + 1] == "services" and core_idx + 2 < len(parts):
            return f"core.services.{parts[core_idx + 2]}"
        if core_idx + 1 < len(parts) and parts[core_idx + 1] == "common":
            return "core.common"

    if len(parts) >= 2:
        return ".".join(parts[:2])
    if parts:
        return parts[0]
    path_parts = Path(relative_path).parts
    if len(path_parts) >= 2:
        return "/".join(path_parts[:2])
    if path_parts:
        return path_parts[0]
    return "root"


def sector_label(sector_id: str) -> str:
    if "/" in sector_id:
        return sector_id.replace("/", " / ")
    return sector_id.replace(".", " · ")


def summarize_patterns(patterns: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for pattern in patterns:
        name = str(pattern.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names[:6]


def file_fingerprint(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return {
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": digest.hexdigest(),
        }
    except OSError:
        return {"size_bytes": None, "mtime_ns": None, "sha256": None}


def topology_fingerprint(nodes: list[dict[str, Any]], package_edges: list[dict[str, Any]]) -> str:
    payload = {
        "nodes": [
            {
                "path": node.get("path"),
                "sector": node.get("sector_id"),
                "sha256": (node.get("fingerprint") or {}).get("sha256"),
            }
            for node in sorted(nodes, key=lambda item: str(item.get("path") or ""))
        ],
        "package_edges": sorted(
            package_edges,
            key=lambda item: (
                str(item.get("source") or ""),
                str(item.get("target") or ""),
                int(item.get("weight") or 0),
            ),
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def infer_component_role(sector_id: str, sample_files: list[str], patterns: list[str]) -> str:
    haystack = " ".join([sector_id, *sample_files, *patterns]).lower()
    for role, hints in ROLE_HINTS.items():
        if any(hint in haystack for hint in hints):
            return role
    return "service"


def _edge_counts(package_edges: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, int]]:
    inbound: dict[str, int] = defaultdict(int)
    outbound: dict[str, int] = defaultdict(int)
    for edge in package_edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        weight = int(edge.get("weight") or 1)
        outbound[source] += weight
        inbound[target] += weight
    return inbound, outbound


def _size_band(line_count: int, max_lines: int) -> str:
    if max_lines <= 0:
        return "sm"
    ratio = line_count / max_lines
    if ratio >= 0.66:
        return "xl"
    if ratio >= 0.33:
        return "lg"
    if ratio >= 0.12:
        return "md"
    return "sm"


def _activity_heat_stub(sector: dict[str, Any], max_lines: int) -> float:
    """Static readiness heat until AISpy/Braid overlays inject live activity."""
    line_pressure = (int(sector.get("line_count") or 0) / max(max_lines, 1)) * 0.55
    stub_pressure = min(int(sector.get("stub_count") or 0) / 12, 1.0) * 0.30
    pattern_pressure = min(int(sector.get("pattern_hits") or 0) / 18, 1.0) * 0.15
    return round(min(line_pressure + stub_pressure + pattern_pressure, 1.0), 3)


def enrich_components(
    sectors: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    package_edges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    inbound, outbound = _edge_counts(package_edges)
    max_lines = max((int(sector.get("line_count") or 0) for sector in sectors), default=1)
    files_by_sector: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        files_by_sector[str(node.get("sector_id") or "root")].append(node)

    enriched: list[dict[str, Any]] = []
    for sector in sectors:
        sector_id = str(sector.get("id") or "root")
        files = sorted(
            files_by_sector.get(sector_id, []),
            key=lambda item: (-int(item.get("line_count") or 0), str(item.get("path") or "")),
        )
        pattern_names: list[str] = []
        for file_node in files:
            for pattern in file_node.get("patterns") or []:
                if pattern not in pattern_names:
                    pattern_names.append(pattern)
        role = infer_component_role(
            sector_id,
            [str(path) for path in sector.get("sample_files") or []],
            pattern_names,
        )
        component = dict(sector)
        component.update({
            "role": role,
            "dependency_in": inbound.get(sector_id, 0),
            "dependency_out": outbound.get(sector_id, 0),
            "dependency_weight": inbound.get(sector_id, 0) + outbound.get(sector_id, 0),
            "size_band": _size_band(int(sector.get("line_count") or 0), max_lines),
            "static_heat": _activity_heat_stub(sector, max_lines),
            "patterns": pattern_names[:8],
            "drilldown_id": f"component:{sector_id}",
        })
        enriched.append(component)

    return sorted(
        enriched,
        key=lambda item: (
            ROLE_ORDER.index(item["role"]) if item["role"] in ROLE_ORDER else len(ROLE_ORDER),
            -int(item.get("dependency_weight") or 0),
            -int(item.get("line_count") or 0),
            str(item.get("id") or ""),
        ),
    )


def build_system_overview(
    components: list[dict[str, Any]],
    package_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate layout-ready system-map data; renderers should obey this model."""
    role_lanes = {role: idx for idx, role in enumerate(ROLE_ORDER)}
    lane_offsets: dict[str, int] = defaultdict(int)
    layout_nodes: list[dict[str, Any]] = []

    for component in components:
        role = str(component.get("role") or "service")
        lane = role_lanes.get(role, role_lanes["service"])
        row = lane_offsets[role]
        lane_offsets[role] += 1
        size_band = str(component.get("size_band") or "sm")
        width = {"xl": 280, "lg": 240, "md": 210, "sm": 180}.get(size_band, 180)
        height = {"xl": 132, "lg": 116, "md": 104, "sm": 92}.get(size_band, 92)
        layout_nodes.append({
            "id": component["id"],
            "label": component["label"],
            "role": role,
            "path_hint": component.get("path_hint"),
            "metrics": {
                "files": component.get("file_count", 0),
                "lines": component.get("line_count", 0),
                "stubs": component.get("stub_count", 0),
                "dependency_in": component.get("dependency_in", 0),
                "dependency_out": component.get("dependency_out", 0),
                "static_heat": component.get("static_heat", 0),
            },
            "layout": {
                "lane": role,
                "x": 72 + lane * 320,
                "y": 84 + row * 178,
                "width": width,
                "height": height,
                "size_band": size_band,
            },
            "overlay_slots": {
                "agent_presence": [],
                "activity_heat": None,
                "error_heat": None,
                "braid_streams": [],
            },
            "drilldown_id": component["drilldown_id"],
        })

    return {
        "kind": "system_component_map",
        "layout_engine": "shufti_static_lanes_v1",
        "lanes": [
            {"id": role, "label": role.title(), "order": idx}
            for idx, role in enumerate(ROLE_ORDER)
        ],
        "nodes": layout_nodes,
        "edges": [
            {
                "source": edge.get("source"),
                "target": edge.get("target"),
                "weight": edge.get("weight", 1),
                "relation": edge.get("relation", "package_import"),
            }
            for edge in package_edges
        ],
        "interaction_contract": {
            "hover": "show component metrics and current overlay summary",
            "click": "open component drilldown",
            "agent_pin_click": "open ephemeral agent card",
        },
    }


def build_component_drilldowns(
    components: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    file_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    files_by_sector: dict[str, list[dict[str, Any]]] = defaultdict(list)
    edge_counts: dict[str, int] = defaultdict(int)
    for node in nodes:
        files_by_sector[str(node.get("sector_id") or "root")].append(node)
    for edge in file_edges:
        edge_counts[str(edge.get("source") or "")] += 1
        edge_counts[str(edge.get("target") or "")] += 1

    drilldowns: dict[str, Any] = {}
    for component in components:
        component_id = str(component.get("id") or "root")
        files = sorted(
            files_by_sector.get(component_id, []),
            key=lambda item: (
                -edge_counts.get(str(item.get("id") or ""), 0),
                -int(item.get("line_count") or 0),
                str(item.get("path") or ""),
            ),
        )
        drilldowns[f"component:{component_id}"] = {
            "kind": "component_detail",
            "component_id": component_id,
            "label": component.get("label"),
            "role": component.get("role"),
            "summary": {
                "files": component.get("file_count", 0),
                "lines": component.get("line_count", 0),
                "stubs": component.get("stub_count", 0),
                "dependency_in": component.get("dependency_in", 0),
                "dependency_out": component.get("dependency_out", 0),
                "static_heat": component.get("static_heat", 0),
            },
            "files": [
                {
                    "id": file_node.get("id"),
                    "path": file_node.get("path"),
                    "module": file_node.get("module"),
                    "lines": file_node.get("line_count", 0),
                    "stubs": file_node.get("stub_count", 0),
                    "patterns": file_node.get("patterns", []),
                    "dependency_touch_count": edge_counts.get(str(file_node.get("id") or ""), 0),
                }
                for file_node in files[:80]
            ],
            "live_slots": {
                "agents": [],
                "xterm_stream": None,
                "braid_events": [],
                "priority_events": [],
            },
        }
    return drilldowns


def build_code_topology(
    *,
    analysis_root: Path,
    files: list[dict[str, Any]],
    module_edges: list[tuple[str, str]],
    targets: list[str],
    mode: str,
    header: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical topology document from analyzed file records."""
    root = analysis_root.resolve()
    sector_stats: dict[str, dict[str, Any]] = {}
    nodes: list[dict[str, Any]] = []
    package_edge_counts: dict[tuple[str, str], int] = defaultdict(int)

    for record in files:
        path = Path(str(record.get("path") or ""))
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = path.name
        module_name = str(record.get("module_name") or path.stem)
        sector_id = sector_key_for_module(module_name, relative)
        line_count = int(record.get("line_count") or 0)
        stub_count = int(record.get("stub_count") or 0)
        patterns = record.get("patterns") or []

        if sector_id not in sector_stats:
            sector_stats[sector_id] = {
                "id": sector_id,
                "label": sector_label(sector_id),
                "path_hint": sector_id.replace(".", "/"),
                "file_count": 0,
                "line_count": 0,
                "stub_count": 0,
                "pattern_hits": 0,
                "sample_files": [],
            }
        sector = sector_stats[sector_id]
        sector["file_count"] += 1
        sector["line_count"] += line_count
        sector["stub_count"] += stub_count
        sector["pattern_hits"] += len(patterns)
        if len(sector["sample_files"]) < MAX_SECTOR_FILES_LISTED:
            sector["sample_files"].append(relative)

        nodes.append({
            "id": relative,
            "path": relative,
            "module": module_name,
            "sector_id": sector_id,
            "line_count": line_count,
            "stub_count": stub_count,
            "patterns": summarize_patterns(patterns),
            "fingerprint": file_fingerprint(path),
        })

    module_to_sector = {
        str(record.get("module_name") or Path(str(record.get("path") or "")).stem): sector_key_for_module(
            str(record.get("module_name") or ""),
            Path(str(record.get("path") or "")).name,
        )
        for record in files
    }

    file_edges: list[dict[str, str]] = []
    for src_module, dst_module in module_edges:
        src_sector = module_to_sector.get(src_module, src_module.split(".")[0] if src_module else "root")
        dst_sector = module_to_sector.get(dst_module, dst_module.split(".")[0] if dst_module else "root")
        if src_sector != dst_sector:
            package_edge_counts[(src_sector, dst_sector)] += 1
        src_node = next(
            (node for node in nodes if node["module"] == src_module),
            None,
        )
        dst_node = next(
            (node for node in nodes if node["module"] == dst_module),
            None,
        )
        if src_node and dst_node and src_node["id"] != dst_node["id"]:
            file_edges.append({
                "source": src_node["id"],
                "target": dst_node["id"],
                "relation": "imports",
            })

    package_edges = [
        {
            "source": src,
            "target": dst,
            "weight": weight,
            "relation": "package_import",
        }
        for (src, dst), weight in sorted(
            package_edge_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:MAX_PACKAGE_EDGES]
    ]

    sectors = sorted(
        sector_stats.values(),
        key=lambda item: (-int(item["line_count"]), item["id"]),
    )
    components = enrich_components(sectors, nodes, package_edges)
    system_overview = build_system_overview(components, package_edges)
    component_drilldowns = build_component_drilldowns(components, nodes, file_edges)

    return {
        "schema_version": TOPOLOGY_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "analysis_root": str(root),
        "mode": mode,
        "targets": targets,
        "header": header or {},
        "summary": {
            "sector_count": len(sectors),
            "file_count": len(nodes),
            "line_count": sum(int(node["line_count"]) for node in nodes),
            "stub_count": sum(int(node["stub_count"]) for node in nodes),
            "package_edge_count": len(package_edges),
            "file_edge_count": len(file_edges),
            "topology_fingerprint": topology_fingerprint(nodes, package_edges),
        },
        "sectors": sectors,
        "components": components,
        "nodes": nodes,
        "edges": {
            "files": file_edges[:500],
            "packages": package_edges,
        },
        "views": {
            "system_overview": system_overview,
            "component_drilldowns": component_drilldowns,
        },
    }


def render_filesystem_overview_mermaid(topology: dict[str, Any]) -> str:
    """Package-grouped flowchart TB — readable filesystem overview for export."""
    sectors = topology.get("sectors") or []
    package_edges = (topology.get("edges") or {}).get("packages") or []
    lines = ["flowchart TB"]
    for sector in sectors:
        sector_id = str(sector.get("id") or "sector")
        safe = _safe_id(sector_id)
        label = str(sector.get("label") or sector_id).replace('"', "'")
        files = int(sector.get("file_count") or 0)
        lines_count = int(sector.get("line_count") or 0)
        stubs = int(sector.get("stub_count") or 0)
        lines.append(
            f'  subgraph {safe}["{label}<br/>{files} files · {lines_count} lines · {stubs} stubs"]'
        )
        for sample in (sector.get("sample_files") or [])[:4]:
            sample_safe = _safe_id(sample)
            sample_label = sample.replace('"', "'")
            lines.append(f'    {sample_safe}["{sample_label}"]')
        lines.append("  end")
    for edge in package_edges:
        src = _safe_id(str(edge.get("source") or ""))
        dst = _safe_id(str(edge.get("target") or ""))
        weight = int(edge.get("weight") or 1)
        lines.append(f"  {src} -->|{weight}| {dst}")
    body = "\n".join(lines) + "\n"
    return wrap_mermaid_diagram(body)


def write_code_topology(
    topology: dict[str, Any],
    output_dir: Path,
    *,
    write_mermaid: bool = True,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "code_topology.json"
    json_path.write_text(json.dumps(topology, indent=2) + "\n", encoding="utf-8")
    system_map_path = output_dir / "system_map.json"
    system_map_path.write_text(
        json.dumps(topology.get("views", {}).get("system_overview", {}), indent=2) + "\n",
        encoding="utf-8",
    )
    if write_mermaid:
        mermaid_path = output_dir / "filesystem_overview.mmd"
        mermaid_path.write_text(
            render_filesystem_overview_mermaid(topology),
            encoding="utf-8",
        )
    return json_path
