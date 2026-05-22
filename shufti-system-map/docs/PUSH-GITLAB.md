# Push to GitLab (Lightspeed internal)

GitLab CE host (from Lightspeed foundation docs): **`gitlab.lightspeed.internal`**, SSH port **2222**.

## 1. Create empty project

In GitLab UI: **New project** → name e.g. `shufti-system-map` (or `SAI-Shufti-System-Map`), visibility per your policy.

## 2. Add remote (from this directory or monorepo root)

```bash
git remote add gitlab "ssh://git@gitlab.lightspeed.internal:2222/<group>/shufti-system-map.git"
```

Replace `<group>` with your namespace (e.g. `lightspeed-engine`).

## 3. Push milestone branch

```bash
git push -u gitlab main
# or only the milestone tag:
git push gitlab refs/tags/shufti-map-2026.05.22-milestone
```

## 4. If hostname does not resolve

Use VPN/Tailscale DNS that resolves `gitlab.lightspeed.internal`, or add an `/etc/hosts` entry pointing at your GitLab VM IP (see `foundation/versioning systems/GitlAb/GitLab/docker-compose.yml`).

## Monorepo option

This bundle also lives under `SAI-Cursor-Validation/shufti-system-map/`. You may push the parent repo to GitLab instead of a standalone project; keep `VERSION` tagged when the map UI changes.
