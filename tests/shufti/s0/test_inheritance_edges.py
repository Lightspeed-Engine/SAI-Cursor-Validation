"""Inheritance edges aggregate cross-sector class bases."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path("/mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts")
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from shufti_code_topology import build_inheritance_layer_edges, module_to_sector_map  # noqa: E402


def test_inheritance_edge_between_sectors() -> None:
    root = Path("/repo")
    files = [
        {
            "path": str(root / "core/services/child/service.py"),
            "module_name": "core.services.child.service",
            "classes": [{"qualified_name": "ChildService", "bases": ["BaseService"]}],
        },
        {
            "path": str(root / "core/services/base/service.py"),
            "module_name": "core.services.base.service",
            "classes": [{"qualified_name": "BaseService", "bases": ["object"]}],
        },
    ]
    module_to_sector = module_to_sector_map(files, root)
    edges = build_inheritance_layer_edges(files, module_to_sector)
    assert any(
        e["source"] == "core.services.child" and e["target"] == "core.services.base"
        for e in edges
    )
