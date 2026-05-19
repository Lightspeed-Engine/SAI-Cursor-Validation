#!/usr/bin/env bash
# Install repo-local git hooks: pre-commit (local CI) + post-commit (auto-push to GitHub).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

chmod +x .githooks/pre-commit .githooks/post-commit
chmod +x cursor/scripts/run-ci-local.sh cursor/scripts/auto-push.sh cursor/scripts/tests/verify-vsix.sh

git config --local core.hooksPath .githooks
git config --local activity.autoPush true

echo "Installed git hooks for ${ROOT}"
echo ""
echo "  core.hooksPath     = .githooks"
echo "  activity.autoPush  = true"
echo ""
echo "  On every git commit:"
echo "    1. run-ci-local.sh  (phase 0–2 + VSIX + coverage >= ${COVERAGE_MIN:-85}%)"
echo "    2. post-commit      → git push origin (triggers GitHub Actions)"
echo ""
echo "  Full report: reports/ci-local-latest.txt"
echo "  Coverage HTML: coverage/index.html"
echo ""
echo "  One-time push auth: cp .env.local.example .env.local && bash cursor/scripts/setup-git-auth.sh"
echo ""
echo "  Disable auto-push:  git config --local activity.autoPush false"
echo "  Skip hooks once:    git commit --no-verify  (no tests, no push)"
echo "  Manual CI only:     bash cursor/scripts/run-ci-local.sh"
echo "  Manual push:        bash cursor/scripts/auto-push.sh"
echo "  Uninstall hooks:    git config --local --unset core.hooksPath"
