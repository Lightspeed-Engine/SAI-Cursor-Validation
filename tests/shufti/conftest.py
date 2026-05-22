"""Shared paths and centralized test logging for Shufti slice tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.lib.selder_error_codes import CodedError
from tests.lib.test_log import TestLog

REPO_ROOT = Path(__file__).resolve().parents[2]
_TEST_LOG: TestLog | None = None


def _get_log() -> TestLog:
    global _TEST_LOG
    if _TEST_LOG is None:
        _TEST_LOG = TestLog()
    return _TEST_LOG


def _slice_id(item: pytest.Item) -> str:
    mark = item.get_closest_marker("slice")
    if mark and mark.args:
        return str(mark.args[0])
    return "UNKNOWN"
FIXTURES = REPO_ROOT / "tests" / "fixtures"
VENDOR_MAPPER = REPO_ROOT / "tests" / "shufti" / "vendor" / "shufti_compose_mapper.py"
LIGHTSPEED_ROOT = Path(
    os.environ.get("LIGHTSPEED_ENGINE_ROOT", "/mnt/lightspeed-data/Lightspeed-Engine"),
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "offline: no network; safe for pre-commit and PR CI")
    config.addinivalue_line("markers", "live: requires Shufti :3005 and/or AI-Spy :8887")
    config.addinivalue_line("markers", "slice(name): slice id S0–S8 per PLAN doc")


@pytest.fixture
def minimal_compose_path() -> Path:
    path = FIXTURES / "docker-compose.minimal.yml"
    assert path.is_file(), f"missing fixture: {path}"
    return path


@pytest.fixture
def vendor_mapper_module():
    import importlib.util
    import sys

    assert VENDOR_MAPPER.is_file(), f"missing vendor mapper: {VENDOR_MAPPER}"
    name = "shufti_compose_mapper_vendor"
    spec = importlib.util.spec_from_file_location(name, VENDOR_MAPPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def pytest_sessionstart(session: pytest.Session) -> None:
    mode = os.environ.get("SLICE_TEST_MODE", "offline")
    log = _get_log()
    log.session_start("pytest", mode)
    if os.environ.get("FINISH_RUN_DEFERRED") == "1":
        return
    try:
        from tests.lib.rich_report import print_session_banner

        print_session_banner("pytest", mode, log.path)
    except ImportError:
        pass


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    # Combined runner (run-shufti-slice-tests.sh) prints Rich summary once at the end.
    if os.environ.get("FINISH_RUN_DEFERRED") == "1":
        return
    if os.environ.get("TEST_LOG_SUMMARY") != "pytest":
        return
    log = _get_log()
    try:
        from tests.lib.rich_report import print_summary_from_log

        print_summary_from_log(log.path, runner_exit=exitstatus)
    except ImportError:
        pass


def pytest_runtest_setup(item: pytest.Item) -> None:
    _get_log().test_start(_slice_id(item), item.nodeid)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    outcome = yield
    report = outcome.get_result()
    if report.when != "call":
        return

    log = _get_log()
    slice_id = _slice_id(item)
    test_id = item.nodeid

    if report.passed:
        log.record_pass(slice_id, test_id)
    elif report.skipped:
        reason = ""
        if hasattr(report, "longrepr") and report.longrepr:
            reason = str(report.longrepr)[:500]
        try:
            log.record_skip(slice_id, test_id, reason or "skipped")
        except CodedError as exc:
            log.record_fail(slice_id, test_id, exc.code, exc.payload["message"])
    elif report.failed:
        code = "SAIV-TEST-0001"
        message = str(report.longrepr)[:800] if report.longrepr else "assertion failed"
        if call.excinfo is not None:
            if call.excinfo.typename == "CodedError":
                val = call.excinfo.value
                code = getattr(val, "code", code)
                message = str(val)[:800]
            elif call.excinfo.typename != "AssertionError":
                code = "SAIV-TEST-0003"
        log.record_fail(slice_id, test_id, code, message)
