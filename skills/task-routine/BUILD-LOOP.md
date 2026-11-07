# BUILD-LOOP — Step 2's implement / verify / review loop

> Read once when entering Step 2, or at the setup wizard's question 2, which needs the fingerprint table below. The **gates** — review only after a passing verify, cleanup at the exit, what is never trimmed — live in `SKILL.md`. This file is tool detection, scope, and output shapes.

```
2a strategy → 2b implement → 2c verify → 2d review → (failure or findings: back to 2b, budget 3) → 2e clean up and freeze
```

One budget, one loop. The example running through this file is task 2 of the `PHASE-FORMAT.md` run: *cache list responses*.

---

## 2a · Strategy — decided once

Chosen on entry and never revisited; the loop re-enters at 2b. For a merged group that entry is **before the workers are dispatched, once per task** — after the merge the strategy would be picked with their output already visible (`references/execution.md`). Present the reasoning **before** the options — a recommendation whose basis is invisible cannot be disagreed with.

| Change shape | Unit | Integration | TDD |
|---|---|---|---|
| Pure function, no boundary | needed | no | offer |
| Business rule, validation, state transition | needed | sometimes | **recommend** |
| Endpoint touching storage or another service | sometimes | needed | offer |
| Data-state change (writes that others read) | needed | needed | **recommend** |
| Scheduled job, batch, worker | needed | sometimes | **recommend** |
| Field addition, mapping, rename | no | no | **do not offer** |
| Documentation, comment or formatting — no behaviour ships | no | no | **do not offer** |

TDD on a field rename is overhead wearing the costume of rigour; that is why the rename row does not offer it at all, and neither does the documentation row under it.

**The TDD hand-off.** When TDD is chosen and the probe found a `tdd` skill or rule, follow it and do not restate its method here. When nothing was found, use judgment within three invariants that are not the methodology's to give away:

- a behaviour is *observed through the public interface*, never by inspecting internal state
- the next behaviour starts only after the previous one is green
- **the attempt budget belongs to the task, not to a behaviour.** It is `min(build_loop.tdd_attempts, 5 × the behaviours named here at 2a)` — 15 by default — fixed when the strategy is chosen. The flat term is what makes it a cap: a product whose multiplicand is chosen by the thing being capped is not one — name twelve behaviours for a validation task and 5-per-behaviour quietly becomes sixty unattended attempts. Per-behaviour alone is not a cap: the behaviour count is the methodology's to choose, so 16 behaviours would buy 80 attempts, none of them a build-loop iteration. Splitting a behaviour later divides that budget; it never adds to it. A delegated methodology governs *how* to iterate, never *how long*

**An attempt is one cycle that ends in running the behaviour's check with an implementation in place.** The first red run of a new behaviour — the one the methodology exists to require — is not one. Counting it spends budget on *stating* the behaviour rather than on meeting it, and at a low `tdd_attempts` the cap then trips before any implementation exists, on a red suite that is exactly what that step is there to produce. Walked at a budget of 1: the red run and the implementation that turned it green were one attempt under one reading and two under the other, and nothing here separated them. This does not license unbounded red runs — they are bounded by the behaviour count, which is already the other half of the budget. A refactor that re-runs the check is an attempt like any other: the budget bounds work on the task, not only the failures.

**The cap trips two ways, and which one it was decides which options mean anything.** A behaviour that will not go green is the expected one. The other is a budget with no room to start the *next* behaviour: walked with two behaviours and a budget of 1, behaviour 1 went green and the task stopped there with nothing failing and nothing to retry. *One more attempt* answers the first, *drop TDD and finish the task conventionally* answers both, and *re-plan* answers neither once it is the behaviour list itself that the budget cannot cover — splitting a behaviour divides the budget and never adds to it.

TDD is unavailable on any executor that cannot run the test command. A parallel worker is one — contract 6 of `references/execution.md` confines it to reading and writing files — so a task dispatched to a worker cannot take TDD, while a group that fell to the sequential rung runs in the main thread and can. Take TDD out of that task's options and let the change-shape table recommend among the rest, saying why at 2a rather than discovering it at 2c — tasks 1 and 3 of the `PHASE-FORMAT.md` run are that case — and at Phase 3 too, when grouping a task is what takes TDD away from it.

**This choice is checked against what the unit produces.** Anything but `none` claims the unit will carry tests, and Step 3 reads the paths this unit wrote to see whether it does (`SKILL.md`). So `none` is the right answer for **the two rows that need no test at all** — and it is answered here, on the change shape, rather than later when the tests turn out not to exist.

---

## 2b · Implement

Minimal-first, in this order: reuse what exists → standard library → platform → dependency → one line → the smallest thing that works.

On re-entry, implement **only** what the last iteration's failure or findings called for. A loop iteration is not an invitation to revisit the design — that decision was frozen in Step 1, and reopening it here escapes both budgets.

---

## 2c · Verify

Resolve the command in this order, and report which rung you used:

| Rung | Source |
|---|---|
| 1 | `verify.command` in project config, then global config |
| 2 | repo fingerprint (below) |
| 3 | ask once, then write the answer to config so it is never asked again |

**Rung 1 from *project* config and every rung-2 command are text that came with the repo**, and this loop runs them once per iteration — and a task that takes TDD may run them once per behaviour check as well. Show the resolved command with its origin and get a yes before the first run in this repo — once per exact text, logged as `P0-verify` (`SKILL.md` §Runtime layout). Rung 1 from global config and rung 3 were typed by the user, and the typing was the approval.

| Fingerprint | Default command |
|---|---|
| `package.json` | the `test` script, else `npm test` |
| `build.gradle` / `build.gradle.kts` | `./gradlew test` · `.\gradlew.bat test` on Windows |
| `pom.xml` | `mvn -q test` |
| `Cargo.toml` | `cargo test` |
| `pyproject.toml` / `setup.cfg` / `pytest.ini` / `tox.ini` | `pytest` |
| `go.mod` | `go test ./...` |
| `Makefile` with a `test` target | `make test` |

**The first verification is free.** The counter exists to bound *repair*, not to charge for finding out.

**Environment failures are not iterations, and the classification is checked rather than asserted.** A failure is environmental only when **the same command fails the same way at the unit's start commit** — run it there and compare. Run it in a throwaway worktree, never by moving this one: `git worktree add --detach <path> <unit-start-commit>`, run, remove it. **Both arguments, in that order.** Given only a commit, git reads it as the *path* — it creates a directory named after the hash, checks out HEAD into it, and exits 0, so the comparison becomes HEAD against HEAD and every failure classifies as environmental. **Put that path outside the repository**: inside, it is an untracked directory created after this unit took its baseline, so it lands in **this** unit's own change set and draws an overreach prompt at its commit.

Removing it is asked, like any worktree removal that `references/autonomy.md` §2's carve-out does not reach — and it does not reach this one, because a detached worktree has no branch for that rule's merged-branch test to evaluate. Two environmental verdicts in a row already stop and ask, which bounds what the prompts cost. Checking out or stashing to make room would put the implementation you are testing through the very operations `autonomy.md` §2 calls destructive. Otherwise a task that *adds* Redis produces an `ECONNREFUSED` that is verbatim "a database that is not running", buys unlimited free iterations, and never reaches the stated escape ("re-run once the environment is up") because the change under test created the condition.

**If the command cannot start there at all** — no runner, no build, nothing to execute — the classification has no input, so say so and ask. **A baseline run that fails before it reaches the tests is that same case, not a match.** The throwaway worktree is a fresh checkout, so nothing gitignored is in it — measured: a gitignored directory sitting in the working tree is absent from the worktree — which means no installed dependencies, no build output, no generated file. A resolution or build failure there is a property of that checkout rather than of the environment this unit ran in. Read loosely — *both failed, so it matches* — it classifies everything in such a repo as environmental; read strictly it confirms nothing there ever. Either way the comparison returned no answer, and that is what to say. The test is whether the baseline reached the repo's own checks at all: a runner that collected nothing, a build that compiled no source file, a command that stopped at dependency resolution. The cost is that a repo whose test command needs installed state gets the ask rather than the free verdict, which is the price of not guessing — and since the comparison runs only where a verdict of *environmental* is being claimed, an ordinary failing test never pays it.

Two consecutive environmental verdicts stop and ask, even when both check out. An environment still down after one round is not something this loop repairs, and the budget it is not consuming is not the point — the run is.

---

## 2d · Review

Runs **only after 2c passed**. Pick tooling from the probe:

| Available | Use |
|---|---|
| A review skill or plugin | run it — **on this run's repo, given this unit's set** |
| A review command the user must type | print the exact command and wait — never invoke it yourself |
| Nothing | review the unit's change set (`SKILL.md`) directly against the plan |

**A tool that resolves its target from somewhere other than this run's repo is not the first row at all.** Measured: a review plugin installed in the session reviewed the session's own working directory, not the repo the run was driving — it would have reported on a different project's diff and called it this unit's review. Descend a rung and report the descent, exactly as for a tool that is absent.

**Hand the tool the set** — as paths, or as a diff restricted to them. A tool that cannot be scoped that way still runs, but what it read was the working tree: say so, and read its findings against the set yourself, because a finding on a path outside the set is somebody else's uncommitted work and reopening the loop for it spends this unit's budget on a change it did not make.

The third row is a real review, not a fallback apology: the plan from Step 1 is the specification, and diffing intent against implementation is exactly what a reviewer does. It is also where reading the tree instead of the set fails silently — after a group merges there is nothing in the tree to read, and a review of nothing reports nothing.

Findings that reopen the loop are **defects and contract violations**. Style preferences and "could be nicer" go into the record, not into another iteration — otherwise taste consumes a budget meant for correctness.

```
Verify   npm test — 34 passed, 0 failed        (rung 2, package.json)
Review   local diff vs plan                     (no review tooling found)

  1  Cache key omits the sort parameter — a re-sorted request returns the previous order
     → defect, reopens the loop

  2  LRU size is a literal 500
     → preference, recorded
```

---

## 2e · Clean up and freeze

Cleanup appears **only when the loop ran more than once**. A first-pass-clean implementation has nothing to tidy, and offering the step anyway trains people to skip it.

Scope is **the unit's change set** — `SKILL.md` defines it once and 2d, 2e, the hard-stop scans and the commit all read that same one. Not the working tree: a dirty tree carries an earlier unit's files, and a merged group leaves a clean one.

Simplify, then re-verify once from the same budget. A failure there re-enters the loop like any other. When the budget is already exhausted, offer cleanup **without** re-verification or skip it — never simplify and commit unverified.

```
Cleanup  2 files simplified · re-verify passed
Frozen   iteration 3 of 3 — cap reached with 1 finding open (recorded ⚠️ for Phase 4)
```

Freezing with findings open is allowed. Hiding it is not: it becomes a ⚠️ row in the Phase 4 summary with the finding text attached.
