"""module_to_sector_map uses full relative paths (not basename-only)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path("/mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts")
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from shufti_code_topology import module_to_sector_map  # noqa: E402


def test_module_to_sector_uses_core_services_path() -> None:
    root = Path("/repo/LSE-Core-2.0")
    files = [
        {
            "path": str(root / "core/services/sigauth/service.py"),
            "module_name": "core.services.sigauth.service",
        },
        {
            "path": str(root / "core/services/sigfile/service.py"),
            "module_name": "core.services.sigfile.service",
        },
    ]
    mapping = module_to_sector_map(files, root)
    assert mapping["core.services.sigauth.service"] == "core.services.sigauth"
    assert mapping["core.services.sigfile.service"] == "core.services.sigfile"
    assert mapping["core.services.sigauth.service"] != mapping["core.services.sigfile.service"]
