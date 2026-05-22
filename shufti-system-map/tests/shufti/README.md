# Shufti + AI-Spy slice tests

Canonical plan: `docs/PLAN-2026-05-21-shufti-aispy-phased-slices.md`

## Quick commands

```bash
npm run precommit:shufti      # S0 + S2 + S5 (merge gate)
npm run test:shufti:contract  # S3 + S8 xfail contracts
RUN_LIVE=1 npm run test:shufti:live   # S1 + S8 ports
```

On failure, read **`reports/shufti-slice-latest.jsonl`** — each line has `error_code`, `recovery`, `slice`, `test_id`. Codes live in `core/shared/selder-error-codes.json`.

**Rich console output** (Lightspeed-style): summaries and failure panels print at the end of `run-shufti-slice-tests.sh`. Disable with `TEST_LOG_RICH=0`. Per-line live telemetry: `TEST_LOG_RICH_LIVE=1`. Pytest-only Rich summary: `TEST_LOG_SUMMARY=pytest` (without `FINISH_RUN_DEFERRED=1`).

## Layout

```
tests/shufti/
  s0/   compose mapper (vendor copy, offline)
  s1/   AI-Spy daemon sockets (live)
  s2/   topology merge (tsx)
  s3/   braid bridge contracts (xfail)
  s5/   sectional stitch (tsx)
  s8/   stack scripts (partial)
  vendor/shufti_compose_mapper.py
tests/fixtures/docker-compose.minimal.yml
```
