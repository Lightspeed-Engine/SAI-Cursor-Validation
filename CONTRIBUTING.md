# Contributing to SAI Cursor Validation

Thank you for helping improve governed activity capture for Cursor.

## What to work on

See [cursor/PLAN-2026-05-18-governed-activity-correlator.md](cursor/PLAN-2026-05-18-governed-activity-correlator.md) and [cursor/FEATURE-CHECKLIST-2026-05-18.md](cursor/FEATURE-CHECKLIST-2026-05-18.md).

## Before opening a PR

```bash
bash cursor/scripts/run-phase-tests.sh 2
```

If you changed hook behavior and have a live Agent log in this workspace:

```bash
bash cursor/scripts/validate-live.sh
```

## PR guidelines

- One logical change per PR
- Match existing style in `cursor/scripts/hooks/` and `cursor-activity/src/`
- Do not commit `.cursor/activity/` (audit logs are local and gitignored)
- Update docs if you change hook schema or extension commands

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
