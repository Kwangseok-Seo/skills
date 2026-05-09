---
name: dream
description: "Memory consolidation pass — a reflective reorganize of `~/.claude/memory/` files. Reviews recent transcripts and existing memory, merges new signals into topic files, prunes contradicted or stale entries, and tightens the MEMORY.md index. Args: (none) = current project memory; `user` = user-scope memory at `~/.claude/memory/`; `all` = user-scope plus every project memory directory. Use when the user says: 'consolidate memory', 'clean up memory', 'dream', 'reflective memory pass', 'tighten my memory index'."
---

# Dream: Memory Consolidation

You are running **dream** — a reflective pass over memory files. Your job is to take what was recently learned and consolidate it into **durable, well-organized memory** so future sessions can orient quickly.

This skill assumes the standard Claude Code memory layout (`~/.claude/memory/` for user-scope, `~/.claude/projects/<project-id>/memory/` for project-scope) and the four memory types defined below. If a target memory directory does not exist, create it before writing.

---

## Memory schema (referenced throughout)

Memory files are markdown files with frontmatter. Four types:

| Type        | Stores                                                                | Body convention                                                  |
|-------------|-----------------------------------------------------------------------|------------------------------------------------------------------|
| `user`      | The user's role, goals, knowledge, preferences                        | Free prose                                                       |
| `feedback`  | Guidance from the user about how to work — corrections AND validated approaches | Lead with rule, then **Why:** + **How to apply:** lines |
| `project`   | Initiatives, deadlines, motivations specific to this project          | Lead with fact, then **Why:** + **How to apply:** lines          |
| `reference` | Pointers to external systems (Linear projects, Slack channels, dashboards) | Free prose                                                  |

Each memory file:

```markdown
---
name: {short slug}
description: {one-line — used for relevance lookup; be specific}
type: user | feedback | project | reference
---

{body}
```

The directory's `MEMORY.md` is a **flat index** (no frontmatter), one line per memory file:

```markdown
- [Title](file.md) — one-line hook
```

Keep `MEMORY.md` under ~200 lines / ~25 KB. Do not write memory body content directly into `MEMORY.md`.

---

## Args (invocation modes)

| Args     | Target MEMORY_DIR                                              | Target TRANSCRIPTS_DIR                                                  |
|----------|----------------------------------------------------------------|-------------------------------------------------------------------------|
| (none)   | The current project's memory directory                         | The current project's transcripts                                       |
| `user`   | `~/.claude/memory/` (create if missing)                        | All projects' transcripts (cross-project signals only)                  |
| `all`    | The above `user` pass plus every project memory dir, one by one | Each pass uses its own transcripts                                      |

**Path conventions**

- Project transcript directory: `~/.claude/projects/<project-id>/*.jsonl`
- Project memory directory: `~/.claude/projects/<project-id>/memory/`
- `<project-id>` is what Claude Code wrote when it recorded the session — list with `ls ~/.claude/projects/`.

**Mode-specific entry rules**

- **(none)**: Process only the project-id matching the current session's cwd.
- **`user`**: If `~/.claude/memory/` is missing, create it with an empty `MEMORY.md` index. In this mode store **only signals that generalize across projects** (user identity, global preferences, tool-asset patterns). Do not lift project-specific facts to user-scope.
- **`all`**: Run `user` first, then iterate every directory under `~/.claude/projects/` and run the (none)-mode flow once per project. Each iteration runs Phase 1–4 independently and emits its own short report. End with a combined summary.

---

## Phase 1 — Orient

For each target MEMORY_DIR:

- `ls <MEMORY_DIR>` to see what already exists.
- Read `<MEMORY_DIR>/MEMORY.md` to learn the current index.
- Scan only the **frontmatter** (name / description / type) of existing topic files. **Do NOT read full bodies** — the goal is to avoid duplicate writes, not to reinterpret existing content.

## Phase 2 — Gather recent signal

Find new information worth saving. Priority:

1. **Recent transcripts** — From the target TRANSCRIPTS_DIR, take only the **1–3 most recently modified** `*.jsonl` files. JSONL files are large; grep narrowly — never read end-to-end.

   bash:
   ```bash
   ls -t ~/.claude/projects/<project-id>/*.jsonl | head -3
   ```

   PowerShell:
   ```powershell
   Get-ChildItem ~/.claude/projects/<project-id>/*.jsonl |
     Sort-Object LastWriteTime -Descending | Select-Object -First 3
   ```

2. **Existing memory entries that have drifted** — facts that contradict current code or reality. Spot-check via grep / Read.

3. **Narrow keyword grep** — if a specific event comes to mind, search transcripts for that keyword only.
   ```bash
   grep -rn "<narrow term>" ~/.claude/projects/<project-id>/ --include="*.jsonl" | tail -50
   ```

Do not read transcripts cover-to-cover. Confirm only the things you *suspect are important*.

In `user` mode, run step 1 across **every project**, but cap each project at its 1–2 most recent files. Promote only cross-project common signals to user-scope.

## Phase 3 — Consolidate

For each item worth remembering, write or update a memory file at the **top level** of the target MEMORY_DIR, following the schema above.

- Pick the right type. Don't invent new types.
- For `feedback` and `project`, include **Why:** and **How to apply:** lines so future-you can judge edge cases.
- Skip items that don't belong in memory at all (code patterns, project structure, debugging recipes, anything already in `CLAUDE.md`). Even if the user explicitly asks, redirect — extract the *surprising* / *non-obvious* part instead.

Core moves:

- **Merge new signal into existing topic files** — don't create near-duplicate new files.
- **Convert relative dates to absolute** ("yesterday" → "2026-05-08") so memory stays interpretable later.
- **Delete refuted facts** — if today's investigation proved old memory wrong, *edit the original file*; don't accumulate corrections.
- **Mode discipline** — files in `user` mode go to user-scope only; project mode goes to that project only. Don't lift up or push down by mistake.

## Phase 4 — Prune and index

Tighten the target MEMORY_DIR's `MEMORY.md`:

- Keep under **200 lines** and ~**25 KB**.
- Each entry one line, **under ~150 chars**: `- [Title](file.md) — one-line hook`.
- Don't put body content directly in the index.

Actions:

- Remove pointers to stale / wrong / superseded memory.
- For lines over 200 chars, *move the content into a topic file* and shorten the line.
- Add pointers to newly-important memory.
- If two files contradict, fix the wrong one.

> Reconciliation with `CLAUDE.md` is not automated. If you find memory that **clearly contradicts** a `CLAUDE.md` statement, mention it in the report only — do not edit `CLAUDE.md` (user-owned).

---

## Report format

Emit one short block per processed mode (1 block for (none) / `user`; one per project for `all`, plus a combined summary):

```
[Mode] (none | user | <project-id>)

- Added: <filename> (type=<type>) — <why>
- Updated: <filename> — <what signal, what changed>
- Removed: <filename> — <why no longer valid>
- Index: <lines before → after, lines changed>

CLAUDE.md contradictions found (only when present): <one line>
```

If nothing changed, say so explicitly ("already tidy — no changes").

---

## Don'ts

- **Don't read memory bodies in full** — frontmatter only in Phase 1, narrow grep only in Phase 2.
- **Don't create speculative wikilinks or filenames** — `MEMORY.md` lines must point to files that actually exist.
- **Don't bypass the type schema** — no fifth type, no nested categories.
- **Don't save items the schema excludes**, even on explicit user request — instead surface what was actually surprising.
- **Don't lift project-specific facts to user-scope** in `user` mode — only generalizable signals.
- **Don't auto-trigger** — this skill is non-trivial and only runs when the user asks for it explicitly.
