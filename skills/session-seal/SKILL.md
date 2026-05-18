---
name: session-seal
description: "Session snapshot sealer — captures the current Claude Code session's raw transcript and adds Why/How frontmatter (intent + approach) so a future session can resume cleanly. Saves under `<cwd>/.claude/sessions/`. Proposes chain links (continues-why, continues-how) by scanning recent sealed snapshots. Use when the user says: 'seal this session', 'session-seal', 'save session', 'snapshot the session', 'wrap up this session'."
---

# Session-Seal: capture session intent for resumable handoff

`session-seal` writes a **sealed snapshot** of the current Claude Code session so a future session can pick up cleanly. The full raw transcript is preserved verbatim, and a small **Why / How** frontmatter captures the session's intent and approach — enough that scanning a folder of past sessions reveals what each one was about in seconds.

This is a **manual** skill. It runs only when the user invokes it explicitly (e.g. `/session-seal`, "seal this session").

---

## What gets written

```
<cwd>/.claude/sessions/
└── YYYY-MM-DD - {short why}.md
```

Each file contains:

```yaml
---
id: "YYYYMMDDHHmm"
title: "YYYY-MM-DD - {short why}"
type: session
session-id: "<claude-code-session-id-or-derived>"
project: "<cwd basename>"
date: YYYY-MM-DD
why: "one-line intent of this session"
how: "one-line approach / methodology"
continues-why: "[[previous session title]]"   # optional, omit if new chain
continues-how: "[[previous session title]]"   # optional, omit if new chain
status: sealed
tags: [kebab, case, two-to-four]
---

# Original conversation

## user
...
## assistant
...
```

The body (raw conversation) is **immutable** once sealed. New interpretations go in a new session.

---

## Core concepts

- **Why** — one-line intent of *this* session. Not a project-wide goal ("build the trading bot"), not a single tool call ("edit `config.py`"). Something in between — e.g. *"compare backtest results of strategy A and B"*.
- **How** — one-line approach. E.g. *"audited three repos, debated tradeoffs, agreed on v0 skeleton"*. The *method* the session actually used, not the tools.
- **Chain** — `continues-why` and `continues-how` link this session to the most recent sealed snapshot in the same save directory whose Why or How is a *continuation*. They are **independent axes**: intent may continue while the approach changes (or vice versa). Either or both may be empty — that simply means a new chain starts here.
- **Sealed = immutable** — the body is never rewritten after sealing.

---

## Workflow

### Phase 1 — Locate the active transcript

Find the JSONL Claude Code is currently writing for this session. The most recently modified `.jsonl` under `~/.claude/projects/` is usually the active one.

bash:
```bash
ls -t ~/.claude/projects/*/*.jsonl | head -1
```

PowerShell:
```powershell
Get-ChildItem ~/.claude/projects/*/*.jsonl |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

If multiple sessions may be active concurrently, ask the user to confirm the path.

### Phase 2 — Resolve the save directory

- Default: `<cwd>/.claude/sessions/` — where `<cwd>` is the current working directory.
- Override: if `SESSION_SEAL_DIR` is set in the environment, use it verbatim.
- Create the directory if missing.

### Phase 3 — Convert the transcript to markdown

This skill ships with `convert_transcript.py` in the same directory as this `SKILL.md`. Run it on the JSONL from Phase 1:

bash:
```bash
python <skill-dir>/convert_transcript.py <transcript.jsonl> > /tmp/session-seal-body.md
```

PowerShell:
```powershell
python <skill-dir>\convert_transcript.py <transcript.jsonl> |
  Out-File -Encoding utf8 $env:TEMP\session-seal-body.md
```

`<skill-dir>` is the directory containing this SKILL.md. If you need to discover it programmatically, `Glob` for `**/session-seal/convert_transcript.py` under the Claude plugins root.

The helper renders user/assistant turns as `## role` headers and folds tool uses / tool results into code blocks. Tool output longer than 4000 chars is truncated with a marker.

### Phase 4 — Scan recent sealed snapshots (chain candidates)

Read **only the frontmatter** of up to the 3 most recent sealed snapshots in the save directory:

bash:
```bash
ls -t <save-dir>/*.md | head -3
```

PowerShell:
```powershell
Get-ChildItem <save-dir>/*.md |
  Sort-Object LastWriteTime -Descending | Select-Object -First 3
```

For each file, read only the block between the first pair of `---`. Do **not** read bodies — frontmatter has everything needed.

From that scan, pick at most one **Why-chain candidate** (most recent sealed snapshot whose Why is a direct continuation of this session's Why) and one **How-chain candidate** (same for How). They may be the same snapshot, different snapshots, or absent.

Continuation is a semantic judgment, not a keyword match. Ask: *"Is this session's intent a direct continuation of that one's intent?"*

### Phase 5 — Propose Why / How / chain / filename / tags in a single round

Present everything to the user in **one** prompt:

```
Save to: `<save-dir>/{filename}.md`

Proposed:
- Why: {one-line}
- How: {one-line}
- continues-why: [[<title>]] | (new chain start)
- continues-how: [[<title>]] | (new chain start)
- filename: `YYYY-MM-DD - {short why}.md`
- tags: [tag1, tag2, ...]

Accept as-is, or point out only the fields you want to change.
```

Handling:
- Acceptance / "yes" / blank → commit all proposals as-is, go to Phase 6.
- Partial correction → replace only the named field(s), keep the rest. No second confirmation round.
- Rejection / postpone → exit without writing.

**Never ask twice for the same field.** If the response is ambiguous, re-prompt at most once, in a single combined round.

### Phase 6 — Write the sealed snapshot

Build the final file:
1. Frontmatter block (Phase 5 result, `status: sealed`).
2. `# Original conversation` header.
3. The converted markdown from Phase 3.

Strip filesystem-unsafe characters from the filename: `:`, `/`, `\`, `?`, `*`, `"`, `<`, `>`, `|`.

Write the file. **Do not modify the converted body.**

### Phase 7 — Report

Tell the user:

```
✓ Sealed: <save-dir>/{filename}.md

Why: {final why}
How: {final how}
Continues-why: [[previous title]] | (new chain start)
Continues-how: [[previous title]] | (new chain start)
```

---

## Don'ts

- **Don't read sealed bodies** during the chain scan — frontmatter only. Bodies can be large.
- **Don't invent chain links** — `continues-why` / `continues-how` must point at a snapshot that actually exists in the save directory.
- **Don't rewrite the conversation body** — any new interpretation belongs in a new session.
- **Don't auto-trigger** — run only when the user invokes the skill explicitly.
- **Don't seal a session whose Why / How the user did not confirm.** Skill-only judgment is not a seal.

---

## Customization

Defaults are intentionally fixed for simplicity. Edit this SKILL.md to change them:

- **Save directory** — change Phase 2's default if `<cwd>/.claude/sessions/` doesn't fit your workflow. Common alternative: a personal wiki at `~/wiki/Sessions/<project>/`.
- **Chain scan depth** — Phase 4 reads the 3 most recent snapshots. Lower = faster, higher = better chain coverage in long-lived projects.
- **Tool output truncation length** — edit `MAX_TOOL_OUTPUT` in `convert_transcript.py` (default 4000 chars).
- **Auto-recall on session start** — not bundled by design. If you want previous Why/How injected automatically when a session starts, register a `SessionStart` hook in `~/.claude/settings.json` that reads the latest sealed snapshot's frontmatter and prints it. Kept out of this skill to keep the install standalone.
