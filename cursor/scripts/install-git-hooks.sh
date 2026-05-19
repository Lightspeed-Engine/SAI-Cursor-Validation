#!/usr/bin/env bash
# Install repo-local git hooks (pre-commit: tests + coverage). Does not change global git config.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

chmod +x .githooks/pre-commit
git config --local core.hooksPath .githooks

echo "Installed git hooks for ${ROOT}"
echo "  core.hooksPath = .githooks"
echo "  pre-commit     → phase tests + coverage (>= ${COVERAGE_MIN:-85}%)"
echo ""
echo "Skip once:  git commit --no-verify"
echo "Uninstall:  git config --local --unset core.hooksPath"
