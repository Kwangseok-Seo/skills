# PHASE-FORMAT — what Phase 1–4 put on screen

> Read once when entering Phase 1. The **gates** (what must not happen) live in `SKILL.md`; this file is the **shape of the output**. Copy the shapes, never the sample data.

Every example below is the same run: a Node/TypeScript API repo, a local `TODO.md` with four open items. One run, four phases, so the shapes connect. Two blocks depart from it and both say so where they appear: the Phase 4 brake trip, which that run never reaches, and the pending-completions prompt, which needs a remote source.

---

## Phase 1 — Resolve

**The effective configuration prints first**, before anything is resolved — the dial, the caps, the source, the verify command, each tagged with where it came from, plus anything that was ignored. Then report three things about the source: where you looked, what you found, how old it is. Freshness is what carries the recommendation.

The prior analysis is **the newest run in this project's decision log with the same `source_ref`**, and its order and grouping come from that run's checkpoint. There is no separate analysis file to write, go stale, or be committed into the repo by accident.

| Age of the prior run against the same source | Recommendation |
|---|---|
| ≤ 24h | reuse its order and grouping |
| 24h – 7d | reuse, flagged as ageing |
| > 7d | re-derive them |
| > 30d | ignore it — proceed as if there were none |

```
Config    level auto (--auto) · max_tasks 5 (global) · source TODO.md (project)
          verify "npm test" (project config, approved for this repo)
Ignored   autonomy.level in project config — the dial is not the repo's to set

Source    TODO.md (local markdown) · 4 open items
Prior     run 20260816T0611 on TODO.md — 3h ago → reuse its order (≤24h)

  1  [ ] Add a sort parameter to the list API
  2  [ ] Cache list responses
  3  [ ] Require admin role on /admin/*
  4  [ ] Report cache hit rate
```

A repo that keeps no tests as separate paths — Rust `#[cfg(test)]`, in-source Vitest — gets one more line here, `Tests    in-source; the Step 3 claim check does not run in this repo`, and that is the only place it is ever said (`SKILL.md` §Step 3).

`Ignored` appears only when something was, and so does `Prior` — a project's first run against a source has no prior run, which is reported by the line's absence, not by a line saying there is nothing. On the first run in a repo — or whenever the command's text changed since it was approved — the verify line is a prompt rather than a report:

```
⛔ Verify command supplied by the repo, not by you

   node scripts/verify.js          (.claude/task-routine.json)
   It runs once per build iteration, up to 3 per unit.

   Approve for this repo / type a different command / stop
```

When nothing is found, the shape is the same minus the recommendation — and when **no items** come back, print the paths you searched and stop there. An empty source is a reportable outcome, not an invitation to invent work:

```
Source    TODO.md (local markdown) · 0 open items
Looked    ./TODO.md · ./docs/TODO.md · .claude/task-routine.json → source.path

No open items. Nothing to run.
```

---

## Phase 2 — Order

Show the edges, not just the result. A reordering the user cannot check is a reordering they cannot correct.

```
Order     by dependency (2 edges found)

  1 → 2   the cache key has to include the sort parameter, so sorting lands first
  2 → 4   nothing to measure until the cache exists
  3       independent

Result    1, 3, 2, 4      (source order was 1, 2, 3, 4)
```

Keeping the source order is a legitimate outcome and gets the same shape with `Result    unchanged`.

---

## Phase 3 — Group and pick an executor

### Grouping verdicts

| Relationship between two tasks | Verdict |
|---|---|
| B consumes A's output | **sequential** |
| Disjoint files | **parallel** |
| Same file, different regions | parallel is possible — order them anyway once the diffs would overlap |
| Same file, same region | **sequential**, always |

### Executor ladder — highest available rung wins

| Rung | Requires | Isolation |
|---|---|---|
| Configured multiplexer | probe found the CLI **and** its session env is live | its own panes / worktrees |
| Native subagents | always available | one `git worktree` per task |
| Sequential | — | none |

**Name the rung you landed on and why the higher ones were unavailable.** A run that silently degrades from parallel to sequential looks identical to a run that was never parallel.

```
Groups

  G1  (parallel)     1  Add a sort parameter    src/api/list.ts
                     3  Require admin role      src/api/admin.ts, src/auth/guard.ts
  G2  (after G1)     2  Cache list responses    src/api/list.ts, src/cache/*
  G3  (after G2)     4  Report cache hit rate   src/cache/metrics.ts

  ⚠️ 1 and 2 both touch src/api/list.ts — different regions, so ordered rather than parallel

Executor  native subagents + git worktree
          multiplexer not configured · codex not installed → rung 2 of 3
```

---

## Phase 4 — Summary

### Result table

| Column | Holds |
|---|---|
| `#` / task | index and title |
| status | ✅ done · ⚠️ progressed past a cap · ⏭️ skipped · ❓ finished, but it committed something the run cannot stand behind — its test strategy and what it wrote disagree (no test where one was claimed, or behaviour where `none` was), or it passed a dirty-path stop and its commit is not the tree 2c verified. **⚠️ advances the consecutive-failure counter, and ⏭️ advances it only for a task this run had already spent a budget on**, ✅ clears it, ❓ does neither (`SKILL.md`) |
| tests | the strategy actually used, not the one chosen |
| re-verify | failed re-verification count · `(cap)` when the cap was hit · `(group)` when the count is a merged group's shared one |
| commit | short hash, or `—` when nothing was committed |

```
Task Routine — TODO.md · 4 tasks · level auto · 18m

| # | task                   | status | tests    | re-verify | commit  |
|---|------------------------|--------|----------|-----------|---------|
| 1 | Add a sort parameter   | ✅     | unit+int | 1 (group) | a1b2c3d |
| 3 | Require admin role     | ✅     | unit+int | 1 (group) | c3d4e5f |
| 2 | Cache list responses   | ⚠️     | unit+int | 3 (cap)   | e4f5g6h |
| 4 | Report cache hit rate  | ❓     | none     | 0         | f7g8h9i |

4 commits · 14 files changed
⚠️ task 2 froze at the cap with 1 finding open — "LRU eviction has no test" — review it by hand
❓ task 4 chose "unit" at 2a and wrote no test path (src/cache/metrics.ts alone).
   Committed and green; no test this unit added stands behind it.
Consecutive failures 1 of 2 after task 2 — task 4 ❓ neither advanced nor cleared it
TODO.md — 4 completion marks, uncommitted
```

Tasks 1 and 3 were one merged group, so they show **one** shared re-verify count, not one each. The failure-counter line appears only when that counter moved: printing `0 of 2` every run is noise, and printing nothing after it moved hides how close the run came to stopping.

A `❓` row from an unmet test claim has its `tests` cell reading `none` because that column holds what was **used**; the strategy that was *chosen* belongs in the line underneath, which is the only place the contradiction is legible. A unit that legitimately chose `none` prints `none` here too and keeps its ✅ — the two rows differ in what was claimed, never in what the cell shows, which is why the line reports the claim.

When the brake does trip, the run stops where it stands and names what tripped it — this is the six-task run traced in `references/autonomy.md`, not the one above:

```
⛔ consecutive-failure brake — 2 tasks in a row ended ⚠️ or ⏭️ (task 5 ⚠️ cap · task 6 ⏭️)
⏭️ tasks 7, 8 not attempted

   Checkpoint written. --resume picks up at task 7 — the first unit still pending — with counters restored.
   Task 6 was attempted and skipped; skipped is a finished status, not a retry.
```

### Decision audit — mandatory whenever the run was not fully manual

Four columns, and the fourth is the one that matters: **did the outcome support the choice?** A decision table without outcomes is a log, not an audit.

```
Decisions made on your behalf (level auto)

| task | step      | chose        | because                          | outcome        |
|------|-----------|--------------|----------------------------------|----------------|
| 1    | S1-design | skip loop    | 1 file, no new interface         | clean          |
| 1,3  | S2-test   | unit+int     | the group's widest surface       | 1 re-verify (G1) |
| 3    | S1-design | 2 rounds     | new auth surface                 | 1 blocking fix |
| 2    | S2-test   | unit+int     | cache layer is an integration    | 3 re-verify ⚠️ |
| 2    | S2-review | local diff   | no PR; gh present, branch unpushed | 1 finding     |
| 4    | S2-test   | unit         | pure function, no boundary       | claim unmet ❓ |

Asked, not automatic: task 3 security surface (approved), task 2 cap reached (froze as-is)
```

The second line is not decoration. Showing what **stopped** for a human next to what did not is how the reader tells "nothing was risky" from "the guard never fired".

### Pending completions — everything the run could not write

One prompt per run, listing everything held since Step 3. This block needs a remote source, so it is the GitHub-issue variant of the run above rather than its `TODO.md` original:

```
Pending completions — GitHub issue #142, 4 items
  ☑ 1  Add a sort parameter
  ☑ 3  Require admin role
  ☑ 2  Cache list responses
  ☑ 4  Report cache hit rate

Writing to the tracker is never automatic. Apply all four?
```

Anything declined or failed stays `pending` in the checkpoint and is reported as pending — never as done.
