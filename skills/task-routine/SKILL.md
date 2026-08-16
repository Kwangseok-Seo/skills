---
name: task-routine
description: "Drives a checklist of tasks to committed code, one task at a time — design, test strategy, implement, verify, review, commit — with an autonomy dial (manual / assisted / auto) deciding which gates run unattended, and an append-only decision log recording recommendation vs choice vs outcome. The task source is pluggable: a local markdown checklist or a GitHub issue. Stops at the commit; never pushes, opens PRs, or writes to a tracker without asking. Args: `setup` = (re)run the setup wizard; `report` = print the decision-log scorecard and exit; `--source=<ref>` = task source for this run; `--auto` = unattended for this invocation only; `--level=manual|assisted|auto`; `--todos=1,3` = only those items; `--resume` = continue an interrupted run. Use when the user says: 'task routine', 'work through the checklist', 'run the TODO loop', 'do these tasks one by one', 'automate this task list', 'implement the checklist and commit each item'."
argument-hint: "[setup|report] [--source=<ref>] [--todos=1,3] [--level=manual|assisted|auto] [--auto] [--resume]"
---

<what-to-do>

Take a list of tasks and drive each one to a commit through a fixed cycle:
**a design loop → a build loop (implement / verify / review) → a commit.**

Two things make this more than "just do the work":

1. **An autonomy dial.** Every decision point carries a risk tier. A decision runs unattended only when *the level allows it* **AND** *the tier is auto-eligible* — never one or the other. Four classes of action are asked about at every level, including `auto`.
2. **An append-only decision log.** Each recommendation, each choice, and later each outcome is appended as its own line. That log is the evidence for raising the dial — the dial is not raised on vibes.

Fixed order: **setup (once) → probe → resolve tasks → order → group → per-task cycle → summary.**

The gates below are the contract: entry conditions, caps, and hard stops. Everything else — option wording, decision tables, procedures — lives in `references/` and is read **on demand, once, when that path is entered.**

**This skill stops at the commit.** It never pushes, opens a PR, merges, or runs a retrospective. Hand those to whatever skills you already use.

**`git` is required, and a git repository with it.** Everything else degrades and says so; without git there is no unit baseline, no change set, no worktree, and no commit — so there is no run.

</what-to-do>

<supporting-info>

## Read-on-demand map

| Read this | When |
|---|---|
| [PHASE-FORMAT.md](./PHASE-FORMAT.md) | entering Phase 1 — what phases 1–4 put on screen |
| [DESIGN-LOOP.md](./DESIGN-LOOP.md) | entering Step 1 with the loop enabled — reviewer protocol |
| [BUILD-LOOP.md](./BUILD-LOOP.md) | entering Step 2, **or the wizard's question 2** — verify/review tooling, the fingerprint table, cleanup scope, TDD hand-off |
| [references/setup.md](./references/setup.md) | first run, or `setup` argument — wizard, config schema, capability probe |
| [references/sources.md](./references/sources.md) | resolving tasks — adapter contract, local-markdown and GitHub implementations |
| [references/autonomy.md](./references/autonomy.md) | every run, before Phase 1 — level × tier table, hard-stop detection, brake semantics |
| [references/execution.md](./references/execution.md) | more than one parallel-eligible group — executor contract and fallback ladder |
| [references/telemetry.md](./references/telemetry.md) | writing the decision log or the checkpoint, or analysing either — both schemas |

Read each at most once per session. Do not read `execution.md` on a sequential run; do not read `setup.md` when config already exists.

## Runtime layout

```
~/.claude/task-routine/config.json                 # global config (wizard writes this)
<repo>/.claude/task-routine.json                   # optional per-project override
~/.claude/task-routine/<project-slug>/decisions.jsonl   # append-only decision log
~/.claude/task-routine/<project-slug>/run-<id>.json     # checkpoint
```

State lives **outside the repo** on purpose: an unattended run that stages files must never be able to commit its own log. `TASK_ROUTINE_DIR` overrides the root.

**Config merges project-over-global key by key, but the two files are not equally trusted.** A project config arrives *with the repo*, so it may state facts about the project — `source`, `verify.command`, conventions — and nothing that decides **how much runs without you**: `autonomy.*`, `auto.*`, and the loop caps come from global config or the command line. A project key on the wrong side of that line is ignored, with one line saying so, and a key added to the schema later is ignored from project config until someone classifies it. Silent precedence is what lets a cloned repo set the dial to `auto` and the task cap to 50.

**A command the repo supplied is approved before it first runs here.** `verify.command` from project config and any command derived from a repo file (`package.json`'s `test` script, a `Makefile` target) are both text this machine did not write. Show the resolved command with its origin and run it only after a yes — once per repo, per exact text, so an edited command asks again. A command the user typed, at the wizard or at rung 3, is approved by the typing. Log the approval as `P0-verify`. A config file holding something shaped like a credential stops the run instead (`references/setup.md`).

Print the effective configuration, each value tagged with its origin, **before Phase 1 does anything.** A run whose autonomy level the reader first learns in the summary was never theirs to approve.

## Arguments

- `setup` — run the wizard and exit. When it runs **automatically** because no config exists, the invocation continues into the run instead of exiting.
- `report` — print the decision-log scorecard and exit. Reads the log, changes nothing, never touches the dial.
- `--source=<ref>` — task source for this run (a file path, a GitHub issue number/URL, or an adapter-specific ref). Defaults to config.
- `--todos=1,3` — process only these items. Skips ordering and grouping.
- `--level=manual|assisted|auto` — override the dial for this run.
- `--auto` — shorthand for `--level=auto`. **Not persisted.** Unattended is always an explicit choice.
- `--resume` — load the newest checkpoint and continue at the first unit whose checkpoint status is `pending`. The dial is **not** inherited from it: an unattended resume needs `--auto` again. A `--source` that disagrees with the checkpoint's `source_ref` is a stop, not a merge of two runs.

No arguments and config present → resolve tasks from the configured source.

## Capability probe (every run, once)

Ask the machine, do not trust a stored list — a snapshot goes stale the moment the user installs or removes something.

Probe: external CLIs (`git`, `gh`, and any configured executor such as `codex`/`herdr`) via `command -v` / `Get-Command`; installed skills and agents under `~/.claude/skills/`, `~/.claude/agents/`, `~/.claude/plugins/installed_plugins.json`, and the project's `.claude/`. Native subagents and `git worktree` are always available and need no probe.

If the result differs from the config snapshot, **say so in one line and update it.** Capability loss must never be silent — "parallel unavailable, running sequentially" is a report, not an omission.

## Autonomy: level × tier

```
run unattended  ⟺  level allows this step  ∧  tier == auto-eligible  ∧  no hard-stop signal
```

| Level | Behaviour |
|---|---|
| `manual` | Every decision is asked. Identical to running the cycle by hand. |
| `assisted` *(default)* | Auto-eligible decisions **that carry a recommendation** run unattended. Everything else is asked. |
| `auto` | All auto-eligible decisions run unattended; where there is no recommendation, state the reasoning in one line and proceed. |

**A decision with no assigned tier is treated as `manual-only`.** Unknown means ask — the guard fails closed, not open.

## Hard stops — asked at every level, `auto` included

1. `H1` **Outward-facing** — `push`, opening or merging a PR, pushing tags, publishing a release.
2. `H2` **Destructive local work** — two tests, either one enough: unrecoverable bytes, **or** never named by the plan.
3. `H3` **Writing to an external tracker** — comments, status, checkboxes, labels, assignees.
4. `H4` **Touching a security surface** — any one of five signals.

These fire at every level, so **`references/autonomy.md` is read on every run, before Phase 1**, and each class's tests live there. The level decides which *decisions* are asked, never which *actions* are guarded.

**A test whose input is unavailable is a stop — written as a rule, never as a list of broken inputs.** No input, no pass. A guard that goes quiet when it breaks is worse than no guard.

## Brakes on an unattended run

| Brake | Default | On trip |
|---|---|---|
| Tree dirty at start | `git status --porcelain` | List what is uncommitted and record it as the baseline (below) |
| A commit would reach outside the unit's set | the set below | Stop and ask — at every level, not only `--auto` |
| Tasks per invocation | 5 (`auto.max_tasks`) | Report progress and ask whether to continue — **only when tasks remain** |
| Consecutive failed units | 2 | Stop the whole loop — repeated failure means the premise is wrong, not the attempt |
| Design review rounds per task | 3 | Ask: one more / freeze as-is / SKIP this task / stop |
| Design reviewer invocations per task | rounds + 1 (4) | Ask: one more / freeze as-is / SKIP this task / stop |
| Build-loop iterations per unit | 3 | Ask: one more / freeze as-is / SKIP this task / stop |
| TDD attempts per task | `min(15, 5 × behaviours named at 2a)` | Ask: retry / SKIP / re-plan / drop TDD / stop |

**Each counter resets at the boundary of the thing it bounds, and those boundaries are not the same:**

| Counter | Bounds | Resets |
|---|---|---|
| design rounds · reviewer invocations · TDD attempts | one task | when the next task starts |
| build-loop iterations | one **unit** — a sequential task, or a merged parallel group, which shares one budget, one verify, one review | when the next unit starts |
| consecutive failures | the whole **run**, counted in **tasks** | only when a task ends ✅ |

Only ✅ clears the consecutive-failure counter; ⚠️ and ⏭️ advance it, a merged group by one per task it contains, and a task counts as attempted once it entered Step 2. The design, build, and TDD budgets are independent of each other, and environment failures consume no iteration.

**Which end-state advances what, why the scopes are drawn where they are, and the worked six-task trace: `references/autonomy.md`.** Getting a reset boundary wrong is how a cap becomes unreachable, so read it there rather than reconstructing it here.

## What "this unit changed" means — one set, read by everything

A unit records its baseline when it starts: **the commit it started at, and the paths already dirty in the tree at that moment.**

```
changed = git diff <unit-start-commit>        # tree vs that commit, so committed merges
          (git add -N first, so a new file    # and uncommitted edits are both in it
           is not invisible)
        − the paths already dirty at unit start
```

The review at 2d, the cleanup scope at 2e, every hard-stop scan, and what a commit stages all read **that one set**. Never bare `git diff`, never the whole working tree: after a parallel group merges, the tree is clean and the work is in commits, so a check that reads the tree finds nothing and **passes by absence**.

- **An empty set for a unit whose plan named files is a stop**, not a pass — the same rule as a check that could not run.
- A commit stages exactly that set. Symmetrically: anything **outside** it is somebody's unrelated work, and anything **inside** it that the plan never named is unplanned overreach — say so and ask before committing, either way. A formatter that rewrote sixty files is the second case, and a guard that only interrogates the complement never sees it.
- **The destructiveness tests read the paths this unit *wrote*, not this set.** `git diff` cannot show an ignored file and the subtraction removes an untracked one, so routing H2 through the change set would blind it to exactly the files it exists to protect. Take those paths from the write operations themselves.
- A unit that must modify a path that was **already dirty at its start** stops and asks. Afterwards the two changes cannot be told apart.
- On `--resume` the tree is dirty by construction; the resumed unit records its own baseline the same way, so resume needs no exception to any of this.

## Phase 1–3 — Resolve, order, group

Fetch the task list from the source, order it by dependency, group what can run in parallel, and pick an executor.

Output shapes and worked judgments: **[PHASE-FORMAT.md](./PHASE-FORMAT.md)**. Read `references/execution.md` only when two or more parallel groups exist. Fewer than two tasks skips grouping entirely and goes straight to the sequential cycle.

**Between resolving and ordering, predict each task's change surface.** Both ordering and grouping are judgments about files, and Step 1 produces the file list far too late to inform either. This is a scan, not a design: read the task text, search the repo for the obvious owners, write one line of paths per task. Bound it — one search sweep per task, no reading beyond what the sweep returns, and paths left as `?` when it found nothing rather than guessed. **A `?` task is ordered sequentially**, because disjointness cannot be proven from an unknown.

| Phase | Decision | Tier | Does not fold away |
|---|---|---|---|
| 1 resolve | `P1-source` | auto-eligible | **No list, no run** — say where the source was looked for and stop. Never invent tasks |
| 2 order | `P2-order` | auto-eligible | Skipped entirely when `--todos` is given |
| 3 group | `P3-exec` | auto-eligible | Parallel workers need **write permission** — a read-only worker has its edits refused and reports success anyway · verify / review / commit always run **after the merge**, per group, sequentially |

## Per-task cycle

Two loops and a commit. Banner each task as `TASK [n/N]: <title>`.

**Step 1 · Design — an internal loop.** A wrong design is cheapest to catch before any code exists; without this loop the first check on it is Step 2d, on finished code.

`1a gather → 1b design → 1c independent review → 1d apply → (back to 1c, max 3) → 1e freeze`

Reviewer selection, brief contents, verdict vocabulary, and skip table: **[DESIGN-LOOP.md](./DESIGN-LOOP.md)**.

- **The reviewer is not the designer, and receives the plan — never the reasoning.** Hand over the design conversation and what comes back is agreement, not review.
- **Accepting or rejecting a finding stays in this thread.** The reviewer advises, it does not decide — otherwise the Phase 4 audit table attributes to you a choice you did not make.
- **Skip the loop** when the change is one file with no new interface, schema, or dependency — **and when the surface was already reviewed earlier in this run**: extend the frozen plan instead of re-reviewing it. Without that second clause, a checklist that slices one feature reviews the same design once per slice, each time from a reviewer who cannot see the other slices. Never skip on the strength of that alone: the full table is in `DESIGN-LOOP.md`, and the task's own text read against the security signals can force the loop before any code exists.
- **A skipped loop still freezes a plan** — the one-line file list the pre-ordering scan produced. Skipping means "no review was needed", never "no plan exists": the destructiveness scope test asks what the plan named, and a missing plan would answer *nothing to compare against*, which reads as a pass.
- **A verdict that does not count as a round still costs an invocation.** `NEEDS_MORE_INFO` is exempt from the round counter, never from the ceiling of `rounds + 1` dispatches per task; two unusable verdicts in a row is a stop-and-ask.
- Decision `S1-design`, tier `auto-eligible`.

**Step 2 · Build — a loop.** Implementation, verification, and review share one budget and one loop, which is what makes the cleanup condition loop state rather than a pair of flags.

`2a strategy → 2b implement → 2c verify → 2d review → (failure or findings: back to 2b, budget 3) → 2e clean up and freeze`

Verify-command detection, review tooling, cleanup scope, and the TDD hand-off: **[BUILD-LOOP.md](./BUILD-LOOP.md)**.

- Decisions `S2-test` (at 2a, **chosen once** — the loop re-enters at 2b) and `S2-review` (at 2d), tier `auto-eligible`. Choosing TDD **delegates the method, never the caps** — those stay here.
- **Implement minimal-first**, reusing before building. **Validation, security, accessibility, and backward compatibility are never trimmed.**
- **Review only runs after verify passes.** A failed iteration therefore costs no review, which is why no separate re-review cap exists.
- **The first verification is not counted**, and environment failures never are.
- **Cleanup belongs to the exit, not to an iteration**, and appears only when the loop ran more than once.
- A review tool that must be typed by the user is **requested, never invoked** — say so and wait.

**Step 3 · Commit and mark done.** Derive the message convention from the repo (`git log --pretty=%s`, last ~20), falling back to `<type>: <summary>`; include the task reference when the source gives one.
- Decision `S3-commit`, tier `auto-eligible`. It stages the unit's change set and nothing else. Committing is local and reversible; pushing is not, and pushing is a hard stop.
- Then mark it done **in the source**, at the tier **the source dictates, not the step**: local writes through immediately, remote is held `pending` and flushed in Phase 4 (`references/sources.md`). Without this, `--resume` redoes work it already committed.

## Phase 4 — Summary

Print the per-task result table, then close the run out. Column definitions and the audit-table layout: **[PHASE-FORMAT.md](./PHASE-FORMAT.md)**.

- **⚠️ rows need manual review** — a cap was reached and the work continued anyway.
- **Whenever the run was not fully manual, the decision-audit table is mandatory**: what was chosen on the user's behalf, why, and whether the outcome supported it. Unattended mode is only acceptable because it can be audited afterwards; skipping this table removes the thing that made it acceptable.
- Append one `outcome` line per decision (`references/telemetry.md`). Record `manual_intervention` **honestly** — only clean, uninterrupted successes are evidence for raising the dial.
- If a step newly crosses both evidence thresholds, **say so in one line and stop there.** Never raise the dial as a side effect of a run.
- **Flush pending completions in one batch.** A remote source's completions have been held since Step 3: show them all and ask **once per run**, never per task. Declined or failed writes stay `pending`; never report them as done.
- Delete the checkpoint only when the run finished **and** nothing is left pending.

## Interrupt and resume

On "stop", or when a brake trips, write the checkpoint and print: what is done, what is left, and `--resume` to continue. Resume reloads counters and decision history so caps survive across sessions.

**The task source is the source of truth**, with one exception: completions still `pending` a tracker write. Everything else in the checkpoint — counters, decision history — is bookkeeping, and where the two disagree the source wins.

## Never

- ❌ Push, open a PR, merge, delete files, or write to a tracker without asking — at any level
- ❌ Treat a failed hard-stop check as a pass
- ❌ Run a decision unattended because it is "obviously fine" when its tier is unknown
- ❌ Fall back from parallel to sequential, or from a configured tool to a default, without saying so
- ❌ Call it an independent design review after handing the reviewer the design conversation
- ❌ Burn the remaining review rounds after the design already came back clean
- ❌ Duplicate the capability list into config instead of probing
- ❌ Rewrite a line in the decision log — outcomes are appended, never merged in place
- ❌ Load `references/` files that this run's path does not enter

</supporting-info>
