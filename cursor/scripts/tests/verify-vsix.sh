#!/usr/bin/env bash
# Build cursor-activity VSIX and verify archive contents (CI + phase 2 gate).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
EXT_DIR="${ROOT}/cursor-activity"

cd "$EXT_DIR"

rm -f ./*.vsix

echo "Building VSIX..."
npm run package --silent

shopt -s nullglob
vsix_files=(./*.vsix)
if [[ ${#vsix_files[@]} -ne 1 ]]; then
  echo "FAIL: expected exactly one .vsix, found ${#vsix_files[@]}"
  exit 1
fi

VSIX="${vsix_files[0]}"
echo "VSIX: ${VSIX}"

if ! unzip -t "$VSIX" >/dev/null 2>&1; then
  echo "FAIL: VSIX is not a valid zip archive"
  exit 1
fi

required=(
  extension/package.json
  extension/dist/extension.js
  extension/dist/activity/store.js
  extension/dist/activity/tailer.js
  extension/dist/activity/types.js
)

missing=0
for path in "${required[@]}"; do
  if ! unzip -l "$VSIX" | awk '{print $4}' | grep -qxF "$path"; then
    echo "FAIL: missing in VSIX: $path"
    missing=$((missing + 1))
  fi
done

if [[ "$missing" -gt 0 ]]; then
  exit 1
fi

node -e "
const { execSync } = require('child_process');
const fs = require('fs');
const vsix = fs.readdirSync('.').filter((f) => f.endsWith('.vsix'));
if (vsix.length !== 1) process.exit(1);
const pkgJson = execSync('unzip -p ' + JSON.stringify(vsix[0]) + ' extension/package.json', {
  encoding: 'utf8',
});
const pkg = JSON.parse(pkgJson);
if (!pkg.name || !pkg.version) throw new Error('package.json missing name/version');
if (!pkg.engines?.vscode) throw new Error('package.json missing engines.vscode');
if (pkg.main !== './dist/extension.js') throw new Error('unexpected main: ' + pkg.main);
if (!pkg.contributes?.views) throw new Error('package.json missing contributes.views');
console.log('VSIX manifest OK:', pkg.name + '@' + pkg.version);
"

echo "PASS: VSIX build and contents verified"
