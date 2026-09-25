---
name: session-retro
description: "Session retrospective — records rule verdicts in a ledger, and shows the user only two tables: Remove (isolate · restore · archive · fix-or-drop · rarely-relevant) and Add (🟢 new rules and reinforcements). Every probability comes from counting the ledger. Nothing is published or moved without a human GATE. Run it before sealing the session. Args: (none) = one full pass; free text = an axis or scope hint. Use when the user says: 'session retro', 'retro', 'retrospective', 'look back at this session', 'what did we learn', 'turn the lessons into a rule', 'prune unused rules'."
---

<what-to-do>

Run one retrospective pass before closing the session. The order is fixed — **verdicts -> 4 axes x 2 lenses -> 🟢 verdict -> ledger and cards -> final message (Remove and Add tables) -> human GATE -> execute -> (optional) corpus node.**

Output format follows [RETRO-FORMAT.md](./RETRO-FORMAT.md); a real run is in [examples/worked-example.md](./examples/worked-example.md).

**Nothing is published or moved without the human GATE.** Self-graded auto-approval hardens a false recommendation into an always-loaded rule.

**Every ratio or probability used as evidence comes from [`ledger.py`](./ledger.py) output. Never assign one in words.** The tables stand in for reading, so an uncalibrated number is a rubber stamp (measured in the design review: of five card probabilities first assigned in words, four were constants fixed by the card's own trigger condition). Measure sizes (chars) with Python.

</what-to-do>

<supporting-info>

## When this runs

Before the session ends, while the conversation is still live, so the record of what was published or moved stays in the transcript. If you use the bundled `session-seal` skill, run this **before** sealing — the sealed snapshot then carries the evidence. **Only the corpus node comes after sealing** — a node's sources must be sealed sessions.

## Where rules live — location is state

This skill assumes **one rule = one file**. Always-on guardrails are published to `~/.claude/rules/*.md`, which Claude Code loads as global instructions across projects. A rule's state is the folder its file sits in:

| Folder | State | Context |
|---|---|---|
| `~/.claude/rules/` | loaded | loaded every session |
| `~/.claude/rules-probation/` | isolated | not loaded — watch whether the behaviour holds without the rule |
| `~/.claude/rules-archive/` | archived | not loaded |

The probation folder must be a **sibling outside** `rules/`. `rules/` is read recursively, so a folder inside it would still be loaded and the isolation would be void.

## The ledger and `ledger.py`

- Ledger: `~/.claude/session-retro/verdicts.csv` (change the folder with `SESSION_RETRO_DIR`). **Only `ledger.py` writes it** — never edit it by hand. The first `add` creates it. Verdicts are stored as English tokens, so this ledger is not shared with the Korean `session-retro-ko`.
- Revision (rev) = a hash of the rule file's content. Editing a rule starts a fresh observation window for it.
- Probability: the baseline failure rate p = the share of sessions in which a loaded rule failed. On an isolate row, P is "the chance an average rule works this many sessions in a row"; on a fix-or-drop row, P is "the chance an average rule fails at least this often". The smaller P, the less this rule looks like an average one. **While the ledger is empty there is no baseline and no probability proposal** — cards appear as verdicts accumulate.
- Exit codes: `0` ok · `3` violation (fix the input and run again) · **anything else = the tool failed → leave the ledger alone and report to the user.**
- Thresholds live in the constants block at the top of `ledger.py`, the single authority. This document does not copy the numbers.
- Run: `python <skill-dir>/ledger.py <command> …` (Python 3.8+). `<skill-dir>` is the directory holding this SKILL.md — if you do not know it, Glob for `**/session-retro/ledger.py`. `add`, `cards` and `gate` also take `--date <YYYY-MM-DD> --project <cwd basename> --slug <working title>` (`stats` and `leaks` take a rule name only). Tests are in `tests/` next to it.

| Command | When |
|---|---|
| `add --slug S --file rows.json` | step 4 — write verdicts (a single violation writes zero rows). **A new slug every retro** — an existing session key exits 3. Use `--append` only for more rows from the same retro |
| `cards --slug S` | step 4 — the Remove table and reference lines |
| `stats <rule>` | step 4 — evidence for a reinforcement row in Add |
| `leaks <rule>` | step 7 — right before accepting an isolation |
| `gate --slug S --rule R --proposal P --decision D --note N` | steps 4 and 7 — once per Remove decision (rejections too). P is the card's proposal value verbatim. On accept it moves the file |

Optional environment variables — without them only that feature drops out. The recurrence line and `leaks` say "not configured / not scanned", so it cannot be mistaken for an empty result; `sealed N` is simply left out of the evidence column:

| Variable | Turns on |
|---|---|
| `SESSION_SEAL_DIR` | `sealed N` in card evidence — sealed sessions over the window, next to the retro count, which exposes sessions that never got a retro. Same variable as the bundled `session-seal` |
| `SESSION_RETRO_CORPUS` | the recurrence rate on the Add reference line — the folder holding the step 8 corpus node files |
| `SESSION_RETRO_PROJECTS` | `leaks` also scans `<that folder>/*/CLAUDE.md` |

## Step 1 — Verdicts

Judge the `rules/` rules that bore on this session, plus **every rule in `rules-probation/`**. Isolated rules are not in context, so read their files — if the situation that called for the behaviour never came up, the verdict is `irrelevant`. If the step 3 grep turns up an **archived rule** this session needed, judge it too (that is the only way an archived rule comes back).

- The verdict is one of `worked` · `partly-worked` · `did-not-work` · `irrelevant`, **as a bare token**. Qualifiers, caveats and "but by luck" go in the note.
- The note is a concrete event — it is shown to the user as a "failure behind" line under the Remove table. Never just the rule's name. For an isolated rule: "the situation that called for it -> what was actually done".
- **Do not hide a failure.** If a rule existed and you still walked into what it warns about, write that — it is the only input to fix-or-drop.
- A loaded rule that had nothing to do with this session gets no row (`irrelevant` is for isolated rules only). Memory is not judged.
- **Check that isolation holds**: if the session's opening context shows the content of a rule from `rules-probation`, isolation is void — do not judge, report it to the user.
- Print as working text, one line per item.

## Step 2 — 4 axes x 2 lenses

Axes: **what went well / what went wrong / what was hard / what was learned.** Lenses: **engineering / business.** Working text — raw material for the sealed snapshot and the corpus node.

- Every item is **anchored to a concrete event in this session**. Quote numbers, output, or error text when you can. An abstract exhortation is not an item.
- **Never leave the mistakes axis empty.** Put the agent's own mistakes first.
- The business lens is not about money: users, progress, the shape of the artifact, collaboration friction (on a learning project, learning efficiency).
- Hard is not wrong — it is where the cost was high, and the candidate for changing tools next time.
- Write what was learned as "when X, do Y". If a 🟢 candidate pops up that is not here, the earlier steps were too thin.

## Step 3 — 🟢 verdict

The judgment is **binary**: `🟢 candidate (type)` or `unclassified (one-line reason)`. No intensity grades — a low grade buries an item for good. `unclassified` does not mean worthless, it means not triaged yet.

- **Duplicate check**: loaded rules are in context, free. On top of that, **grep** `rules-probation/` and `rules-archive/` — this closes the back door through which a rule missing from context gets republished.
- **Do not reinforce an isolated or archived rule** — write a step 1 verdict row instead and the Remove table proposes restoring it (failing without the rule is exactly what the isolation experiment is there to observe).
- Do not use frequency (number of sources) as importance — a one-off insight can outrank a repeated annoyance. Overlap with other projects' memory or notes is a partial view; check it at publish time.

| If the node is… | Artifact | Format authority |
|---|---|---|
| An always-on behavioural guardrail | **rule** (`~/.claude/rules/*.md`) | [RULE-FORMAT.md](./RULE-FORMAT.md) |
| A repeatable procedure with inputs and outputs | **skill** | your skill-authoring tool (e.g. `skill-creator`) |
| An irreversible, surprising, real trade-off decision | **ADR** (in the repo) | your project's ADR format, else the mini-spec below |
| A fact about reuse, or user feedback | **memory** | the bundled `dream` skill |
| Multi-agent orchestration | **workflow** | only if your harness supports one |
| Already enforced by an existing rule | **nothing** — observe only, unclassified | — |

**ADR mini-spec**, when the project has no format of its own: first sentence = the decision + why + the cost you accept (say NO explicitly for a rejection). One paragraph by default. Write one only when all three hold: reversal is expensive AND it is surprising without context AND a real trade-off existed.

## Step 4 — Ledger and cards

1. Put the step 1 and step 3 verdicts in `rows.json` (a temp folder) — `[{"rule": "verify-your-evidence", "verdict": "partly-worked", "note": "…"}, …]`.
2. `ledger.py add` -> `ledger.py cards`. On exit 3, fix the input as stderr says and run again. If a verdict for an isolated rule is missing, `cards` stops with 3.
3. **Keep a `rarely-relevant` row only if that rule's `Scope` section is narrow.** What the row measures is not "was the situation rare" but "did retros pay attention to the rule" — so it also catches broad rules nobody scored (measured: a reporting rule that applies to almost every implementation session was scored in only 4 of 31 retros and got flagged). For each row you drop, one line of reason in the working text plus `gate --proposal rarely-relevant --decision reject --note "retro filter: broad scope"` — so it does not come back every retro.
4. For each reinforcement row in Add, attach `ledger.py stats <rule>` as evidence.

## Step 5 — Final message

**Remove table -> Add table -> GATE prompt**, nothing else. Remove comes first — seeing what to cut before adding is the brake. Format in [RETRO-FORMAT.md](./RETRO-FORMAT.md).

## Step 6 — Human GATE

- Take answers by row number. `fix-or-drop` takes **fix / isolate / reject**, other Remove rows take **accept / reject**, Add rows take **accept / reject / edit**. **Say that rejecting and rewording are legitimate outcomes.**
- Do not reduce this to option buttons — make the user read the tables and answer by number.
- On Add rows, surface **past rejections** as caveats (project memory's publication log; your corpus's rejection marks if you keep one), so a rejected proposal does not return under a new name. Past rejections on Remove rows are appended by the script as `rejected n×`.

## Step 7 — Execute

Only what was accepted.

- **Remove**: one `ledger.py gate` per decision — **record rejections too** (so the same proposal does not come back every retro).
  - Before accepting an isolate or rarely-relevant row, run `ledger.py leaks <rule>`. For places that carry the rule's content (hooks · CLAUDE.md · MEMORY.md), ask the user whether to keep them. If this skill's own files point at the rule by name, fix them — but not the recorded outputs in `examples/`, which are past facts. An isolated rule drops out of context from the next session — that is when the standing cost goes down.
  - fix-or-drop: **fix** = `gate --proposal fix-or-drop --decision accept`, then rewrite under RULE-FORMAT's reinforcement discipline (the rev changes and a fresh window starts) · **isolate** = `gate --proposal isolate --decision accept` · **reject** = `gate --proposal fix-or-drop --decision reject`.
- **Add**: **read** the format authority, then publish. Rules load every session, so length is a standing cost — follow RULE-FORMAT's size discipline.
- Finally, one line each in project memory for **what was published, rejected, and left unclassified** — the past-rejection caveats of the next retro.

## Step 8 (optional) — Corpus node

Only worth doing if you keep a retrospective store that spans sessions. If you do not, stop at step 7.

Nodes are filed into five category files — the same names as the categories in [RETRO-FORMAT.md](./RETRO-FORMAT.md)'s working text. Keep the names even without a corpus; they force you to say *what kind* of thing this is.

| File | Holds |
|---|---|
| `a-mistakes.md` | Something that went wrong and could have gone otherwise |
| `b-insights.md` | Something learned that changes future behaviour |
| `c-improvements.md` | A process or tooling change worth making |
| `d-deferred.md` | An agreement postponed, plus the condition for revisiting it |
| `e-recurring.md` | A pattern that has now shown up across several sessions |

The only node shape `ledger.py` reads: a `### {node title}` line, and within the 11 lines right below it `sources: [[YYYY-MM-DD - session title]], …` (the earliest date is the session the node was born in). When the same node is observed again in another session, add a link to its sources. Point `SESSION_RETRO_CORPUS` at the folder and the Add reference line counts "the share of single-source nodes recorded again in later retros".

Back-link each published artifact from its node as `✅ published (rule:<file>, date)`. Isolating or archiving does not edit nodes — the ledger and file location are the authority on current state; `✅ published` is publication history.

## Never

- ❌ Publish or move anything without the human GATE
- ❌ Assign an evidential ratio or probability in words — `ledger.py` output only
- ❌ Hand-edit the ledger CSV, or touch the ledger after a failure other than exit 3
- ❌ Skip the verdict for an isolated rule, or reuse another retro's slug
- ❌ Cite an unsealed session as a first-class corpus `sources:` entry
- ❌ Put an abstract exhortation with no reproducible evidence on the list
- ❌ Leave the mistakes axis empty
- ❌ Intensity grades (🟡⚪) — keep the verdict binary
- ❌ Copy a single authority (your project's ADR format · `ledger.py` thresholds) into this skill

</supporting-info>
