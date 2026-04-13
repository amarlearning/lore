# AGENTS.md

Context for AI coding agents working on the Lore codebase.

---

## What This Project Is

Lore is a CLI tool and background daemon that gives AI agents persistent memory across sessions. It integrates with Claude Code's hook system to capture agent reasoning, then distills it into structured decision records keyed by git commit hash.

Two components:
- **`lore-daemon`** — local HTTP server (port 7340) that receives Claude Code lifecycle hook events (launched via `lore start`)
- **`lore` CLI** — git-mirrored commands for managing the three-tier `.lore/` directory

---

## Language & Stack

**Python.** Use `pyproject.toml` for packaging.

Key dependencies:
- `typer` or `click` — CLI framework
- `fastapi` + `uvicorn` — lore-daemon HTTP server
- `anthropic` — Anthropic SDK for distillation LLM calls
- `gitpython` — git integration (diff reading, hook installation)
- `watchdog` — file system watching fallback for non-Claude Code tools
- `sentence-transformers` or Anthropic embeddings API — semantic search index

---

## Project Structure

```
lore/
  src/
    lore/
      cli/          ← lore CLI commands (init, commit, merge, log, query, etc.)
      daemon/       ← lore-daemon HTTP server and hook receivers
      distill/      ← LLM distillation logic (temp/ → staging/)
      promote/      ← promotion logic (staging/ → decisions/)
      query/        ← semantic search over decisions/
      hooks/        ← git hook installers and Claude Code hook registration
      models/       ← data models for sessions, decisions, events
  tests/
  docs/             ← product documentation (do not modify without reason)
  pyproject.toml
  AGENTS.md
  README.md
```

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Build & Test

```bash
pytest                        # run all tests
pytest tests/unit/            # unit tests only
pytest tests/integration/     # integration tests (require git)
mypy src/                     # type checking
ruff check src/               # linting
ruff format src/              # formatting
```

---

## Coding Standards & Philosophy

Follow these principles strictly for all contributions:

- **Clean Code**: Prioritize readability, meaningful names, and small, single-purpose functions.
- **TDD (Test-Driven Development)**: Write tests *before* implementation. Ensure 100% coverage for core logic.
- **Functional Programming**: Prefer immutability, pure functions, and high-order functions where pragmatic. Avoid side effects in core logic.
- **Pragmatic Programming**: Focus on building what is necessary, avoid over-engineering, and ensure the code is robust and easy to change.
- **Immutability**: Treat data as immutable whenever possible. Use Pydantic models for structured data.

---

## Key Architectural Constraints

Read [docs/architecture.md](docs/architecture.md) before touching the core pipeline. Critical constraints:

**Three-tier storage — never skip a tier:**
- `temp/` is raw, cleared per commit. Never treat it as truth.
- `staging/` is distilled, cleared per merge. Never query it as final.
- `decisions/` is permanent, grows only on merge to main.

**Commit hash is the primary ID.** Decision files are named `<git-commit-hash>.md`. Never use Lore-specific IDs.

**Symbols not line numbers.** Decisions link to function/class names, not line numbers. Line numbers change; symbols are stable.

**Ghost reasoning filter.** Only reasoning about code that survived the commit enters staging. Only decisions from branches that reached main enter decisions/. This is the core correctness guarantee — do not compromise it.

**lore-daemon runs on port 7340.** This is registered in `.claude/settings.json` by `lore init`. Do not change the port without updating the hook registration.

---

## Claude Code Hook Events Used

Lore uses five of Claude Code's lifecycle hooks:

| Hook | Purpose |
|------|---------|
| `UserPromptSubmit` | Capture task intent at session start |
| `PostToolUse` | Record every file touch (structured JSON) |
| `PreCompact` | Capture full session state before context compaction — most important |
| `Stop` | Seal the session, mark ready for distillation |
| `PreToolUse` (Write/Edit/MultiEdit) | Inject relevant decisions before Claude touches known files |

---

## What Gets Written to temp/

Each session writes to `.lore/temp/<session_id>/`:
```
prompt.json         ← UserPromptSubmit payload
tool_events.jsonl   ← PostToolUse stream, one JSON object per line
compact.json        ← PreCompact full session state
stop.json           ← Stop event, timestamp
```

---

## Distillation Prompt

The distillation LLM call receives:
1. The committed diff (what actually survived)
2. `UserPromptSubmit` events — what the agent was asked to do
3. `PostToolUse` sequence — what it did, in order
4. `PreCompact` captures — reasoning before compaction
5. Existing `decisions/` for touched symbols — prior context
6. Instruction to extract: why this approach, what was rejected, what assumptions exist, what constraints must be preserved

Output is a structured markdown decision record written to `staging/<branch>/<commit-hash>.md`.

---

## Git Hooks Installed by `lore init`

```
.git/hooks/post-commit  → runs `lore commit`
.git/hooks/post-merge   → runs `lore merge`
```

These must be idempotent — `lore init` run twice should not duplicate hooks.

---

## Testing Patterns

- Unit test distillation logic with fixture session data — do not call real LLM APIs in unit tests
- Integration tests should use a real git repo (tmp directory), real `.lore/` structure
- Test the ghost reasoning filter explicitly: sessions that touched rejected symbols must not appear in staging
- Test multi-repo session routing: two sessions with different working directories must route to different `.lore/temp/` paths
