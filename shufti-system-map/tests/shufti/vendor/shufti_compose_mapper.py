#!/usr/bin/env python3
# Pinned copy for SAI-Cursor-Validation CI (S0 offline tests).
# Sync from: Lightspeed-Engine/LSE-Core-2.0-2.1/scripts/shufti_compose_mapper.py
"""
Shufti compose / deployment topology mapper.

Produces architecture diagrams (Mermaid) similar to coupling reference visuals:
- high_level_overview
- component_coupling
- coupling_summary
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for compose mapping") from exc


COMPOSE_FILENAMES = {
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "standalone-deployment-docker-compose.yml",
}

URL_ENV_PATTERNS = (
    re.compile(r"^[A-Z0-9_]*URL$"),
    re.compile(r"^[A-Z0-9_]*_URL$"),
)


@dataclass
class ComposeNode:
    node_id: str
    label: str
    subtitle: str
    kind: str  # service | auth | bus | network | volume | orchestration


@dataclass
class ComposeEdge:
    source: str
    target: str
    relation: str


@dataclass
class ComposeGraph:
    source_path: str
    nodes: list[ComposeNode] = field(default_factory=list)
    edges: list[ComposeEdge] = field(default_factory=list)


def is_compose_file(path: Path) -> bool:
    name = path.name.lower()
    if name in COMPOSE_FILENAMES:
        return True
    return name.startswith("docker-compose") and name.endswith((".yml", ".yaml"))


def find_compose_file(targets: list[str], repo_root: Path | None = None) -> Path | None:
    for raw in targets:
        candidate = Path(raw).resolve()
        if candidate.is_file() and is_compose_file(candidate):
            return candidate
        if candidate.is_dir():
            for name in sorted(COMPOSE_FILENAMES):
                nested = candidate / name
                if nested.is_file():
                    return nested
    if repo_root is not None:
        for name in sorted(COMPOSE_FILENAMES):
            nested = repo_root / "LSE-StandAlone-Deployment" / name
            if nested.is_file():
                return nested
    return None


def mermaid_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value) or "node"


def node_mermaid_label(node: ComposeNode) -> str:
    safe_title = node.label.replace('"', "'")
    safe_sub = node.subtitle.replace('"', "'")
    return f'{mermaid_id(node.node_id)}["{safe_title}<br/><small>{safe_sub}</small>"]'


def classify_service(name: str, config: dict[str, Any]) -> str:
    lowered = name.lower()
    if "bus" in lowered:
        return "Message Bus"
    if lowered in {"sig-auth", "sigauth"} or "auth" in lowered:
        return "Auth Service"
    if lowered in {"redis", "mongodb-rocketchat", "chromadb-hydro", "qdrant-hydro"}:
        return "Infrastructure"
    if lowered in {"portal-gateway"}:
        return "Entry Point"
    if config.get("network_mode") == "host":
        return "Host Network Service"
    labels = config.get("labels") or {}
    if isinstance(labels, dict) and labels.get("lse.service_name"):
        return "LSE Service"
    return "Service"


def classify_volume(name: str) -> str:
    if name in {"sigid", "schemas", "keys", "sockets"}:
        return "Shared Data"
    return "Volume"


def parse_depends_on(config: dict[str, Any]) -> list[str]:
    raw = config.get("depends_on")
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, dict):
        return [str(key) for key in raw.keys()]
    return []


def host_from_env_value(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if "://" not in stripped:
        return None
    parsed = urlparse(stripped)
    host = parsed.hostname
    if host and host not in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return host.split(".")[0]
    return None


def load_compose_graph(compose_path: Path) -> ComposeGraph:
    data = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
    services: dict[str, Any] = data.get("services") or {}
    networks: dict[str, Any] = data.get("networks") or {}
    volumes: dict[str, Any] = data.get("volumes") or {}

    graph = ComposeGraph(source_path=str(compose_path))
    service_names = sorted(services.keys())

    graph.nodes.append(
        ComposeNode(
            node_id="docker_compose",
            label="Docker Compose",
            subtitle="Orchestration",
            kind="orchestration",
        )
    )

    for net_name in sorted(networks.keys()):
        graph.nodes.append(
            ComposeNode(
                node_id=f"net_{net_name}",
                label=net_name,
                subtitle="Bridge Network" if "net" in net_name else "Network",
                kind="network",
            )
        )

    for vol_name in sorted(volumes.keys()):
        graph.nodes.append(
            ComposeNode(
                node_id=f"vol_{vol_name}",
                label=vol_name,
                subtitle=classify_volume(vol_name),
                kind="volume",
            )
        )

    for service_name, config in sorted(services.items()):
        if not isinstance(config, dict):
            continue
        graph.nodes.append(
            ComposeNode(
                node_id=f"svc_{service_name}",
                label=service_name,
                subtitle=classify_service(service_name, config),
                kind="service",
            )
        )

    for service_name, config in services.items():
        if not isinstance(config, dict):
            continue
        sid = f"svc_{service_name}"
        graph.edges.append(
            ComposeEdge("docker_compose", sid, "orchestrates")
        )
        for dep in parse_depends_on(config):
            graph.edges.append(ComposeEdge(sid, f"svc_{dep}", "depends on"))
        for net in config.get("networks") or []:
            if isinstance(net, str):
                graph.edges.append(ComposeEdge(sid, f"net_{net}", "connects to"))
        if config.get("network_mode") == "host":
            for net_name in networks:
                graph.edges.append(
                    ComposeEdge(sid, f"net_{net_name}", "communicates via")
                )
        env = config.get("environment") or []
        env_items: list[str] = []
        if isinstance(env, list):
            env_items = [str(item) for item in env]
        elif isinstance(env, dict):
            env_items = [f"{key}={value}" for key, value in env.items()]
        for item in env_items:
            if "=" not in item:
                continue
            key, _, value = item.partition("=")
            if not URL_ENV_PATTERNS[0].match(key) and not URL_ENV_PATTERNS[1].match(key):
                continue
            host = host_from_env_value(value)
            if host and host in service_names and host != service_name:
                graph.edges.append(ComposeEdge(sid, f"svc_{host}", "uses"))
        for mount in config.get("volumes") or []:
            if not isinstance(mount, str):
                continue
            mount_name = mount.split(":")[0]
            if mount_name in volumes:
                graph.edges.append(ComposeEdge(sid, f"vol_{mount_name}", "shares"))

    deduped: dict[tuple[str, str, str], ComposeEdge] = {}
    for edge in graph.edges:
        deduped[(edge.source, edge.target, edge.relation)] = edge
    graph.edges = list(deduped.values())
    return graph


def render_markdown(graph: ComposeGraph) -> str:
    lines = [
        "# Shufti Compose Architecture Map",
        "",
        f"- Source: `{graph.source_path}`",
        f"- Services: `{sum(1 for n in graph.nodes if n.kind == 'service')}`",
        f"- Relationships: `{len(graph.edges)}`",
        "",
        "## Diagrams",
        "",
        "- `high_level_overview.mmd` — orchestration + network coupling",
        "- `component_coupling.mmd` — full component graph",
        "- `coupling_summary.mmd` — grouped coupling summary",
        "",
    ]
    return "\n".join(lines)


def _emit_edges(lines: list[str], edges: list[ComposeEdge], node_ids: set[str]) -> None:
    for edge in edges:
        if edge.source not in node_ids or edge.target not in node_ids:
            continue
        lines.append(
            f"  {mermaid_id(edge.source)} -->|\"{edge.relation}\"| {mermaid_id(edge.target)}"
        )


def render_high_level_overview(graph: ComposeGraph) -> str:
    lines = [
        "flowchart TB",
        "  classDef orch fill:#4c1d95,stroke:#a78bfa,color:#f8fafc",
        "  classDef svc fill:#1e3a5f,stroke:#60a5fa,color:#e2e8f0",
        "  classDef net fill:#312e81,stroke:#818cf8,color:#e2e8f0,stroke-dasharray:4 2",
    ]
    node_ids: set[str] = set()
    for node in graph.nodes:
        if node.kind not in {"orchestration", "service", "network"}:
            continue
        lines.append(f"  {node_mermaid_label(node)}")
        node_ids.add(node.node_id)
        if node.kind == "orchestration":
            lines.append(f"  class {mermaid_id(node.node_id)} orch")
        elif node.kind == "network":
            lines.append(f"  class {mermaid_id(node.node_id)} net")
        else:
            lines.append(f"  class {mermaid_id(node.node_id)} svc")

    overview_edges = [
        e
        for e in graph.edges
        if e.relation in {"orchestrates", "communicates via", "connects to", "depends on"}
    ]
    _emit_edges(lines, overview_edges, node_ids)
    return "\n".join(lines) + "\n"


def render_component_coupling(graph: ComposeGraph) -> str:
    lines = [
        "flowchart LR",
        "  classDef svc fill:#1e3a5f,stroke:#60a5fa,color:#f1f5f9",
        "  classDef auth fill:#312e81,stroke:#a78bfa,color:#f8fafc",
        "  classDef bus fill:#3b2f63,stroke:#c4b5fd,color:#f8fafc,stroke-dasharray:5 3",
        "  classDef net fill:#1e1b4b,stroke:#818cf8,color:#e2e8f0,stroke-dasharray:4 2",
        "  classDef vol fill:#134e4a,stroke:#5eead4,color:#ecfeff",
    ]
    node_ids = {node.node_id for node in graph.nodes}
    for node in graph.nodes:
        lines.append(f"  {node_mermaid_label(node)}")
        mid = mermaid_id(node.node_id)
        if node.kind == "auth" or "auth" in node.subtitle.lower():
            lines.append(f"  class {mid} auth")
        elif node.kind == "bus" or "bus" in node.subtitle.lower():
            lines.append(f"  class {mid} bus")
        elif node.kind == "network":
            lines.append(f"  class {mid} net")
        elif node.kind == "volume":
            lines.append(f"  class {mid} vol")
        else:
            lines.append(f"  class {mid} svc")
    _emit_edges(lines, graph.edges, node_ids)
    return "\n".join(lines) + "\n"


def _subgraph_nodes(graph: ComposeGraph, predicate) -> list[ComposeNode]:
    return [node for node in graph.nodes if predicate(node)]


def render_coupling_summary(graph: ComposeGraph) -> str:
    auth_names = {"sig-auth", "sigauth"}
    bus_names = {n.label for n in graph.nodes if "bus" in n.label.lower()}
    vol_names = {"schemas", "sigid", "keys", "sockets"}
    net_names = {n.label for n in graph.nodes if n.kind == "network"}

    def svc_id(name: str) -> str:
        return f"svc_{name}"

    lines = ["flowchart TB"]

    groups: list[tuple[str, list[str]]] = [
        ("Centralized Authentication", sorted(auth_names & {n.label for n in graph.nodes})),
        ("Message Bus Integration", sorted(bus_names)),
        ("Volume Sharing", sorted(vol_names & {n.label for n in graph.nodes})),
        (
            "Network-Based Coupling",
            sorted(net_names | {n.label for n in graph.nodes if n.kind == "service"}),
        ),
    ]

    included: set[str] = set()
    for title, members in groups:
        if not members:
            continue
        lines.append(f'  subgraph {mermaid_id(title)}["{title}"]')
        for member in members:
            node = next((n for n in graph.nodes if n.label == member), None)
            if node is None:
                continue
            lines.append(f"    {node_mermaid_label(node)}")
            included.add(node.node_id)
        lines.append("  end")

    summary_edges = [e for e in graph.edges if e.source in included and e.target in included]
    _emit_edges(lines, summary_edges, included)
    return "\n".join(lines) + "\n"


def write_compose_artifacts(
    graph: ComposeGraph,
    diagram_dir: Path,
    diagram_format: str = "mermaid",
) -> list[dict[str, Any]]:
    diagram_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        ("high_level_overview", "High-level architecture", render_high_level_overview(graph)),
        ("component_coupling", "Component descriptions and coupling", render_component_coupling(graph)),
        ("coupling_summary", "Modular coupling summary", render_coupling_summary(graph)),
    ]
    artifacts: list[dict[str, Any]] = []
    extension = "mmd" if diagram_format == "mermaid" else "dot"
    for name, description, content in specs:
        path = diagram_dir / f"{name}.{extension}"
        path.write_text(content, encoding="utf-8")
        artifacts.append(
            {
                "name": name,
                "kind": "diagram_source",
                "format": diagram_format,
                "path": str(path),
                "description": description,
            }
        )
    snapshot = diagram_dir / "compose-graph.json"
    snapshot.write_text(
        json.dumps(
            {
                "source_path": graph.source_path,
                "nodes": [asdict(node) for node in graph.nodes],
                "edges": [asdict(edge) for edge in graph.edges],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    artifacts.append(
        {
            "name": "compose_graph",
            "kind": "snapshot",
            "format": "json",
            "path": str(snapshot),
            "description": "Structured compose graph for viewers",
        }
    )
    manifest_path = diagram_dir / "diagram_manifest.json"
    manifest_path.write_text(json.dumps(artifacts, indent=2) + "\n", encoding="utf-8")
    artifacts.append(
        {
            "name": "diagram_manifest",
            "kind": "manifest",
            "format": "json",
            "path": str(manifest_path),
            "description": "List of generated compose diagram artifacts",
        }
    )
    return artifacts


def run_compose_map(
    compose_path: Path,
    run_dir: Path,
    output_format: str = "markdown",
) -> dict[str, Any]:
    graph = load_compose_graph(compose_path)
    diagram_dir = run_dir / "diagrams"
    artifacts = write_compose_artifacts(graph, diagram_dir, "mermaid")
    output_ext = "json" if output_format == "json" else "md"
    output_path = run_dir / f"code-map.{output_ext}"
    if output_format == "json":
        payload = {
            "source_path": graph.source_path,
            "mode": "compose",
            "nodes": [asdict(node) for node in graph.nodes],
            "edges": [asdict(edge) for edge in graph.edges],
            "artifacts": artifacts,
        }
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        rendered = output_path.read_text(encoding="utf-8")
    else:
        rendered = render_markdown(graph)
        output_path.write_text(rendered, encoding="utf-8")
    snapshot_path = run_dir / "snapshot.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "mode": "compose",
                "source_path": graph.source_path,
                "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "service_count": sum(1 for n in graph.nodes if n.kind == "service"),
                "edge_count": len(graph.edges),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "ok": True,
        "map_format": output_format,
        "map_path": str(output_path),
        "map_text": rendered[:500_000],
        "artifacts": artifacts,
        "compose_path": str(compose_path),
        "service_count": sum(1 for n in graph.nodes if n.kind == "service"),
        "edge_count": len(graph.edges),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Map docker-compose topology into architecture diagrams.")
    parser.add_argument("targets", nargs="+", help="Compose file path(s)")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", help="Output markdown/json path")
    parser.add_argument("--diagram-dir", help="Directory for mermaid artifacts")
    args = parser.parse_args()

    compose_path = find_compose_file(args.targets)
    if compose_path is None:
        raise SystemExit("no docker-compose file found in targets")

    run_dir = Path(args.diagram_dir) if args.diagram_dir else Path.cwd() / "compose-run"
    run_dir.mkdir(parents=True, exist_ok=True)
    result = run_compose_map(compose_path, run_dir, args.format)
    if args.output:
        Path(args.output).write_text(
            (run_dir / f"code-map.{ 'json' if args.format == 'json' else 'md'}").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    print(json.dumps({k: v for k, v in result.items() if k != "map_text"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
