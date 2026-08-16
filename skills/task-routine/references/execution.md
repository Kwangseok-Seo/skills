# execution — the executor contract and its fallback ladder

> Read when **any group Phase 3 produced holds two or more tasks** — that, not the number of groups, is what puts concurrent workers in one repo. A sequential run never needs this file.

## The contract

Anything that claims to be an executor must satisfy all six. Write against the contract, never against a particular tool — that is what lets the ladder degrade without rewriting the cycle.

1. **Isolation.** Two tasks running at once never share a working directory.
2. **Write permission.** Workers can create and edit files. See the failure mode below.
3. **Result readback.** Each worker's changed-file list and summary is retrievable after it finishes.
4. **Termination.** Every worker either finishes or is declared timed out; none can hang the run. The deadline is `execution.timeout_minutes` (default 20), not a number each run invents.
5. **Cleanup is reversible or asked.** See §Cleanup.
6. **Confinement.** The executor can restrict a worker to reading and writing files. A brief cannot constrain a tool the worker is holding: told to hand back a dependency install, a worker with a shell runs `npm i` instead, and only the lockfile delta ever reaches a diff — the `postinstall` already ran. **An executor that cannot restrict its workers' tools does not satisfy this contract**; drop a rung and say so.

Verify / review / commit are **not** the executor's job. They run afterwards, per group, sequentially, in the main thread — one budget, one reviewer, one commit convention.

**The test strategy is not the executor's either, and it goes the other way round: `S2-test` is chosen per task, in the main thread, *before* that task's worker is dispatched, and it goes in the brief.** It names what will verify the task, so choosing it after the merge means choosing it with the workers' tests, or their absence, already on screen — and Step 3 would then be checking a claim against the thing that produced it, which no unit can fail. Decided up front it is a commitment the worker is asked to meet.

## The ladder

| Rung | Requires | Isolation | Use when |
|---|---|---|---|
| 1 · Configured multiplexer | `execution.executor` set, its `command` on `PATH`, **and** its `session_env` set and non-empty | its own panes and worktrees | the user set one up and is watching |
| 2 · Native subagents | nothing beyond `git` | one `git worktree` per task | the default whenever rung 1 is unavailable |
| 3 · Sequential | nothing | none | one group, or a repo where worktrees are impractical |

**Descending a rung is reported, never assumed.** A run that silently drops from 1 to 2 is indistinguishable from a run that never had a multiplexer, and the user's mental model of what happened quietly goes wrong:

```
Executor  rung 2 — native subagents + git worktree
          multiplexer configured (herdr) but HERDR_ENV not set → not in a live session
```

Rung 1 details belong with whatever tool is configured; this skill requires the key above (`references/setup.md`) and that the tool satisfy the six-point contract. **With no `execution.executor` there is no rung 1 to be unavailable**: a run reporting "multiplexer not configured" is naming an absent key rather than an absent binary, and that is the state of every run until someone writes one.

## Rung 2 — native subagents with worktrees

One worktree per task, one subagent per worktree:

```bash
git worktree add -b tr/<task-id> ../<repo>-<task-id>
```

Each subagent gets: the task, the frozen plan from Step 1, **the `S2-test` strategy chosen for it above**, its worktree path, and its permission — stated as **what it may do**, never as a list of what it may not:

```
may     read anything · create and modify files under its own worktree path
anything else   do not do it — hand it back to the main thread as a request
                and carry on with the rest of the task
```

**The permitted set is the point.** A worker is the one place in the run with no channel to a human, so nothing it does can be asked about — which means a brief that forbids four actions has silently allowed every action nobody thought to forbid: deleting a file, installing a dependency, calling out to the network, writing outside its worktree. The four hard-stop classes live in the main thread, and handing the action back is a worker's only way to reach them.

Committing, pushing, branch operations, and running the verify command fall out of that rule rather than being enumerated by it — they are also the main thread's work after the merge, and a worker that commits makes the merge unreadable.

Workers return the contract's readback: changed files, a summary, and anything they could not do.

**The main thread commits each worktree before merging it.** A worker writes files and stops; a branch with no commits is still pointing at the group's start commit, so `git merge --no-ff` on it prints `Already up to date`, exits 0, and merges nothing — the loudest possible silence. So, per returned worker, in its worktree: stage what it wrote, commit with the repo's convention, then merge. Committing stays in the main thread because that is where the message convention and the hard stops are, not because a commit is dangerous.

**What it wrote is read twice, and the two readings have to agree.** `git add -A` here commits whatever is in that directory — the worker's work, and equally the build output, the cache directory, the scratch file nobody gitignored. That is the discipline `SKILL.md` spends a whole section establishing for every other commit in this skill, dropped in the one place a human is furthest away. Taking the worker's returned list instead only trades it for the quieter failure: a worker that under-reports loses work at the merge and nothing says so.

So compare them — the worktree's own change set, computed from the group's start commit with the two commands `SKILL.md` names, against the changed-file list the contract's third point already requires. **Equal → commit exactly that, the way Step 3 commits it**: `--only`, the readback, the argument-limit form, one act defined once and performed in another directory. **Different → stop and ask**, naming both sides, because the worker either wrote outside what it reported or reported what it did not write, and neither is a thing to merge on a guess. Compare them as **sets of repo-relative paths**, normalised first: a worker writes prose, and an absolute path, a `./` prefix or a different separator is a disagreement about spelling, not about what happened. A guard that stops on spelling gets switched off.

```bash
git -C ../<repo>-<task-id> commit --only -m "<convention>" -- <the agreed paths>
git merge --no-ff tr/<task-id>
```

A branch that still has nothing to commit after its worker returned is the read-only failure below, not a clean result.

### Write permission is the silent failure

A worker started read-only does not error. Its edits are refused one by one and it reports success, because from inside the agent nothing went wrong — it was told no, and it moved on. The run then merges an empty branch and verifies a codebase that never changed.

**Confirm write capability when spawning, and treat "no files changed" as suspect rather than as clean.** A task whose plan named three files and whose worker changed none did not succeed at nothing; it failed at something.

## Merge

Merge groups in dependency order, one at a time, `--no-ff` so the group boundary stays visible in history. A conflict is a stop: report the conflicting paths and ask — *resolve it yourself and continue / abandon this group / stop the run*. Never resolve a cross-worker conflict unattended — the two workers each had a coherent plan, and picking between them is exactly the judgment the dial does not cover.

**Each answer says what becomes of the merge, because none of them disposes of it by default:**

| Answer | The merge in progress |
|---|---|
| resolve it yourself and continue | stays until the resolution is staged and `git merge --continue` completes it — **not** Step 3's `--only` form, which git refuses mid-merge with one of the 128s `SKILL.md` already sorts out. Ask git whether there is still a merge to finish rather than assuming there is: `git rev-parse -q --verify MERGE_HEAD`, empty and exit 1 meaning the resolver already committed it. Unstaged, `--continue` refuses; and it takes no arguments, so the `--no-edit` reached for by analogy is a **129**, not a merge |
| abandon this group | `git merge --abort`, **whose exit is read** — see below |
| stop the run | stays, and the report says so: what is being handed back is a repository sitting mid-merge |

Saying nothing is not the same as leaving it alone. A conflicted tree keeps the markers in tracked files, so that path stays in the unit's change set — measured, `git diff --name-only --no-renames <group-start>` lists a `UU` path — and from there it reaches 2c, the hard-stop scans, and the next unit's `dirty_at_start`.

**`git merge --abort` can refuse, and one thing that refuses it is something this skill creates.** A non-zero exit means the abandon did not happen and the merge is still there. Measured and isolated: an intent-to-add entry in the index — from the `git add -N` the change-set computation requires — exits **128** with `Entry '<path>' not uptodate. Cannot merge.`, while an ordinary modified file and an untracked file both abort cleanly. When that entry is one **this run** made — the early untracked read in `SKILL.md` is what tells those from the user's — `git rm --cached` on it restores the abort, and the file stays on disk untracked. Any other cause, that one included once it turns out to be the user's: report the state and hand it over. **Never escalate to `git reset --hard`** — whatever blocked the abort is uncommitted work, and this is the one path where the repair costs more than the failure.

An abort that succeeds destroys nothing the two branches do not still hold, since re-running the merge reproduces the conflicted tree; that is why `autonomy.md` §2's recoverability test does not turn it into a second question after the answer to abandon already came. **A resolution someone had already started by hand is the exception** — those edits are in neither branch — so name them and confirm before discarding them.

After a group merges, run Step 2 for that group in the main thread starting at **2c** — the strategy was chosen before dispatch and the implementation is what just merged — re-entering at 2b for repairs like any other iteration, then Step 3.

**The hard stops are evaluated here.** A worker cannot prompt, so the four classes are checked in the main thread against the group's change set — the pinned set from `SKILL.md`, computed from the group's own start commit, which survives the merge that empties the working tree. A security surface written by a worker is asked about the same as one written sequentially, just later in the cycle. Requests workers handed back are answered in the same place, with the same classes applied.

A group has one change set but **N frozen plans**, so the scope test reads their **union**: asking whether task 3's plan named a file that task 1 deleted produces a false stop, and asking no plan at all produces a false pass.

## Cleanup

Removing a worktree is destructive local work, which is a hard stop — with one carve-out, stated as a rule so it stays correct as the tooling changes:

```
this run created it  ∧  its branch is merged  ∧  the worktree is clean   → auto-eligible
anything else                                                            → ask
```

All three conjuncts, and the third is the one an enumeration drops. A branch with **no commits** is trivially an ancestor of HEAD, so `git branch --merged` lists it: without the clean-worktree test, a worktree full of unstaged worker output reads as "merged, nothing lost" and gets removed with `--force`. Nothing is lost only when the content is in the branch *and* the directory holds nothing that is not.

Before finishing, list worktrees and report any this run created that still exist. Leaked worktrees are cheap to leave and expensive to discover months later.

## Timeouts

Every worker gets a deadline. On expiry, report which are still running and ask: wait longer / take what finished / stop. Compute it the portable way: record the start time once, and on each poll compare elapsed seconds against the deadline. No `timeout(1)`, no `gtimeout`, no shell-specific arithmetic — a portability failure inside the timeout logic turns a slow worker into a hung run, which is the one failure this rule exists to prevent.
