# Lore

> **The institutional memory for your codebase. Persistent reasoning for Claude Code — so every session knows what every previous session decided, and why.**

```bash
git log    # shows what changed
lore log   # shows the lore (why it changed)
```

---

## What It Is

Lore is a **decision memory layer** for projects built with **Claude Code**. It sits alongside your project like `.git` — silent, automatic, and local. 

While version control tracks the evolution of your code, Lore captures the **"Lore" of your project**: the reasoning, rejected alternatives, and critical constraints that normally disappear when a Claude session ends. It integrates directly with Claude Code's hook system to ensure your project's institutional knowledge grows as fast as your code.

No documentation required. No human discipline required. No changes to how agents or developers work.

---

## How It Works

Lore operates silently in the background, synchronizing with your git workflow to capture reasoning exactly when it happens.

- **Observe** — The `lore-daemon` captures agent activity and reasoning as it happens. Every tool use, every thought process, and every file touch is recorded.
- **Distill** — When you commit code, Lore automatically analyzes the changes. It identifies which sessions contributed to the surviving code and distills the raw reasoning into structured decision records.
- **Promote** — As features merge into your main branch, their corresponding decisions are promoted to permanent storage. Reasoning for abandoned work is automatically filtered out.

This three-tier approach ensures your knowledge base only contains the "truth" of your production codebase, free from the noise of discarded iterations.

---

## Why Symbols Not Line Numbers

Lore links decisions to function and class symbols, not to line numbers. Line numbers change with every refactor; symbols are stable. This ensures that the reasoning behind `checkInternalIP()` follows the code even after it's moved or refactored.


---

## Installation

```bash
curl -fsSL https://raw.githubusercontent.com/amarlearning/lore/main/install.sh | bash
```

Done. Everything automatic from that point.

---

## Getting Started

1.  **Start the daemon**: Run `lore start` to begin capturing reasoning.
2.  **Initialize your project**: Run `lore init` in your project root. This installs:
    - **Git Hooks**: `post-commit` and `post-merge` hooks to automate distillation and promotion.
    - **Claude Code Hooks**: Registers the daemon in `.claude/settings.json` to capture lifecycle events.

---

## CLI Reference

Lore mirrors the tools you already know.

- `lore start` — Start the reasoning capture daemon.
- `lore stop` — Stop the reasoning capture daemon.
- `lore status` — Inspect your reasoning memory tiers.
- `lore log` — View decision history by commit hash.
- `lore show` — Drill into a specific decision.
- `lore query` — Semantic search across your entire institutional memory.


---

## Frequently Asked Questions

**1. Why do I need Lore?**
AI agents like Claude Code make critical decisions every session, but that reasoning disappears when the session ends. Lore captures the "why" behind your code, preventing "institutional amnesia" as your project grows.

**2. Do I need to write documentation manually?**
No. Lore is entirely automatic. It observes what Claude is already thinking and doing, then distills that into structured records without any extra effort from you.

**3. Does it change how I use Claude Code?**
Not at all. You continue working exactly as you do today. Lore sits silently in the background, integrated via hooks, and only speaks up when it has relevant historical context to share.

**4. How does Lore capture my thoughts?**
Lore uses a background daemon that listens to Claude Code's lifecycle events. It records every tool use, file touch, and reasoning block in a temporary "working memory" while you work.

**5. When does a "thought" become a "permanent record"?**
Lore mirrors the git lifecycle. Raw thoughts stay in `temp/` until you `git commit` (Distillation). Those records stay in `staging/` until you `git merge` to your main branch (Promotion).

**6. How does Claude actually use this data?**
Lore uses "just-in-time" memory injection. When Claude is about to touch a file, Lore intercepts the request, looks up relevant historical decisions, and injects them as context before the agent acts.

**7. Does Lore inject context during research or only when editing?**
Lore is proactive. It injects reasoning as soon as Claude **reads** a file. This ensures the agent is aware of critical constraints during the planning phase, before any code is written.

**8. Does this work with remote teams and PRs?**
Yes. Since Lore's data is version-controlled in the `.lore` directory, it travels with your repo. When you pull a teammate's merged branch, Lore automatically promotes their reasoning into your local memory.

**9. What happens if I squash or rebase my commits?**
Lore handles history rewrites naturally. If you squash multiple commits, Lore automatically re-distills the reasoning from all affected sessions into a single, high-fidelity record for the final commit hash.

**10. Where is my data stored?**
Lore is local-first. All reasoning and decision records are stored inside your repository in the `.lore` directory. Your institutional memory stays exactly where your code lives—under your control.

---

## Technical Architecture

Lore is built as three independent packages that work together:

```
lore/
├── lore-core/       # Core data models, storage logic, distillation utilities
├── lore-cli/        # Command-line interface (user-facing commands)
└── lore-daemon/     # HTTP server that listens to Claude Code hooks
```

### Three-Tier Storage Model

Lore uses a three-tier storage system to ensure only high-quality, production-relevant reasoning becomes permanent knowledge:

1. **`temp/`** (Raw Working Memory)
   - Stores raw Claude Code session data as it happens
   - Cleared automatically after each commit
   - **Never treat as truth** — contains discarded experiments and dead ends

2. **`staging/<branch>/`** (Distilled Records)
   - Structured decision records distilled from `temp/`
   - Contains only reasoning about code that survived the commit
   - Cleared after merge to main
   - **Never query as final** — still branch-specific

3. **`decisions/`** (Permanent Knowledge)
   - Production-grade decision records
   - Only grows when branches merge to main
   - Ghost reasoning filter ensures only decisions about surviving code are here
   - **This is your institutional memory** — safe to rely on

### Data Flow

```
Claude Code Session → temp/ (raw events)
         ↓
     git commit → distill → staging/ (branch-specific)
         ↓
     git merge → promote → decisions/ (permanent)
```

---

## Project Structure & Components

### lore-core
The heart of Lore — contains all shared logic:
- **Models**: Pydantic data models for `SessionData`, `DecisionRecord`, etc.
- **Store**: Utilities for finding/writing to `.lore/`, loading sessions, finding decisions
- **Distill**: Logic for extracting symbols from diffs and distilling reasoning
- **Constraints**: Loading architectural constraints from AGENTS.md

### lore-cli
User-facing command-line interface:
- All user commands: `init`, `start`, `stop`, `commit`, `merge`, `status`, `log`, `show`, `query`, `constraints`
- Git hook installation
- Claude Code hook registration

### lore-daemon
Background HTTP server (port 7340):
- Receives Claude Code lifecycle events via webhooks
- Writes raw session data to `temp/`
- Injects relevant decisions as context before tool use
- Handles 5 hook types: `UserPromptSubmit`, `PostToolUse`, `PreCompact`, `Stop`, `PreToolUse`

---

## Data Formats

### Decision Record (YAML)

Decision records are stored as YAML for token efficiency and Claude-friendliness:

```yaml
commit_hash: a3f9c2d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0
summary: Skip 2FA for internal IPs
why: Skipped 2FA for internal IPs due to SSO compliance requirement confirmed by legal
alternatives_rejected:
  - Enforce 2FA for all → broke internal deploy tooling
  - IP allowlist at firewall level → too ops-heavy
constraints:
  - Must not break internal deploy pipeline
  - Compliance review required before this block is removed
symbols:
  - checkInternalIP
files:
  - auth/middleware.js
```

### Session Data in temp/

Each session directory contains:
- `prompt.json` - Initial user prompt
- `tool_events.jsonl` - Stream of tool use events
- `compact.json` - Full session state before context compaction
- `stop.json` - Session termination timestamp

---

## Claude Code Hook Integration

Lore integrates with Claude Code via 5 lifecycle hooks registered in `.claude/settings.json`:

| Hook | Purpose | When It Fires |
|------|---------|----------------|
| `UserPromptSubmit` | Capture initial task intent | At session start |
| `PostToolUse` | Record every file touch and tool call | After every tool use |
| `PreCompact` | Capture full reasoning before context loss | Before Claude compacts its context |
| `Stop` | Seal the session | When session ends |
| `PreToolUse` | Inject relevant decisions | Before Claude reads/writes a file |

**Proactive Context Injection**: Lore injects decisions as soon as Claude **reads** a file, not just when it edits. This ensures the agent knows critical constraints during planning.

---

## Tech Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Language | Python 3.11+ | Excellent ecosystem for CLI tools and ML/LLM integration |
| CLI Framework | Typer | Modern, type-safe, beautiful CLI output |
| Web Server | FastAPI + Uvicorn | High-performance async server with automatic OpenAPI docs |
| Data Validation | Pydantic 2.0 | Type-safe data models with excellent error messages |
| Git Integration | GitPython | Robust git operations without shelling out |
| Storage Format | YAML | 2-3x more token-efficient than Markdown for Claude |
| Testing | pytest + pytest-cov | Industry-standard testing with coverage reporting |
| Linting/Formatting | ruff | Blazing-fast linter and formatter in one |
| Type Checking | mypy | Static type checking for robustness |

---

## Development & Contributing

### Local Setup

```bash
# Clone the repo
git clone https://github.com/amarlearning/lore.git
cd lore

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e "./lore-core[dev]"
pip install -e "./lore-daemon[dev]"
pip install -e "./lore-cli[dev]"
```

### Running Tests

```bash
# Run all tests with coverage
export PYTHONPATH=$PYTHONPATH:$(pwd)/lore-core/src:$(pwd)/lore-cli:$(pwd)/lore-daemon/src
pytest --cov=lore_core --cov=lore_cli --cov=lore_daemon

# Run pre-commit checks (same as CI)
./hooks/pre-commit
```

### Project Principles

All contributions must follow:
- **Clean Code**: Readability, meaningful names, small single-purpose functions
- **TDD**: Write tests *before* implementation. Aim for >80% coverage.
- **Functional Programming**: Prefer immutability, pure functions, Pydantic models
- **Pragmatic Programming**: Build what's necessary, avoid over-engineering

---

## Security & Privacy

Lore is designed with privacy as a first-class concern:

- **100% Local**: All data stays on your machine in `.lore/`
- **No Phone Home**: No data is sent to any external servers
- **Your Code, Your Lore**: Decision records live in your repo, under your control
- **No Secrets Stored**: Lore doesn't access or store API keys, credentials, or secrets
- **Git-Compatible**: `.lore/` can be committed to git to share institutional memory with your team

---

## What A Decision Looks Like

```yaml
commit_hash: a3f9c2d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0
summary: Skip 2FA for internal IPs
why: Skipped 2FA for internal IPs due to SSO compliance requirement confirmed by legal in ticket #234.
alternatives_rejected:
  - Enforce 2FA for all → broke internal deploy tooling
  - IP allowlist at firewall level → too ops-heavy
constraints:
  - Must not break internal deploy pipeline
  - Compliance review required before this block is removed
symbols:
  - checkInternalIP
files:
  - auth/middleware.js
```
