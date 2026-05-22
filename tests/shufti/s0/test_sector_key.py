"""Sector grouping for HQ component maps (shufti_code_topology)."""

from __future__ import annotations

import pytest

import sys

pytestmark = [pytest.mark.offline, pytest.mark.slice("S0")]
from pathlib import Path

SCRIPTS = Path("/mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/scripts")
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from shufti_code_topology import sector_key_for_module  # noqa: E402


def test_core_service_sector_from_path() -> None:
    key = sector_key_for_module(
        "mnt.x.core.services.agent_enrollment.service",
        "mnt/lightspeed-data/Lightspeed-Engine/LSE-Core-2.0-2.1/core/services/agent_enrollment/service.py",
    )
    assert key == "core.services.agent_enrollment"


def test_core_common_sector() -> None:
    key = sector_key_for_module(
        "core.common.logger",
        "core/common/logger.py",
    )
    assert key == "core.common"


def test_sai_tests_sector() -> None:
    key = sector_key_for_module(
        "home.legion.SAI-Cursor-Validation.tests.shufti.conftest",
        "home/legion/SAI-Cursor-Validation/tests/shufti/conftest.py",
    )
    assert key == "sai.tests"
