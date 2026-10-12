# rosschambers/open-webui — fork notes

**This repository is PUBLIC.** Never commit credentials: no tokens, API keys, passwords,
`.env` files, decrypted secrets, or real values in examples. Deployment configuration and
secrets live in the private `serve-open-webui` repository and are referenced by name only.
Before every push, review the diff for secrets: `git diff origin/agents..HEAD`.

## Branches

- `main` — mirrors upstream `open-webui/open-webui` `main` (sync only, no local commits).
- `agents` — upstream release tag plus the named sub-agents patch. Rebased onto each new
  upstream release; releases tagged `v<upstream>-agents.<n>`.

Design: exocortex `docs/plans/2026-10-11-open-webui-primary-harness.md` (section "Design: named
sub-agents").
