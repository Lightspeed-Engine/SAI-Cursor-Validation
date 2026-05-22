"""S0 — diagram manifest parsing and artifact URL building (regression for envelope format)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tests.shufti.conftest import LIGHTSPEED_ROOT

pytestmark = [pytest.mark.offline, pytest.mark.slice("S0")]

SCRIPTS_DIR = LIGHTSPEED_ROOT / "LSE-Core-2.0-2.1" / "scripts"
RUN_ARTIFACTS = SCRIPTS_DIR / "shufti_run_artifacts.py"
CODE_MAPPER = SCRIPTS_DIR / "shufti_code_mapper.py"


@pytest.fixture(scope="module")
def run_artifacts_module():
    if not RUN_ARTIFACTS.is_file():
        pytest.skip(f"missing upstream module: {RUN_ARTIFACTS}")
    import importlib.util

    spec = importlib.util.spec_from_file_location("shufti_run_artifacts_test", RUN_ARTIFACTS)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def code_mapper_module():
    if not CODE_MAPPER.is_file():
        pytest.skip(f"missing upstream mapper: {CODE_MAPPER}")
    import importlib.util

    spec = importlib.util.spec_from_file_location("shufti_code_mapper_test", CODE_MAPPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_envelope_manifest(run_artifacts_module, tmp_path: Path):
    diagram = tmp_path / "dep.mmd"
    diagram.write_text("flowchart LR\n  A-->B\n", encoding="utf-8")
    raw = {
        "artifacts": [
            {
                "name": "dependency_graph",
                "kind": "diagram_source",
                "format": "mermaid",
                "path": str(diagram),
                "description": "deps",
            }
        ],
        "errors": [{"diagram": "interaction_map", "error": "too large"}],
    }
    entries = run_artifacts_module.parse_diagram_manifest_payload(raw)
    assert len(entries) == 1
    assert entries[0]["name"] == "dependency_graph"


def test_parse_legacy_list_manifest(run_artifacts_module, tmp_path: Path):
    diagram = tmp_path / "class_map.mmd"
    diagram.write_text("classDiagram\n  class Foo\n", encoding="utf-8")
    raw = [
        {
            "name": "class_map",
            "path": str(diagram),
            "format": "mermaid",
        }
    ]
    entries = run_artifacts_module.parse_diagram_manifest_payload(raw)
    assert len(entries) == 1


def test_parse_rejects_dict_key_iteration_regression(run_artifacts_module):
    """Envelope dict must not be iterated directly (TypeError: string indices)."""
    raw = {
        "artifacts": [
            {
                "name": "dependency_graph",
                "path": "/tmp/dependency_graph.mmd",
                "format": "mermaid",
            }
        ],
        "errors": [],
    }
    # Old bug: for item in raw → item is "artifacts" / "errors" (str)
    with pytest.raises(TypeError):
        for item in raw:
            _ = item["path"]

    entries = run_artifacts_module.parse_diagram_manifest_payload(raw)
    assert len(entries) == 1


def test_parse_rejects_artifacts_as_string_path(run_artifacts_module):
    raw = {"artifacts": "/tmp/only-one-path.mmd", "errors": []}
    entries = run_artifacts_module.parse_diagram_manifest_payload(raw)
    assert entries == []


def test_parse_skips_entries_without_path(run_artifacts_module):
    raw = {
        "artifacts": [
            {"name": "bad"},
            {"name": "good", "path": "/tmp/good.mmd", "format": "mermaid"},
        ]
    }
    entries = run_artifacts_module.parse_diagram_manifest_payload(raw)
    assert len(entries) == 1
    assert entries[0]["name"] == "good"


def test_build_artifact_payloads_adds_urls(run_artifacts_module, tmp_path: Path):
    runs_dir = tmp_path / "runs"
    run_dir = runs_dir / "20260521T120000Z-deadbeef"
    diagram_dir = run_dir / "diagrams"
    diagram_dir.mkdir(parents=True)
    mmd = diagram_dir / "pattern_map.mmd"
    mmd.write_text("flowchart LR\n", encoding="utf-8")
    manifest = {
        "artifacts": [
            {
                "name": "pattern_map",
                "kind": "diagram_source",
                "format": "mermaid",
                "path": str(mmd),
                "description": "patterns",
            }
        ],
        "errors": [],
    }
    (diagram_dir / "diagram_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    payloads = run_artifacts_module.build_artifact_payloads(runs_dir, diagram_dir)
    assert len(payloads) == 1
    assert payloads[0]["url"] == "/artifacts/20260521T120000Z-deadbeef/diagrams/pattern_map.mmd"


def test_code_mapper_writes_envelope_manifest(code_mapper_module, tmp_path: Path):
    target = SCRIPTS_DIR / "shufti_run_artifacts.py"
    assert target.is_file()
    diagram_dir = tmp_path / "diagrams"
    analyses = [
        code_mapper_module.FileAnalyzer(
            target,
            SCRIPTS_DIR,
            code_mapper_module.DEFAULT_MAX_FILE_BYTES,
        ).analyze()
    ]
    artifacts, errors = code_mapper_module.write_diagrams(
        analyses,
        diagram_dir,
        "mermaid",
        False,
        skip_diagrams={"interaction_map"},
    )
    manifest_path = diagram_dir / "diagram_manifest.json"
    assert manifest_path.is_file()
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    assert isinstance(raw.get("artifacts"), list)
    assert len(raw["artifacts"]) >= 1
    assert all(isinstance(entry, dict) and entry.get("path") for entry in raw["artifacts"])
