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

## The named sub-agents patch

A Workspace Model with **"Available as sub-agent"** on (`meta.capabilities.subagent`) is a named
agent. `delegate_task` gains an optional `agent` argument, whose enum and descriptions are built per
request from the agents the user can access. The child chat runs on the agent's own model,
instructions, tools, terminal and features only. The parent's system prompt and tools don't leak
in, and a background result resumes the parent on the parent's own model. Without `agent`, behavior
is upstream's. No database migration: switching back to the stock image just ignores the flag.

| File | Change |
|------|--------|
| `backend/open_webui/utils/named_agents.py` | All agent logic (listing, spec injection, child run) |
| `backend/open_webui/tools/builtin.py` | `delegate_task(..., agent='')` |
| `backend/open_webui/utils/tools.py` | Per-request `agent` enum on the `delegate_task` spec |
| `backend/open_webui/utils/subagents.py` | `delegate()` hooks; agent names kept through result batching; neutral named-agent prompt |
| `src/lib/constants.ts`, `.../Models/Capabilities.svelte`, `.../Models/ModelDefaultsPanel.svelte` | The toggle (hidden in global defaults) |
| `src/lib/components/chat/Messages/SubagentResultRow.svelte` | "*name* finished" and an Open chat link |

**Tests:** `uv run --no-project --with pytest python -m pytest test/named_agents -q` (the module loads
by file path, so no backend dependencies are needed). Frontend: `npm run check` must report no new
errors in the touched files compared with the upstream tag (upstream has thousands of existing ones).

**Known gap:** `list_agents` reads `app.state.MODELS`, which only refreshes when a client loads the
model list. Agents created through the API are invisible until then; editor-made ones are fine.

## Rebasing onto a new upstream release

```bash
git fetch upstream --tags
git checkout agents
git rebase --onto <new-tag> <old-tag> agents      # for example v0.13.0 v0.12.0
uv run --no-project --with pytest python -m pytest test/named_agents -q
npm ci && npm run check                            # compare touched files against <new-tag>
git diff <new-tag>..agents                         # secret review: public repository
git push --force-with-lease origin agents          # rebased branch: the one allowed force push
git tag v<new>-agents.1 && git push origin v<new>-agents.1
```

Then build and deploy from `serve-open-webui` (`./build-image.sh`, `./ship-image.sh`, bump `image:`,
`./deploy.sh`). Back up the data volume first.
