# autonomy — level × tier, hard stops, brakes

> Read on **every** run, before the first hard-stop test. A fully manual run needs it too: the level decides which *decisions* are asked, never which *actions* are guarded, and the four hard-stop classes fire at `manual` exactly as they do at `auto`.

```
run unattended  ⟺  level allows this step  ∧  tier == auto-eligible  ∧  no hard-stop signal
```

Three conjuncts. Dropping any one of them is how automation either leaks or seizes up, so the check is written once, here, and referenced everywhere else.

## Levels

| Level | Auto-eligible **with** a recommendation | Auto-eligible **without** one | manual-only |
|---|---|---|---|
| `manual` | ask | ask | ask |
| `assisted` | run | ask | ask |
| `auto` | run | run, stating the reasoning in one line | ask |

`assisted` splits on "is there a recommendation", because a recommendation is a claim the skill is willing to defend — and the decision log later scores whether it deserved to.

## Tiers, per decision

| Decision | Where | Tier | Recommendation comes from |
|---|---|---|---|
| `P0-verify` | before Phase 1 | **manual-only** — a command the repo supplied, approved once per repo per exact text | — |
| `P1-source` | Phase 1 | auto-eligible | freshness of the last run against the same source |
| `P2-order` | Phase 2 | auto-eligible | the dependency edges found |
| `P3-exec` | Phase 3 | auto-eligible | highest available executor rung |
| `S1-design` | Step 1 | auto-eligible | the skip table in `DESIGN-LOOP.md` |
| `S2-test` | Step 2a | auto-eligible | the change-shape table in `BUILD-LOOP.md` |
| `S2-review` | Step 2d | auto-eligible | which review tooling the probe found |
| `S3-commit` | Step 3 | auto-eligible | the convention read out of `git log` |
| `S3-done` | Step 3 | **follows the source** — `local` auto-eligible, `remote` manual-only | the adapter's `locality` |
| anything not in this table | — | **manual-only** | — |

The last row is the load-bearing one. A new decision point added later is manual until someone deliberately classifies it; the alternative — unlisted means allowed — turns every future edit into an unreviewed expansion of what runs unattended.

## Hard stops

Asked at **every** level, `auto` included.

Each class carries an id — `H1-outward`, `H2-destructive`, `H3-tracker`, `H4-security` — and **every hard-stop prompt is written to the decision log** like any other decision, always with `mode: "asked"`. Without that, thirty security approvals granted at 2 a.m. appear nowhere and `report` prints a clean scorecard for the run that asked for the most.

### 1 · Outward-facing

`git push`, opening or merging a pull request, pushing tags, publishing a release, or anything else whose effect leaves this machine.

### 2 · Destructive local work

Two tests, and either one makes it a hard stop:

| Test | Asks | Covers |
|---|---|---|
| **Recoverability** | can git give back the bytes **this operation destroys**? | discarding uncommitted work (`git checkout -- <path>` · `git restore` · `git reset --hard`) · dropping a stash · deleting a branch whose commits nothing else reaches · truncating or wholesale-rewriting an untracked or ignored file |
| **Scope** | did the frozen plan name this file? | adding, removing, or rewriting a file the plan never mentioned — **recoverable is not the same as reviewed** |

**Recoverability is about the bytes destroyed, not the file's tracking status.** A one-line edit destroys one line; a whole-file rewrite of an unrecoverable file destroys the file. That distinction is what lets Step 3 flip a checkbox in *any* `TODO.md` — tracked or not, a one-character edit destroys almost nothing — while regenerating an ignored `data/seed.json` from scratch is a hard stop. **The Scope test does not catch that checkbox either, for its own reason:** it asks whether the frozen *plan* named the file, and the mark is not the plan's work — it is the step's bookkeeping, written after the commit the plan describes. Requiring a plan to name `TODO.md` before Step 3 may close a task would make every plan name it, which is a rule that has stopped meaning anything. Keyed to tracking status instead, the rule would prompt once per task on the very ordinary setup of a personal, gitignored TODO list, and `sources.md`'s "local completions write through immediately" would be a dead letter.

Both tests read **the paths this unit wrote**, taken from the write operations — not the change set, which by construction cannot contain an ignored file and subtracts an untracked one (`SKILL.md`). **A shell command run for its side effects is one of those write operations** — an installer, a generator, a formatter, a `rm` — and like every other one its tests are applied to **what the operation is about to do, read from the command itself, before it runs.** That is not a preference for static reading: a stop that fires after `rm -rf src/legacy` has already run is a report, and the bytes it was guarding are gone. Comparing the tree before and after tells you what a command *did*; it can never be the input to a test that must precede it. **A command supplies these tests a destination only when it acts on that path itself.** `rm -rf src/legacy`, `mv a b`, `sed -i` and a redirection name what they will write. `make fmt`, `npm run codegen`, `./scripts/bootstrap.sh` and `python scripts/regen_seed.py` name a target, a script, a program — the command's *input*. Where it writes is decided inside code this text does not show, so a path in that position is not a destination and reading it as one is how one level of indirection walks through the guard. **An output path handed to a program does not close the gap either**: `python scripts/regen_seed.py --out data/seed.json` names a destination the program may honour, ignore or add to, and the `data/old/` it also clears appears nowhere in the command. A command that names no destination of its own gives these tests nothing to read, and no input is a stop, exactly as below. The earlier enumeration — "a file whose contents were not produced by this run" — made every edit to an existing file a hard stop, which no run can satisfy, and its natural narrowing let that same `data/seed.json` be overwritten unrecoverably.

**One carve-out, stated as a rule rather than an exception list:** removing a worktree *this run created* whose branch is *already merged* is not destructive — nothing is lost that is not also in the branch. Any other worktree — pre-existing, unmerged, or dirty — is a hard stop.

### 3 · Writing to an external tracker

Posting a comment, changing status or checkboxes, changing labels or assignees. Colleagues see these, which makes them outward-facing even when the API call is trivial.

### 4 · Touching a security surface

Any **one** of five signals is enough:

| | Signal | Detect |
|---|---|---|
| ⓐ | Sensitive path | `.env*` · `*secret*` · `*credential*` · `*.pem` · `*.key` · `id_rsa*` · `.npmrc` · `.netrc` · `.git-credentials` · `.github/workflows/*` · IAM / policy / rules files |
| ⓑ | Sensitive change | **either side of a hunk** matching `auth` · `token` · `password` · `secret` · `permission` · `role` · `grant` · `cors` · `csrf` · `xss` · `sanitiz` · `escape` · `crypto` · `hash` · `tls` · `ssl` · `cert` |
| ⓒ | Supply chain | any dependency manifest or lockfile changed |
| ⓓ | New egress | a new outbound call — HTTP client, socket, webhook, third-party SDK |
| ⓔ | Execution surface | Dockerfile, container or sandbox options, permission flags, `chmod`, CI runner config |

Signals are OR'd, and they are deliberately over-inclusive: a false positive costs one prompt, a false negative ships an unreviewed auth change.

**When they are evaluated.** Twice against code — at 2c on the unit's change set, and again at Step 3 on the set about to be committed, since the last repair iteration is otherwise unscanned. And once *before any code exists*: `S1-design` reads the **task's own text** against **all five signals** — the ⓑ words, the ⓐ path patterns, and the ⓒ–ⓔ subjects (a dependency, an outbound call, a container or permission change). Any hit runs the design loop.

All five, not ⓑ alone. "Require admin role on /admin/\*" declares its surface in ⓑ words, but "post build results to the team Slack webhook" declares an ⓓ surface with no ⓑ word in it, "run the migration container as root" declares ⓔ, and "add the deploy key to `deploy/authorized_keys`" declares ⓐ. Reading only ⓑ before code exists means those three designs are never reviewed and the prompt arrives after the code is written — the exact state this pre-code read was added to prevent.

**ⓑ reads both sides of the diff.** A control is more often *removed* than added, and a removal leaves nothing behind for an added-lines scan to match: replacing `router.get('/search', requireAuth, listSearch)` with `router.get('/search', listSearch)` touches no sensitive path, adds no dependency, opens no egress, and its added line is ordinary routing code. So the vocabulary is matched against the hunk as a whole — added lines, removed lines, and the context git prints around them — and a match on the removed side **alone** is enough. Nothing else in the table covers for it.

**One structural signal, which no vocabulary can cover.** A hunk that removes a call from a request path or a registration chain — middleware, a guard, a decorator, a filter — is ⓑ whatever the call is named. `- app.use('/internal', ipAllowlist(ALLOWED_CIDRS))` matches no word on the list and is exactly the removal the list exists to catch; so is a dropped rate limiter, a removed `helmet()`, a widened `trustProxy`. The word list will always trail the repo's own naming; the shape of "a check that used to run on this path no longer does" will not.

Both lists are floors, not definitions — ⓐ's paths as much as ⓑ's words. A path this repo treats as a secret store matches even when its name is local (`deploy/authorized_keys`, `terraform/prod.tfvars`, `charts/*/values-prod.yaml`), and a word this repo uses for a session lifetime, a key, or a capability matches too. Trimming a JWT expiry from 24h to 15m contains none of the listed words and is squarely this class.

### The check fails closed

**If the check cannot run, that is not a pass — and that is a rule, never a list of broken inputs.** Written as a list — unreadable diff, empty file list, unreachable source — the clause always misses one: the item nobody wrote is "there is no frozen plan to compare against, because the design loop was skipped". So: no input, no pass. Stop and ask, naming what could not be determined. This governs all four classes, not only the signals here.

Those signals are evaluated against the unit's change set (`SKILL.md`), never against a bare `git diff`, because a clean tree after a merge and a genuinely empty change look identical from here — **an empty change set for a unit whose plan named files** is itself one of these stops.

This is the clause most likely to be quietly dropped during a refactor, because a broken check and a clean check look identical from the outside: both produce no warning. They are not the same, and only one of them may proceed.

## Brakes

**The brake table lives in `SKILL.md` and only there.** It was duplicated here once and the two copies drifted within a single fix pass — this file kept refusing `--auto` on a dirty tree months after that became a baseline recording. What this file earns is the part `SKILL.md` has no room for: why the scopes differ, and what the counter does step by step.

**Three scopes, not one.** The design-round, reviewer-invocation and TDD counters are per task and reset when the next task starts. The build-loop budget belongs to a **unit** — a sequential task, or a merged parallel group, which shares one budget, one verify and one review. The consecutive-failure counter belongs to the **run**.

The design, build and TDD budgets are independent of one another — a task that spent three design rounds still arrives at Step 2 with a full build budget. The invocation ceiling is the deliberate exception: it is derived from the round cap, so raising `design_loop.rounds` raises it too. Environment failures consume no build iteration at all; `BUILD-LOOP.md` says how that verdict is checked rather than asserted.

**Consecutive failures stops the whole loop, not the task.** The other brakes bound one unit's effort; this one says the run's premise is wrong. Two tasks in a row hitting a cap is not bad luck, it is usually a stale task list, a broken environment, or a verify command that no longer matches the repo. So it counts what each **task** ended as — a merged group contributing one increment per task in it — and only a ✅ clears it:

```
task                       ended       counter
1, 3  (one merged group)   ✅ ✅         0    a group shares one budget, not one increment
2                          ⚠️  cap       1    the budget ran out — the loop did not converge
4                          ✅            0    a clean task clears it
5                          ⚠️  cap       1
6                          ⏭️  skipped   2 ⛔ abandoned after a budget was spent
7, 8                       —             —    never reached: neither counted nor cleared
```

(Six tasks, so not the four-task run in `PHASE-FORMAT.md`.) Two things this shape buys that a per-unit count does not: a five-task group that ends ⚠️ adds **five**, so the grouping decision cannot quietly widen the run's tolerance — and reset only on ✅, never on the next task, because every failure is followed by a task boundary and resetting there puts 2 out of reach.

**What this counter measures is whether the loop is converging.** ⚠️ says the budget ran out and ⏭️ that the unit was abandoned; ✅ says it converged cleanly. **`❓` says it converged and something else went wrong** — the unit committed and the verify passed, and what failed was the *claim* about its tests, or the match between the commit and the tree that verify passed on — so it does not advance. It does not clear either: the reset is deliberately reserved for ✅, and a unit whose tests nobody can point to is not the clean success that says the run's premise is sound. The ⏭️ that spent nothing is the other end-state outside the count, for the opposite reason: nothing was attempted at all.

A task the user declined before this run had spent **any** of that task's budgets on it is ⏭️ but does **not** count — at a hard stop or at a design prompt, either way. Declining two security prompts in a row is the guard doing its job; treating that as evidence the run's premise is wrong would punish the correct answer.

**The line is what was spent, not which step was reached.** Written as "before Step 2 began", it filed as *nothing attempted* a task abandoned at the design rounds cap, at the invocation ceiling, or at the two-unusable-verdicts stop — three rounds and four reviewers spent, no convergence, and by the counter's own definition that is exactly what it exists to see. A checklist of tasks that all fail to converge before any code exists would never have tripped this brake. So the flag turns at the first reviewer dispatch or the first edit, whichever comes first, and a decline that arrives after one of those counts like any other abandonment.

**The counter is read when a task ends, never when one starts.** Evaluated on entry, a run resumed at the cap re-trips before doing anything, and the `--resume` someone issued *after fixing the cause* becomes a no-op that reports the same stop forever. The brake exists to end a run that cannot progress, not to make progress impossible.

## What "asked" looks like under `auto`

The prompt has to carry enough that a person can answer without reconstructing context, because by definition they were not watching:

```
⛔ TASK [2/6] Drop the per-route auth guard on /search

   Security surface — signal ⓑ (removed lines: requireAuth)
   src/api/search.ts (−1 +1)

   Level is auto; this class is asked at every level.
   Proceed / skip this task / stop the run?
```

Name the class and the signal. "This needs your approval" tells the reader nothing about whether to give it.
