# Git push for agents (project-local)

Agents cannot join a GitHub org. This repo uses **`.env.local`** + **local-only** git config so any Cursor agent on this machine can `git push` without interactive login.

## One-time setup (human)

1. Create a [fine-grained PAT](https://github.com/settings/tokens?type=beta) for `Lightspeed-Engine/SAI-Cursor-Validation` with **Contents: Read and write**.
2. Authorize SSO for **Lightspeed-Engine** on the token if prompted.
3. In the repo root:

```bash
cp .env.local.example .env.local
# edit .env.local — set GITHUB_TOKEN=github_pat_...
bash cursor/scripts/setup-git-auth.sh
```

4. Never commit `.env.local` (already gitignored).

## Agent usage

After `bash cursor/scripts/install-git-hooks.sh`, a normal commit runs local CI and **auto-pushes** when tests pass:

```bash
git add -A && git commit -m "your message"
# → run-ci-local.sh → push → GitHub Actions
```

Manual commands:

```bash
bash cursor/scripts/run-ci-local.sh      # full report without committing
bash cursor/scripts/auto-push.sh         # push only
bash cursor/scripts/push-to-github.sh    # PUSH_YES=1, force-with-lease if needed
bash cursor/scripts/release.sh
```

`auto-push.sh` and `push-to-github.sh` call `setup-git-auth.sh` when `.env.local` exists.

## Security

| Do | Don't |
|----|--------|
| Keep token in `.env.local` only | Paste token in chat or commit it |
| Use repo-scoped fine-grained PAT | Use a classic `repo` token for all of GitHub |
| Revoke and replace if leaked | Share `.env.local` across machines in chat |

Long term: LSE agent identity (enrollment, short-lived caps) replaces shared PATs — see governed activity / sigchain direction.
