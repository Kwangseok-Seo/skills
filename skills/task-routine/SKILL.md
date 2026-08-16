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
| [references/execution.md](./references/execution.md) | any group holds two or more tasks — executor contract and fallback ladder |
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

**A command the repo supplied is approved before it first runs here.** `verify.command` from project config and any command derived from a repo file (`package.json`'s `test` script, a `Makefile` target) are both text this machine did not write. Show the resolved command with its origin and run it only after a yes — once per repo, per exact text, so an edited command asks again. **That prompt, and only that prompt, is logged as `P0-verify`.** A command the user typed, at the wizard or at rung 3, is approved by the typing: no prompt is raised and no record is written. A `P0-verify` line exists so a later run can ask "was this repo-supplied text approved here?" (`references/telemetry.md`); writing one for a command that was never asked about answers a question nobody posed, and it has to claim `mode: "asked"` to be found at all, which is simply false. A config file holding something shaped like a credential stops the run instead (`references/setup.md`).

Print the effective configuration, each value tagged with its origin, **before Phase 1 does anything.** A run whose autonomy level the reader first learns in the summary was never theirs to approve.

## Arguments

- `setup` — run the wizard and exit. When it runs **automatically** because no config exists, the invocation continues into the run instead of exiting.
- `report` — print the decision-log scorecard and exit. Reads the log, changes nothing, never touches the dial.
- `--source=<ref>` — task source for this run (a file path, a GitHub issue number/URL, or an adapter-specific ref). Defaults to config.
- `--todos=1,3` — process only these items. Skips ordering and grouping.
- `--level=manual|assisted|auto` — override the dial for this run.
- `--auto` — shorthand for `--level=auto`. **Not persisted.** Unattended is always an explicit choice.
- `--resume` — load the newest checkpoint and continue at the first unit whose checkpoint status is `pending`. A checkpoint with **no** `pending` unit but completions still held reopens at the Phase 4 flush: it skips Phases 1–3 and the per-task cycle, and it still loads whatever that flush needs rather than a list fixed here. A `pending` unit whose checkpoint already carries a commit resumes at Step 3's completion mark rather than back inside the build loop — which is why the checkpoint is written **after the commit** as well as at the unit's start and end (`references/telemetry.md`). The dial is **not** inherited from it: an unattended resume needs `--auto` again. A `--source` that disagrees with the checkpoint's `source_ref` is a stop, not a merge of two runs.

No arguments and config present → resolve tasks from the configured source.

## Capability probe (every run, once)

Ask the machine, do not trust a stored list — a snapshot goes stale the moment the user installs or removes something.

Probe: external CLIs (`git`, `gh`, and any configured executor such as `codex`/`herdr`) via `command -v` / `Get-Command`; installed skills and agents under `~/.claude/skills/`, `~/.claude/agents/`, `~/.claude/plugins/installed_plugins.json`, and the project's `.claude/`. `git worktree` is always available and needs no probe. Whether a subagent can satisfy the executor contract is that contract's question, not this list's (`references/execution.md`).

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
| Tree dirty at start | the path lists below | List what is uncommitted and record it as the baseline (below) |
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

Only ✅ clears the consecutive-failure counter; ⚠️ and ⏭️ advance it, a merged group by one per task it contains, and **a task counts as attempted once this run has spent one of its budgets on it** — the first reviewer dispatch in Step 1, or the first edit in Step 2, whichever came first. Keyed to Step 2 alone, a task abandoned at the design cap after three rounds and four reviewers files as never attempted, and a checklist whose tasks all fail to converge before any code exists never trips this brake at all. **`❓` does neither** — the cycle finished, so it is not a failure to progress, and something the run cannot stand behind came out of it, so it is not a clean success. Letting it advance would put the run's stopping point in the grouping decision's hands: one unmet claim on a five-task group would count five, from one observation about one unit. The design, build, and TDD budgets are independent of each other, and environment failures consume no iteration.

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

**Both sides are bare path lists from the same pair of commands** — `git diff --name-only -z --no-renames <commit>` for tracked changes, `git ls-files --others --exclude-standard -z` for untracked ones — so they can be compared as bytes. `--no-renames` is load-bearing: with detection on, `git mv old new` reports `new` alone, the deletion of `old` never enters the set, and the commit ships both files while the tree that passed 2c had one. And never `git status --porcelain` on the other side: it prefixes two status characters and a space, writes a rename as two NUL fields of which only the first carries that prefix, and collapses a whole untracked directory to `dir/`. Subtract that from a diff and nothing matches at all — every path the subtraction existed to hold back rides into the commit. Take the untracked half **before** any `git add -N` — not because the set would otherwise lose those files, but because that list is what tells this run's intent-to-add entries from the user's. Measured: after `add -N`, `ls-files --others` stops reporting a new file while `git diff --name-only` starts reporting it, so the union is the same read in either order — and `git status --short` prints every intent-to-add entry as ` A` whether this run made it or the user did, so git can hand you the list but not the half that is yours to undo. The early read can.

Undo them **when Step 3 finishes — committed or not**, never when the set is computed. Undone early, `git commit --only` over a path git does not yet know refuses the whole commit — measured, `error: pathspec 'fresh.txt' did not match any file(s) known to git`, exit 1, nothing committed — so every unit that creates a file fails there. Left in place because no commit was made, the user's next `git commit -a` ships every new file the run touched.

**And `add -N` is not the only thing this run puts in the index.** A write operation can stage on its own — `git mv` stages the deletion of the old path, `git rm` stages a removal — and `--only` commits without them rather than clearing them, so they stay. Measured: after one unit proceeded past a dirty-path stop, `git mv`'s staged deletion sat in the index through two further units and was still there when the run ended, invisible in the summary and waiting for the user's next plain `git commit`. Unstage what **this run** staged and the commit did not take — `git restore --staged <path>`, measured to turn a staged `D ` into an unstaged ` D` and leave the working tree alone — at the same moment as the `add -N` undo, and leave everything else exactly as found — a stranger's staged work is theirs. On `--resume` the record of which entries were this run's is gone, so nothing is unstaged and the summary says which paths were left that way.

**The set is a list of paths; the checks that need content read the diff *restricted to* it.** 2d's review and the ⓑ hunk scans in `references/autonomy.md` need added lines, removed lines and context — `--name-only` has none of that. The set says *which paths are this unit's*; `git diff <unit-start-commit> -- <the set>` is how a check that reads hunks gets them without ever reading the whole tree.

- **An empty set for a unit whose plan named files is a stop**, not a pass — the same rule as a check that could not run.
- A commit stages exactly that set. Symmetrically: anything **outside** it is somebody's unrelated work, and anything **inside** it that the plan never named is unplanned overreach — say so and ask before committing, either way. A formatter that rewrote sixty files is the second case, and a guard that only interrogates the complement never sees it. **A path this unit already put to the user at H2's scope test is not asked again here** — it is named as already approved and the commit proceeds. One path, one question: the H2 prompt showed that path *because* the plan never named it, which is the same fact this test would raise, and asking twice for one answer doubles the prompts on any run whose tasks invoke a generator. The reverse does not hold, and that is why this test stays: overreach also covers paths no write operation ever announced, which H2 never had the chance to show. **This test reads paths, not lines** — a change the plan never authorised inside a file it did name passes it, and what covers that is 2d reviewing the diff against the plan. Do not try to make it line-granular: "did the plan authorise this line" has no general answer and buys false stops.
- **Write operations are read twice, for two different questions.** Before each one, H2 asks what it is *about to* destroy — that reading comes from the operation being requested, because a stop after the bytes are gone is a report (`references/autonomy.md`). As each completes, its paths accumulate into **the record of what this unit wrote**, which is what Step 3's test-claim check reads at the end. A merged group's record is the union of the changed-file lists its workers return (`references/execution.md`), since the main thread performed none of those writes itself.
- **The destructiveness tests read the paths this unit *wrote*, not this set.** `git diff` cannot show an ignored file and the subtraction removes an untracked one, so routing H2 through the change set would blind it to exactly the files it exists to protect. Take those paths from the write operations themselves.
- **A unit that must write a path already dirty at its start stops and asks — and when the operation *moves or copies* content, the path it takes that content from is tested exactly like the path it puts it on.** The subtraction above keeps a stranger's uncommitted work out of this commit, and it does the same to *this unit's own* write to that path — so continuing means committing without that file and saying nothing. The harm is omission — or, when the operation relocates content, absorption of work that was never this unit's — and either way it is about the unit's **work**, never about confusion. Watching only the destination leaves the subtraction's own premise unguarded: it is keyed on paths, so it holds only while content stays where it was. Measured — with `old.txt` dirty, `git mv old.txt new.txt` carried the stranger's uncommitted lines into `new.txt`, which was clean at unit start and so was subtracted from nothing, while the deletion of `old.txt` *was* subtracted. The commit shipped somebody else's work and kept a file the verified tree had removed, and nothing asked. A *program* that relocates content the same way is stopped one layer earlier, on its own terms: its destinations are not in the command text at all (`references/autonomy.md`). Proceeding is allowed; proceeding quietly is not — **name what the commit gets wrong at those paths**, in that unit's row and in the summary, and in both directions: *omitted*, where the subtraction dropped this unit's own write, and *added*, where a relocation put a dirty path's content onto a clean one and the subtraction had nothing to hold back. A report that lists only omissions describes the destination case and stays silent on the half that ships somebody else's lines under this task's message. **A unit that proceeds ends ❓, not ✅.** The loop converged, so this is not a failure to progress and must not advance the brake — a proceed observed once about one unit would otherwise count once per task in a merged group, the same arithmetic that keeps an unmet test claim out of the count. And it is not a clean success either: at those paths the commit records a state nothing in this run verified, which is the same thing `unverified` already means.
  - **Step 3's completion mark is the one write it does not govern**, because it is the one write never meant to be in a commit: it is made after the commit, no change set can hold it, and dropping it from one loses nothing. Without that, the mark left by every earlier unit — and by every earlier run — is dirt at the next unit's start, and the run stops on its first task, forever. The exemption comes from **where the write sits in the order**, so it holds on `--resume` and on tomorrow's invocation; a remembered list of "paths this run wrote" holds on neither.
- On `--resume` the tree is dirty by construction; the resumed unit records its own baseline the same way, so resume needs no exception to any of this.

## Phase 1–3 — Resolve, order, group

Fetch the task list from the source, order it by dependency, group what can run in parallel, and pick an executor.

Output shapes and worked judgments: **[PHASE-FORMAT.md](./PHASE-FORMAT.md)**. Read `references/execution.md` when **any one group holds two or more tasks** — that is what puts concurrent workers in a shared repo, and counting *groups* instead stays silent on one group of six while tripping on six groups of one. Fewer than two tasks skips grouping entirely and goes straight to the sequential cycle.

**Between resolving and ordering, predict each task's change surface — including when `--todos` has skipped ordering and grouping.** Both ordering and grouping are judgments about files, and Step 1 produces the file list far too late to inform either. That is why it runs there, not the only thing that reads it: Step 1 freezes this list as the plan for every task whose design loop is skipped. Under `--todos` that second reader is the only one left — the sweep still costs one search per task and now buys nothing at Phase 2 or 3 — and dropping it along with the phase it sits between leaves a skipped loop with no plan at all, which the bullet under Step 1 names as the false pass the freeze exists to prevent. This is a scan, not a design: read the task text, search the repo for the obvious owners, write one line of paths per task. Bound it — one search sweep per task, no reading beyond what the sweep returns, and paths left as `?` when it found nothing rather than guessed. **A `?` task is ordered sequentially**, because disjointness cannot be proven from an unknown.

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
- Decision `S3-commit`, tier `auto-eligible`. It commits the unit's change set and nothing else — **`git commit --only -m <message> -- <the set>`**, because the index cannot be trusted to hold that and only that. The message goes **before** the `--`: everything after it is a pathspec, and measured, a message placed there costs two errors — `error: pathspec '-m' did not match any file(s) known to git`, then the same for the message text — and exit 1. `git add -N`, which the set's own definition requires, promotes a *deletion* somebody else left uncommitted into a **staged** one, and a plain `git commit` then ships it under this task's message. `--only` ignores whatever else the index already carried. It is **not** a sandbox: it hands hooks a temporary index, so a `lint-staged`-style pre-commit hook that stages still lands inside the commit — measured, a hook running `git add b.txt` put `b.txt`, carrying a stranger's uncommitted lines, inside a `git commit --only -- a.txt`. So read the commit back and stop on anything **outside** the set: `git show --format= --name-only -z --no-renames <the commit just made>`. Every one of those options is load-bearing — bare `git show --name-only` prints the commit header first, without `-z` git renders a non-ASCII path as `"caf\303\251.txt"` and no byte comparison survives it, and with rename detection left on a `git mv` reports the new path alone, so a two-path set and a one-path commit disagree on a commit that was exactly right. **Only that direction is checked**: a merged group's set legitimately holds paths its worker commits already landed, `--only` commits nothing for them, and they are absent from the readback — measured, exit 0, one path committed out of a two-path set. It reads names, like everything else built on the set, so a hook that *rewrote* a file already in the set adds no name and passes here — and nothing else catches it either, since 2d ran before the commit and the hook runs inside it. That limit is worth knowing rather than assuming this readback closes it. And the readback is a report, not a gate. It runs after the commit exists, so it names the extra paths and stops the run rather than preventing anything — affordable only because a commit is local and reversible, and the reason the staging it catches is worth a stop at all is that the next unit would otherwise take its baseline from a commit that absorbed somebody else's uncommitted work. An empty set is not a commit at all: `--only` with no paths exits 128, and a merged group that needed no repair legitimately has nothing to commit here — which `--only` reports as exit **1** with `nothing to commit`, not 128, so a run that reads any non-zero exit as a failed commit records a failure for a group whose work went right, and advances the brake with it. **A non-zero exit is not one answer, and the number does not separate them** — that group, a commit that never happened (what the malformed invocation above returns), and `cannot do a partial commit during a merge`, which is 128 like the empty pathspec. Sort them by neither code nor message: the codes collide, and the messages are localised, so a run under a translated git keys on a string that is not there. **Read the commit `HEAD` points at before the call, then ask git what the call produced** — `git rev-list --reverse <before>..HEAD`. Empty means no commit was made: the merged group that had nothing of its own left, or a failure, told apart by whether the unit's work is still sitting in the tree; the second stops the run and reports git's own output. Otherwise it names what was created, oldest first, and **the first entry is this unit's commit** — which is also how the readback gets its target, because that target is not `HEAD`: measured, a `post-commit` hook that commits leaves HEAD one commit past the unit's, and a readback handed `HEAD` reads the hook's file, reports overreach, and never looks at the commit it was asked about. (A repository with no commits yet has no such value — and no unit baseline either; that gap belongs to the baseline, not to this comparison.) Very large sets exceed the OS argument limit — measured, a 1,200-path commit fails with `Argument list too long` — so pass them with `--pathspec-from-file=- --pathspec-file-nul`, which takes the set in the NUL-separated form it was already produced in, for the same reason both halves of it are taken with `-z`. Committing is local and reversible; pushing is not, and pushing is a hard stop.
- **A merged group's per-task commits are the worker-branch commits**, made before each merge (`references/execution.md`). This step therefore covers only what the post-merge loop itself changed, which on a group that needed no repair is nothing at all.
- **Check the unit against its own test claim.** `S2-test` named what would verify this unit; **the paths this unit wrote** — the list H2 already takes from the write operations — say what it produced. Any strategy other than `none` that **added or changed no test path** is a claim the unit did not meet. The work is committed regardless — a report, not a gate — and the unit ends **`❓`** instead of ✅. A passing suite cannot substitute: it passes whether or not this unit was tested, which is measurable by deleting a unit's whole change and watching every test still come back green.
  - **Written paths, not the change set**, because the set has already had the dirty-path subtraction applied to it: a test the unit really wrote, on a path that was dirty at its start, would read there as a test never written. **The record carries what each write did — added, modified, deleted — not just where.** Only added and modified count. A bare path list cannot express that, and without it `rm tests/cache.test.ts` puts a test path in the record and removing the tests for the code you just rewrote becomes the cheapest way to satisfy this. For the same reason the record is read at the unit's **end**: a test written in one build iteration and deleted in the next is not a test this unit produced.
  - **What counts as a test path is read off the repo, not off a list of filename patterns** — where this repo already keeps its tests, its fixtures and its golden files included, and in a monorepo the part of it this change touches. **Where tests are demonstrably not separate paths** — a `#[cfg(test)]` block or an in-source Vitest guard actually found in this repo's sources — there is nothing here to read: say so once, in Phase 1, and do not run the check for that repo. **A repo with no tests yet is not that case** and does not qualify: a unit claiming tests there has to write the first ones, which is exactly what this check is for. A `❓` on every unit is not honesty, it is noise that buries the rows which mean something.
  - **`none` is checked in the other direction.** A unit that claimed no tests and then wrote something the row it invoked cannot cover — `none` justified by "documentation" against a record holding a new module and a rewritten function body — has the same unmet claim from the other side, and is `❓` and `unmet` like any other, never `unclaimed`. Without this the cheapest way past the check is to claim nothing at 2a, which happens before any code exists. **What the row cannot cover is behaviour, and that is read from the diff restricted to the record's paths, not from a file's extension**: a docstring line added to `duration.py` is the documentation row's own case, and it stays `unclaimed` even though every path in its record is a source file. Read as "a source path in the record refutes `none`", this check marks every comment fix ❓ — and a ❓ on the most ordinary change there is buries the rows that mean something, which is the same reason a repo keeping no separate test paths is excluded above. **Comment syntax is not a synonym for prose**, and the diff is where that shows: a doc-comment carrying an executable example *is* a test wherever the repo runs doctests, and `# pragma: no cover`, `# type: ignore` and `//go:generate` change what tools do. A path already dirty at the unit's start cannot be read this way at all — its diff carries a stranger's lines beside this unit's — but such a unit is `❓` under the rule above regardless, so nothing turns on it. Where the diff leaves it genuinely open, `❓` is the answer, as everywhere else a check cannot settle its own question.
  - **A unit that reached a cap and left its claim unmet is ⚠️, not `❓`.** One cell, and the status column carries what the brake reads; the unmet claim goes in that row's own line — a unit that ran out of budget is the likeliest of all to have left its tests unwritten, so it is the last row that should lose the note. `❓` is for a unit whose cycle finished inside its budget.
  - **A merged group's tasks each choose their own `S2-test`, before their workers are dispatched, and the group still ends on one verdict marking every task row.** Chosen up front because a strategy picked after the merge is picked with the workers' tests, or their absence, already visible, and a claim made after seeing the answer is one no unit can fail (`references/execution.md`). One verdict because the writes cannot be split back apart: each worker returns its own changed-file list, but the post-merge loop's repairs belong to the group and to no task in it, so a per-task verdict would be right for one half of the writes and arbitrary for the other. The union is what is read — if any task claimed tests, the group's writes must hold a test path; if every task claimed `none`, the reverse check applies to the group as a whole. Coarse in both directions: one test path anywhere meets the claim for all of them, exactly as one unmet claim marks all of them. **A group where some tasks claimed tests and others claimed `none` gets the first check only**, since the reverse one asks whether *this* unit shipped behaviour it said it would not, and there is no way to ask that of one task inside a shared write list. Worth knowing rather than assuming the group is checked from both sides.
  - **What this does not establish**: that those tests exercise this change. A test file that imports the new code and asserts nothing satisfies it. Closing that gap means running the tests against the code's absence — a different instrument, and not in this skill. What covers it here is 2d, reviewing the diff against the plan.
- Then mark it done **in the source**, at the tier **the source dictates, not the step**: local writes through immediately, remote is held `pending` and flushed in Phase 4 (`references/sources.md`). Without this, `--resume` redoes work it already committed.

## Phase 4 — Summary

Print the per-task result table, then close the run out. Column definitions and the audit-table layout: **[PHASE-FORMAT.md](./PHASE-FORMAT.md)**.

- **⚠️ and ❓ rows need manual review** — a cap was reached and the work continued anyway, or the unit committed something this run cannot stand behind: no test where its strategy claimed one, or a dirty-path stop passed and a commit that differs from the tree 2c verified.
- **Whenever the run was not fully manual, the decision-audit table is mandatory**: what was chosen on the user's behalf, why, and whether the outcome supported it. Unattended mode is only acceptable because it can be audited afterwards; skipping this table removes the thing that made it acceptable.
- Append one `outcome` line per decision (`references/telemetry.md`). Record `manual_intervention` **honestly** — only clean, uninterrupted successes are evidence for raising the dial.
- If a step newly crosses both evidence thresholds, **say so in one line and stop there.** Never raise the dial as a side effect of a run.
- **Flush pending completions in one batch.** A remote source's completions have been held since Step 3: show them all and ask **once per run**, never per task. Declined or failed writes stay `pending`; never report them as done.
- **Say where a local source's completion marks are.** They are written after the commits they belong to, so no commit of this run contains them — name the file and the count (`TODO.md — 4 completion marks, uncommitted`) and leave them for the reader to commit with their own message. Silence reads as "committed".
- **Close the run out only when it finished and nothing is left pending** — the checkpoint file itself is kept, because the next run reads its order and grouping as the prior analysis (`references/telemetry.md`).
- **A flush that fails or is declined twice needs a way out.** Offer it on the second pass — a read-only source fails forever and is never *declined*, so keying only on refusal leaves that run with no exit: apply, hold for later, or drop these completions and say they were never written. Without the third option the checkpoint can never be closed and every later `--resume` reopens the same prompt.

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
