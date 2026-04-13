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

## What A Decision Looks Like

```
Decision a3f9c2
────────────────────────────────────────────────
Date:     2026-03-10
Branch:   feature-auth
Symbols:  checkInternalIP() in auth/middleware.js

WHY
Skipped 2FA for internal IPs due to SSO compliance
requirement confirmed by legal in ticket #234.

ALTERNATIVES REJECTED
- Enforce 2FA for all → broke internal deploy tooling
- IP allowlist at firewall level → too ops-heavy

CONSTRAINTS — DO NOT VIOLATE WITHOUT REVIEW
- Must not break internal deploy pipeline
- Compliance review required before this block is removed
```
