# DESIGN-LOOP — Step 1's review protocol

> Read once when entering Step 1 — **including when the loop is about to be skipped**, because §When to skip below is what settles that and `SKILL.md` sends the decision here. Gated on the loop already being enabled, this file would be needed to make a decision that decides whether to read it. The **gates** — plan-not-reasoning, who decides, when to skip — live in `SKILL.md`. This file is the protocol and its output shapes.

```
1a gather → 1b design → 1c independent review → 1d apply → (back to 1c, max 3) → 1e freeze
```

The example running through this file is task 3 of the `PHASE-FORMAT.md` run: *require admin role on `/admin/*`*.

---

## 1a · Gather

Read two sources before writing any plan. One alone produces a predictable failure:

| Source | What it answers | Reading only this gives you |
|---|---|---|
| **The floor** — what the code does now | conventions, existing seams, what already exists to reuse | legacy reproduced faithfully, including its mistakes |
| **The ceiling** — what a mature reference implementation does | the idiom, the failure modes others already hit | a design that fights the codebase it lands in |

Match a legacy **surface** — naming, file layout, error shape — so the diff reads like the repo. Do not match legacy **reasoning**. When those two pull apart, that is a deliberate departure and it gets written down (below), not smoothed over.

Delegate a broad sweep to a search agent; do the reading yourself. A summary of files you never opened is not grounding.

---

## 1b · Design

The plan states, in this order: what changes, where, and what stays untouched. Any deliberate departure from local convention gets exactly three lines:

```
Departure  guard middleware instead of a per-handler check
  problem  12 handlers under /admin/*, each re-implementing the role test
  solves   one place to change when the role model changes; new handlers are covered by default
  cost     the middleware ordering becomes load-bearing — a later reorder can silently disable it
```

The third line is the one that earns its place. A departure with no stated cost has not been thought through.

---

## 1c · Independent review

### Picking the reviewer

Highest available rung wins, and **say which one you landed on**:

| Rung | Requires | Independence |
|---|---|---|
| Different vendor's CLI | probe found it, runs non-interactively | different model, different training, different prompt lineage |
| Subagent on a different model | always available | different model, same lineage |
| Fresh subagent, same model | always available | context isolation only |

Rung 3 is a real check — a fresh context genuinely catches things — but it is the weakest of the three, and a report that omits which rung was used converts that caveat into a claim.

Rung 1's details belong with whatever tool is configured. This skill requires only that it take the brief on stdin or as a file argument, run non-interactively, and return one of the four verdicts below. **A configured tool that cannot do all three is not rung 1** — fall to rung 2 and report the descent, the same as any other.

### The brief

Include:

- the task statement and its acceptance criteria
- the plan, verbatim
- the sources it cites — file paths plus what each one showed
- on round 2+: what changed since the last round, one line per applied finding

Exclude:

- the design conversation, in any summarised form
- the designer's reasoning beyond the three-line departure note
- your own assessment of the previous round's findings

**The exclusion list is the point of the whole step.** A reviewer handed the designer's argument reproduces it and returns approval — and that approval is worse than no review, because it reads as corroboration. If you are unsure whether something belongs in the brief, leave it out; a reviewer that asks for more context is a working reviewer.

### The verdict

| Position | Means |
|---|---|
| `APPROVE` | build it |
| `APPROVE_WITH_CHANGES` | build it after the blocking findings are fixed |
| `REJECT` | the approach itself is wrong, not its details |
| `NEEDS_MORE_INFO` | the brief was insufficient — supply what was asked and re-run; the round counter does not move, the invocation counter does |

Findings split two ways, and the reviewer does the splitting:

- **blocking** — the plan is wrong or incomplete without this
- **non-blocking** — an improvement, a preference, a follow-up

```
Review — task 3 · rung 2 (subagent, different model) · round 1
APPROVE_WITH_CHANGES

blocking
  1  The middleware is registered after the route table, so /admin/health resolves before
     the guard runs. The plan's ordering note says "early" without pinning where.

non-blocking
  2  Consider a typed Role enum rather than string comparison
  3  No test named for the ordering property; it will regress silently
```

---

## 1d · Apply

Fix blocking findings. Record the rest in the plan under `deferred` with a one-line reason — recording is not agreeing, and the next round should not re-litigate them.

`NEEDS_MORE_INFO` is not a round: supply what was asked and re-run without incrementing the round counter, so a reviewer cannot exhaust the design budget by asking questions.

**It is still an invocation, and invocations carry their own ceiling.** Count every dispatch of the brief to a reviewer, whatever comes back — verdicts that count as a round, verdicts that do not, and retries after a tool failure — and cap the total per task at `design_loop.rounds + 1` (4 by default). Exempting a verdict from the round counter without counting it somewhere is how the exemption becomes an unlimited budget: the brief withholds context deliberately, each re-run is a fresh reviewer asking a *different* question, and the rounds counter never leaves 0.

Two in a row stops earlier than the ceiling. A second consecutive dispatch that comes back without a usable verdict — `NEEDS_MORE_INFO` again, or nothing parseable — means the brief and the reviewer are not converging, and a third will not fix that. Report both questions and ask: answer them / freeze the plan as-is / SKIP this task / stop.

---

## 1e · Freeze

Exit on the **first** clean verdict — `APPROVE`, or zero blocking findings. Rounds are a ceiling, not a quota; spending a third round on an already-clean design costs a subagent and buys nothing.

`APPROVE_WITH_CHANGES` with every blocking finding applied **is** that clean verdict, and it exits here rather than looping back to 1c. The verdict's own definition is "fix these, then build"; returning to hear that the fixes are fixed spends an invocation on an answer nobody doubted. Name the applied fixes in the freeze so the record carries them. One exception reopens the loop: a blocking fix that moves the **surface itself** — a new public method, a schema change, a new dependency — for the same reason a later task extending that surface would.

```
Review — task 3 · rung 2 · round 2
APPROVE
  ordering pinned to app.use() before the router; property test added to the plan

Design frozen at round 2 of 3.
```

At the **rounds** cap, ask: one more round / freeze as-is / SKIP this task / stop. At the **invocation** ceiling the option set is *freeze as-is / SKIP this task / stop* — "one more" is not offered, because the ceiling is the outer bound and an outer bound that offers to move itself is a suggestion. The next dispatch would re-trip it and ask again, bounded only by the patience of someone who by definition is not watching. Freezing with unresolved blocking findings is allowed, and it must be carried into the Phase 4 summary as a ⚠️ row.

---

## When to skip the loop

Run it when the change creates something that is expensive to reverse; skip it when the change is local and obvious.

| Skip | Run |
|---|---|
| One file, no new interface | New or changed public interface |
| Rename, field addition, copy edit | Schema, data format, or wire format |
| Config value change | New dependency |
| Behaviour already covered by a test | New security or permission surface — read from the **task text** against the ⓑ vocabulary, since no diff exists yet |
| — | Three or more files across modules |

**A surface already reviewed in this run does not trigger the loop again.** A checklist usually slices one feature, so four of its tasks touch the same new module — reviewing that design once per slice pays four times for one answer, and each reviewer sees a fragment with no sight of the others, so all four report the same missing integration story that the next task supplies. Extend the frozen plan instead, and record the extension:

```
Design    extends the plan frozen at task 1 (surface: src/cache/*)
          new: invalidation hook · no re-review
```

Re-open the loop only when the extension changes the surface itself — a new public method on that interface, a schema change, a new dependency. Adding another caller to an interface reviewed an hour ago is not a design decision.

Under `--auto` this arithmetic matters: the loop costs up to three subagents per task, times the task cap. A skipped loop is reported with its reason, the same as a run one.
