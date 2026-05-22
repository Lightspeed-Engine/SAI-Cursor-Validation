"""S0 PASS/FAIL — offline compose mapper (PLAN § S0, no HTTP)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.lib.selder_error_codes import CodedError

pytestmark = [pytest.mark.offline, pytest.mark.slice("S0")]

MIN_COUPLING_LINES = 28  # minimal fixture (full LSE compose is 80+ in PLAN live check)
MIN_EDGES = 8
MIN_SERVICES = 4


def test_s0_compose_mapper_produces_artifacts(
    minimal_compose_path: Path,
    vendor_mapper_module,
    tmp_path: Path,
):
    result = vendor_mapper_module.run_compose_map(
        minimal_compose_path,
        tmp_path,
        output_format="markdown",
    )
    if not result.get("ok"):
        raise CodedError("SHUFTI-0100", "run_compose_map returned not ok", result)

    run_dir = tmp_path
    diagrams = run_dir / "diagrams"
    for name in ("high_level_overview", "component_coupling", "coupling_summary"):
        mmd = diagrams / f"{name}.mmd"
        if not mmd.is_file():
            raise CodedError("SHUFTI-0101", f"missing artifact {name}", {"path": str(mmd)})

    snapshot = json.loads((run_dir / "snapshot.json").read_text(encoding="utf-8"))
    if snapshot.get("mode") != "compose":
        raise CodedError("SHUFTI-0101", "snapshot mode is not compose", snapshot)

    coupling = (diagrams / "component_coupling.mmd").read_text(encoding="utf-8")
    lines = coupling.splitlines()
    if len(lines) < MIN_COUPLING_LINES:
        raise CodedError(
            "SHUFTI-0102",
            f"component_coupling.mmd lines {len(lines)} < {MIN_COUPLING_LINES}",
        )
    edge_markers = sum(1 for line in lines if "-->" in line)
    if edge_markers < 5:
        raise CodedError("SHUFTI-0102", f"mermaid edges {edge_markers} < 5")

    graph = json.loads((diagrams / "compose-graph.json").read_text(encoding="utf-8"))
    edges = graph.get("edges") or []
    nodes = graph.get("nodes") or []
    service_nodes = [n for n in nodes if n.get("kind") == "service"]
    if len(edges) < MIN_EDGES:
        raise CodedError("SHUFTI-0102", f"edges {len(edges)} < {MIN_EDGES}")
    if len(service_nodes) < MIN_SERVICES:
        raise CodedError("SHUFTI-0102", f"services {len(service_nodes)} < {MIN_SERVICES}")


@pytest.mark.skipif(
    not __import__("os").environ.get("SYNC_VENDOR_MAPPER"),
    reason="Set SYNC_VENDOR_MAPPER=1 to compare vendor copy to LIGHTSPEED_ENGINE_ROOT",
)
def test_s0_upstream_mapper_in_sync_when_lightspeed_present(vendor_mapper_module):
    import os

    lightspeed = Path(os.environ["LIGHTSPEED_ENGINE_ROOT"])
    upstream_script = lightspeed / "LSE-Core-2.0-2.1/scripts/shufti_compose_mapper.py"
    if not upstream_script.is_file():
        pytest.skip("upstream shufti_compose_mapper.py not found")
    vendor = Path(__file__).resolve().parents[1] / "vendor" / "shufti_compose_mapper.py"

    def body(path: Path) -> str:
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith('"""') and "Shufti compose" in line:
                return "\n".join(lines[i:])
        return path.read_text(encoding="utf-8")

    assert body(vendor) == body(upstream_script), "vendor copy out of sync; re-copy from upstream"
