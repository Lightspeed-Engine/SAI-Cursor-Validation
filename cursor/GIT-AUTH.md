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

After setup, agents may run:

```bash
bash cursor/scripts/push-to-github.sh    # PUSH_YES=1 for non-interactive
bash cursor/scripts/run-phase-tests.sh 2
bash cursor/scripts/release.sh
```

`push-to-github.sh` calls `setup-git-auth.sh` automatically when `.env.local` exists.

## Security

| Do | Don't |
|----|--------|
| Keep token in `.env.local` only | Paste token in chat or commit it |
| Use repo-scoped fine-grained PAT | Use a classic `repo` token for all of GitHub |
| Revoke and replace if leaked | Share `.env.local` across machines in chat |

Long term: LSE agent identity (enrollment, short-lived caps) replaces shared PATs — see governed activity / sigchain direction.
