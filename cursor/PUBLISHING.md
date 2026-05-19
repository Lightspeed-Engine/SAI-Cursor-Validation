# Publishing: Cursor Activity Correlator

## What users install

| Deliverable | How users get it |
|-------------|------------------|
| **VSIX extension** (`cursor-activity`) | OpenVSX, GitHub Release `.vsix`, or **Install from VSIX** locally |
| **Hook kit** | Copy from `cursor/` or run `cursor/scripts/install-project-hooks.sh` |

## CI publish pipeline (plan)

Repository: https://github.com/Lightspeed-Engine/SAI-Cursor-Validation

Publishing is automated on **version tags** `cursor-activity-v*` (see `.github/workflows/publish.yml`).

| Step | Registry | CI job | When it runs |
|------|----------|--------|----------------|
| 1. Test | — | `phase-tests` | Every tag (after PR tests passed) |
| 2. Build VSIX | — | `build-vsix` | Every tag |
| 3. GitHub Release | GitHub | `github-release` | Every tag (attaches `.vsix`) |
| 4. OpenVSX | [open-vsx.org](https://open-vsx.org) | `publish-openvsx` | Tag + `OPEN_VSX_TOKEN` secret set |
| 5. npm | [npmjs.com](https://www.npmjs.com) | `publish-npm` | **Later** — when `@agent-governance/*` (or hook SDK) packages exist |

GitLab mirrors the same stages in `.gitlab-ci.yml` (`publish` stage, manual OpenVSX/npm until variables are set).

## OpenVSX vs npm

| Channel | `cursor-activity` extension | Shared SDK (future) |
|---------|----------------------------|---------------------|
| **OpenVSX** | **Yes** — primary marketplace for VSIX | N/A |
| **npm** | **No** — use VSIX/OpenVSX, not `npm install` | **Yes** — `@agent-governance/*` when extracted |
| **GitHub Releases** | **Yes** — CI attaches `.vsix` on tag | Optional tarballs |

`npm` in `cursor-activity/package.json` is **build tooling only** until a separate publishable library is split out.

## Secrets (GitHub → Settings → Secrets)

| Secret | Used for |
|--------|----------|
| `OPEN_VSX_TOKEN` | `publish-openvsx` job (`ovsx publish`) |
| `NPM_TOKEN` | Future `publish-npm` job (npm automation token) |

## Manual release (until CI secrets are set)

1. Bump `version` in `cursor-activity/package.json`.
2. `cd cursor-activity && npm ci && npm run compile && npm run package`
3. `bash ../cursor/scripts/run-phase-tests.sh 2`
4. `bash cursor/scripts/release.sh 0.1.0` then `git push origin main && git push origin cursor-activity-v0.1.0`

**First-time remote sync** (GitHub repo created with README/LICENSE only):

```bash
bash cursor/scripts/push-to-github.sh
# or: PUSH_YES=1 bash cursor/scripts/push-to-github.sh
```
5. CI creates GitHub Release with VSIX; OpenVSX runs if token is set.

## Hooks (v0)

Hook scripts are **not** published to npm. Install from this repo or `install-project-hooks.sh`.
