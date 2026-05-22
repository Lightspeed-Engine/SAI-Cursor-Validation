# Shufti error signaling (verified in repo)

**Verification date:** 2026-05-21  
**Paths scanned:** `LSE-Core-2.0-2.1/scripts/shufti_code_mapper.py`, `shufti_ui_server.py`, `LSE-Core-2.0-2.1/core/common/error_codes.py`, `core/common/selder_error_codes.py`

## Summary

| Kind | Present? | Where |
|------|----------|--------|
| `SHUFTI-####` SELDER operational codes (like `AISPY-0900`) | **No** | Not in Shufti scripts or `error_codes.py` |
| `PATTERN_CODES` (FAC, ADP, SM, …) | **Yes** | `shufti_code_mapper.py` — design-pattern labels in maps, not faults |
| `IP_HEADER` with `document_id: SPEC-SELDER-DOCUMENT-STANDARD` | **Yes** | Mapper JSON/markdown header metadata |
| Socket/HTTP `error` strings | **Yes** | `shufti_ui_server.py` — informal keys, not coded |

If you added `SHUFTI-*` codes in another branch, machine, or doc, point the agent at that path; they are **not** in the scanned upstream tree.

## What AI-Spy uses (reference pattern)

`MCP/mcp_server/agent_detection_daemon.py` defines `AISPY_CODES` as `(code, category, default_message)` tuples, e.g. `AISPY-0900` startup failures.

Shufti does **not** mirror that module today. Troubleshooting should use log lines + response payloads below until `SHUFTI_CODES` is added to `core/common/error_codes.py` and wired into the server.

## Current Shufti UI / Socket errors (informal)

From `shufti_ui_server.py` responses (`ok: false` or error fields):

| Key / symptom | Likely cause |
|---------------|----------------|
| `mapper_failed` | `shufti_code_mapper.py` exited non-zero; read stderr in run dir / server log |
| `mapper_timeout` | Scan exceeded `timeout_seconds` |
| `target path does not exist` | Bad path in scan config |
| `log not found` / `readme not found` / `artifact not found` | HTTP static asset 404 |
| Generic `error: str(exc)` | Handler exception; see `data/shufti_ui/shufti_ui_server.log` |
| `areas:list:error` | Log line prefix; check traceback in log |
| `discover:areas:error` | Discovery worker failed on `root` |
| `map:generate:error` | Socket map generation path failed |

Log file (typical): `Lightspeed-Engine/data/shufti_ui/shufti_ui_server.log`

## Mapper analysis errors (non-fatal)

`shufti_code_mapper.py` collects per-file failures in `analysis_errors[]` (strings like `skipped path due to analysis error: …`). The run can still succeed with partial files. Check snapshot JSON `analysis_errors` and header `analysis_errors` count.

## Pattern codes (not errors)

```text
<<FAC>> Facade   <<ADP>> Adapter   <<SM>> State Machine
<<REG>> Event Registry   <<DIS>> Dispatcher   <<TB>> Token Bucket   <<HASH>> Hash
```

Defined in `PATTERN_CODES` in `shufti_code_mapper.py`.

## Recommended SELDER alignment (when implementing)

1. Add `SHUFTI_CODES` dict to `LSE-Core-2.0-2.1/core/common/error_codes.py` and register in `ALL_ERROR_CODES`.
2. Import in `shufti_ui_server.py` / `shufti_code_mapper.py`; return `{ ok: false, code: "SHUFTI-0xxx", message: "..." }` on Socket and HTTP paths.
3. Map existing informal keys (`mapper_failed`, `mapper_timeout`, …) to stable codes.
4. Update this file and [SKILL.md](SKILL.md) with the canonical table.

Until then, agents must **not** invent `SHUFTI-*` numbers in docs or skills.
