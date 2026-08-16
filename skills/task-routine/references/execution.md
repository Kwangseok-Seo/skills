# execution — the executor contract and its fallback ladder

> Read when **any group Phase 3 produced holds two or more tasks** — that, not the number of groups, is what puts concurrent workers in one repo. A sequential run never needs this file.

## The contract

Anything that claims to be an executor must satisfy all five. Write against the contract, never against a particular tool — that is what lets the ladder degrade without rewriting the cycle.

1. **Isolation.** Two tasks running at once never share a working directory.
2. **Write permission.** Workers can create and edit files. See the failure mode below.
3. **Result readback.** Each worker's changed-file list and summary is retrievable after it finishes.
4. **Termination.** Every worker either finishes or is declared timed out; none can hang the run. The deadline is `execution.timeout_minutes` (default 20), not a number each run invents.
5. **Cleanup is reversible or asked.** See §Cleanup.
6. **Confinement.** The executor can restrict a worker to reading and writing files. A brief cannot constrain a tool the worker is holding: told to hand back a dependency install, a worker with a shell runs `npm i` instead, and only the lockfile delta ever reaches a diff — the `postinstall` already ran. **An executor that cannot restrict its workers' tools does not satisfy this contract**; drop a rung and say so.

Verify / review / commit are **not** the executor's job. They run afterwards, per group, sequentially, in the main thread — one budget, one reviewer, one commit convention.

## The ladder

| Rung | Requires | Isolation | Use when |
|---|---|---|---|
| 1 · Configured multiplexer | the CLI on `PATH` **and** its session environment live | its own panes and worktrees | the user set one up and is watching |
| 2 · Native subagents | nothing beyond `git` | one `git worktree` per task | the default whenever rung 1 is unavailable |
| 3 · Sequential | nothing | none | one group, or a repo where worktrees are impractical |

**Descending a rung is reported, never assumed.** A run that silently drops from 1 to 2 is indistinguishable from a run that never had a multiplexer, and the user's mental model of what happened quietly goes wrong:

```
Executor  rung 2 — native subagents + git worktree
          multiplexer configured (herdr) but HERDR_ENV not set → not in a live session
```

Rung 1 details belong with whatever tool is configured; this skill only requires that it satisfy the five-point contract.

## Rung 2 — native subagents with worktrees

One worktree per task, one subagent per worktree:

```bash
git worktree add -b tr/<task-id> ../<repo>-<task-id>
```

Each subagent gets: the task, the frozen plan from Step 1, its worktree path, and its permission — stated as **what it may do**, never as a list of what it may not:

```
may     read anything · create and modify files under its own worktree path
anything else   do not do it — hand it back to the main thread as a request
                and carry on with the rest of the task
```

**The permitted set is the point.** A worker is the one place in the run with no channel to a human, so nothing it does can be asked about — which means a brief that forbids four actions has silently allowed every action nobody thought to forbid: deleting a file, installing a dependency, calling out to the network, writing outside its worktree. The four hard-stop classes live in the main thread, and handing the action back is a worker's only way to reach them.

Committing, pushing, branch operations, and running the verify command fall out of that rule rather than being enumerated by it — they are also the main thread's work after the merge, and a worker that commits makes the merge unreadable.

Workers return the contract's readback: changed files, a summary, and anything they could not do.

**The main thread commits each worktree before merging it.** A worker writes files and stops; a branch with no commits is still pointing at the group's start commit, so `git merge --no-ff` on it prints `Already up to date`, exits 0, and merges nothing — the loudest possible silence. So, per returned worker, in its worktree: stage its written paths, commit with the repo's convention, then merge. Committing stays in the main thread because that is where the message convention and the hard stops are, not because a commit is dangerous.

```bash
git -C ../<repo>-<task-id> add -A && git -C ../<repo>-<task-id> commit -m "<convention>"
git merge --no-ff tr/<task-id>
```

A branch that still has nothing to commit after its worker returned is the read-only failure below, not a clean result.

### Write permission is the silent failure

A worker started read-only does not error. Its edits are refused one by one and it reports success, because from inside the agent nothing went wrong — it was told no, and it moved on. The run then merges an empty branch and verifies a codebase that never changed.

**Confirm write capability when spawning, and treat "no files changed" as suspect rather than as clean.** A task whose plan named three files and whose worker changed none did not succeed at nothing; it failed at something.

## Merge

Merge groups in dependency order, one at a time, `--no-ff` so the group boundary stays visible in history. A conflict is a stop: report the conflicting paths and ask — *resolve it yourself and continue / abandon this group / stop the run*. Never resolve a cross-worker conflict unattended — the two workers each had a coherent plan, and picking between them is exactly the judgment the dial does not cover.

After a group merges, run the full Step 2 build loop and Step 3 commit for that group in the main thread.

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
