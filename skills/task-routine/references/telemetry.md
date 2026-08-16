# telemetry — the decision log and the checkpoint

> Read when writing a decision record or a checkpoint, or when analysing the log. The log is what makes raising the dial an argument from evidence rather than a mood; the checkpoint is what makes `--resume` mean anything.

```
~/.claude/task-routine/<project-slug>/decisions.jsonl
```

`<project-slug>` is the repo path with separators replaced by `-`. `TASK_ROUTINE_DIR` overrides the root. Outside the repo, always — an unattended run that stages files must not be able to commit its own log.

## Two record kinds, never one edited twice

A **decision** is written when the choice is made. An **outcome** is written in Phase 4, as a *new line*, linked by `decision_id`.

```jsonc
// decision — written at the moment of choosing
{
  "kind": "decision",
  "id": "d-20260816T0914-3",          // <run_id>-<n>, unique within the log
  "ts": "2026-08-16T09:14:22+09:00",
  "run_id": "20260816T0914",
  "skill_version": "task-routine@1.0.0",
  "model": "<model id, when known>",
  "source_ref": "TODO.md",
  "task_id": "cache-list-responses",  // the adapter's stable id; an ARRAY of ids when the
                                      // decision belongs to a unit rather than a task;
                                      // null before any task is picked
  "step_id": "S2-test",
  "risk_tier": "auto-eligible",
  "level": "auto",                    // the dial at the time
  "mode": "auto",                     // "auto" = ran unattended, "asked" = a human answered
  "options": ["unit", "integration", "unit+integration", "none"],
  "recommended_index": 2,
  "chosen_index": 2,
  "agreed": true,                     // chosen == recommended; null when there was no recommendation
  "rationale": "cache layer is an integration surface"
}
```

```jsonc
// outcome — written in Phase 4, appended, never merged into the line above
{
  "kind": "outcome",
  "decision_id": "d-20260816T0914-3",
  "ts": "2026-08-16T09:31:05+09:00",
  "build_iterations": 3,
  "design_rounds": 0,
  "verification_ran": true,
  "review_ran": true,
  "review_flagged": true,
  "reverted": false,
  "manual_intervention": false,
  "capped": true,
  "claim_met": "unmet"         // S2-test outcome lines ONLY: "met" · "unmet" · "unclaimed"
                               // (strategy was none). Absent where the repo keeps no tests
                               // as separate paths at all and the check does not run
}
```

**`claim_met` belongs to `S2-test` and to no other line**, because it is that decision's own outcome: the strategy said what would verify the unit, and the paths the unit wrote either hold a test path or do not (`SKILL.md` §Step 3). `unclaimed` is a `none` strategy that also passed the reverse check; a `none` unit that shipped behaviour anyway is `unmet` like any other. Writing it onto the unit's other decisions would file one observation against four separate judgments. Three values rather than a boolean, because *nothing was claimed* and *the claim went unmet* are different facts and only the second is a finding. The absent case is different again and belongs to the **repo**, not the unit — it is reported once in Phase 1, never once per row.

`recommended_index` and `chosen_index` are indices into **the `options` array as actually written on this line** — count them from the array, never from a numbered list in a document. Options get reordered; a stale index silently records disagreement where there was none.

**A decision is logged once at the scope it was taken, and `task_id` records that scope.** A merged group takes some decisions once for the whole unit; writing those out per task multiplies one judgment across the `n (asked)` population the dial is later raised from, and no query can tell the copies apart afterwards.

## The checkpoint

Different file, different rules: the log is append-only history, the checkpoint is **replaceable current state**. Interrupt and resume are separate invocations, so this schema is a contract between them — whatever the first writes, the second has to be able to read.

```jsonc
// ~/.claude/task-routine/<project-slug>/run-<run_id>.json — rewritten in place after each unit
{
  "version": 1,
  "run_id": "20260816T0914Z-a3f",   // UTC at run start + 3 random chars — the same id the log uses
  "updated_at": "2026-08-16T09:31:05+09:00",
  "source_ref": "TODO.md",
  "level": "auto",
  "level_origin": "--auto",         // "--auto" | "--level" | "global" | "default" — never "project"
  "consecutive_failures": 1,        // per run — the one counter that must survive a unit boundary
  "units": [                        // execution order, one entry per unit
    { "id": "g1", "task_ids": ["add-a-sort-parameter", "require-admin-role"],
      "status": "done", "start_commit": "9a8b7c6", "dirty_at_start": [], "build_iterations": 1,
      "workers": { "add-a-sort-parameter": { "branch": "tr/add-a-sort-parameter", "state": "merged" },
                   "require-admin-role":   { "branch": "tr/require-admin-role",   "state": "merged" } } },
    { "id": "t2", "task_ids": ["cache-list-responses"],
      "status": "capped", "start_commit": "a1b2c3d", "dirty_at_start": ["notes.md"],
      "build_iterations": 3 },
    { "id": "t4", "task_ids": ["report-cache-hit-rate"],
      "status": "pending", "start_commit": null, "dirty_at_start": null, "build_iterations": 0 }
  ],
  "tasks": {
    "cache-list-responses": { "status": "capped", "commit": "e4f5g6h", "design_rounds": 1,
                              "reviewer_invocations": 2,
                              "tests_claimed": "unit+int", "tests": "unit+int",
                              "tdd_behaviours": 0, "tdd_attempts": 0,
                              "consecutive_environmental": 0, "consecutive_unusable_verdicts": 0 }
  },
  "pending_completions": []         // remote completions held for the Phase 4 flush — AND any local
}                                   // write that was attempted and failed, so a read-only or renamed
                                    // source cannot leave a committed task looking un-done forever
}
```

- **`run_id` is the id**, and the filename carries it. Fixed-width, so "newest checkpoint" is the largest filename in string order — no timestamp parsing, no filesystem mtime, which is wrong the moment a file is copied. **UTC**, because local time repeats an hour at every DST fallback and string order stops meaning newest. The random suffix is what keeps two runs started in the same minute from sharing a filename and colliding their `d-<run_id>-<n>` decision ids, which the append-only design explicitly allows.
- **Written when a unit starts, again as soon as it commits, and again when it ends** — not only at the end. The middle write is what makes a mid-Step-3 interrupt resumable at the completion mark instead of back inside the build loop (`SKILL.md` §Arguments); without it there is no checkpoint state that is `pending` and carries a commit. A unit interrupted mid-flight must already have its `start_commit` and `dirty_at_start` on disk, or resume has no baseline to restore and re-derives one from a tree that is dirty with the unit's own work.
- **`status`** uses the Phase 4 vocabulary plus `pending`: `done` ✅ · `capped` ⚠️ · `skipped` ⏭️ · `unverified` ❓ (finished, but nothing stands behind what it committed — no test where the strategy claimed one, or a commit that is not the tree verify passed on) · `pending` (**unfinished** — never started, *or* interrupted mid-flight). All but `pending` are finished; the counter clears on `done`, advances on `capped` and on `skipped` **with `attempted: true`**, and `unverified` moves it neither way (`SKILL.md`). That flag is why `skipped` needs one: a task declined before this run spent anything on it stores the same status as one abandoned after a whole budget went into it, and `autonomy.md` counts only the second — without the field, two correctly-declined security prompts stop a run in which nothing failed, and no later read of the checkpoint can tell that it should not have. It turns at the first reviewer dispatch or the first edit, so a task abandoned at the design cap is stored `attempted: true` with `build_iterations: 0`; keyed to Step 2 instead, that row would be indistinguishable from a task nobody ever worked on. Storing that verdict here rather than recomputing it is what lets a resumed run reprint the ❓ row — with `tests_claimed` beside `tests`, since a row that reports only what was *used* would say a unit claiming `none` failed to meet a claim it never made. The change set is gone by resume time, so the offending paths are not reprinted; what survives is the claim and the fact that nothing confirmed it, which is what sends the reader to the commit. An ad-hoc `stop` therefore leaves the current unit `pending` with its counters as they stand: resume re-enters it and continues on the budget it had left, rather than restarting it with a fresh one or abandoning it as though a cap had been reached.
- **`dirty_at_start` is persisted, not re-derived.** It is the other half of the unit's baseline, and at resume time the tree is dirty with *this unit's own work* — re-snapshotting it there would file the unit's own edits as somebody else's and either drop them from the commit or stop on every resume. `null` means the unit has not started; `[]` means it started against a clean tree.
- **A group unit records its workers.** Resume re-spawns only workers whose `state` is not `returned` or `merged`; a branch that already exists is reused, never rebuilt. Without this a brake that trips mid-group either discards a finished worker's branch or merges it twice.
- **Every counter named in `SKILL.md`'s scope table appears here, at the scope that table assigns it** — as a rule, not as a list to keep in sync: `build_iterations` and `start_commit` on the unit, `design_rounds` / `reviewer_invocations` / `tdd_behaviours` / `tdd_attempts` on the task, `consecutive_failures` at the top. The two-in-a-row stops count too (`consecutive_environmental` from `BUILD-LOOP.md` §2c, `consecutive_unusable_verdicts` from `DESIGN-LOOP.md` §1d) — a counter that resets across an interrupt is a stop that never fires. Storing one at the wrong level is how resume silently hands a task a fresh budget.
- `--resume` loads the newest checkpoint for this project and continues at the **first unit whose status is `pending`**; `capped`, `skipped` and `unverified` units are finished, not retried. A checkpoint with no `pending` unit is a completed run — resume says so and stops, **unless `pending_completions` is non-empty**, in which case it reopens at the Phase 4 flush and does nothing else. The level stored here is **not** permission: an unattended resume needs `--auto` again, because unattended is always an explicit choice.
- **A finished run's checkpoint is kept, not deleted.** It is what the next run reads as its prior analysis (`PHASE-FORMAT.md` §Phase 1) — the order and grouping live here and nowhere else, so deleting it on success would delete exactly the record the freshness table recommends reusing. Prune older checkpoints for the same `source_ref` if you like; keep the newest.
- Nothing is considered finished while `pending_completions` is non-empty.

## Why append-only

The obvious design is one record per decision, updated in place when the outcome is known. It fails in a specific, observed way: matching the record to update requires a key, keys drift between sessions, and an over-broad match rewrites *other sessions' records*. Once that happens the log is worse than empty, because it looks complete.

Append-only removes the failure rather than defending against it. Nothing is ever matched-and-rewritten, so there is nothing to over-match. A missing outcome line simply means the run did not finish — which is true, and worth knowing.

Consequences, all of them good:

- No backup files, no restore procedure, no "exit 2 if the filter is too broad" gate.
- Concurrent runs in the same repo append safely; ordering does not matter because every line is self-contained.
- An interrupted run leaves decisions with no outcomes. Those are excluded from analysis by the query below, not repaired.

## What to log, and what not to

Log every decision listed in `autonomy.md` §Tiers — including those that were **asked**, and including manual runs. A log containing only unattended decisions cannot answer "would automating this have been right?", because the comparison case is missing.

A `P0-verify` record carries two extra fields: `"command"`, the approved text **verbatim**, and `"command_source_hash"`, the hash of the repo file that text dereferences when it names one. A later run answers "has this been approved here?" by looking for the newest line with `step_id: "P0-verify"`, `mode: "asked"`, `chosen_index` pointing at the approve option, `command` equal to the resolved string, **and** the hash still matching. Equal, not similar.

The hash is what keeps the approval from being one indirection too shallow. `npm test`, `make test`, `./scripts/verify.sh`, `./gradlew test` are all pointers: the approved *text* never changes while a `git pull` rewrites what it runs. Hash `package.json`, the `Makefile`, or the named script alongside the text, and a changed payload asks again — which is what the user thought they were approving.

Log the hard stops too (`H1-outward`, `H2-destructive`, `H3-tracker`, `H4-security`) and the repo-supplied-command approval (`P0-verify`). They are always `mode: "asked"` and they never score a dial move — but a run that stopped ten times and a run that stopped once must not read the same afterwards.

`skill_version` is `<skill name>@<version from the plugin manifest>`. Installed standalone with no manifest to read, write `<name>@unknown` — an invented number is worse than an honest gap, because it makes two different versions look comparable.

Do not log: file contents, diffs, credentials, or the reviewer's full findings. `rationale` is one line. The log is evidence about *decisions*, and a log that accumulates payloads becomes something nobody wants to keep.

## Scoring a step

Two rates, computed over **different populations**. Getting the populations wrong is what makes this analysis look rigorous while meaning nothing.

```
agreed rate   over decisions with  mode == "asked"           ≥ 0.9
clean rate    over decisions with  an outcome line           ≥ 0.9
              clean = manual_intervention=false ∧ reverted=false ∧ capped=false
                      ∧ claim_met != "unmet"
n (asked)     ≥ 20
```

The last conjunct bites only on `S2-test`, the one step that carries the field. Without it a run of ❓ units — every one of them flagged for manual review in Phase 4 — scores as clean evidence for automating the very decision whose claim went unmet. A repo the check does not run in carries no `claim_met`, and an absent field passes the conjunct — so those decisions **do** score clean on this dimension. That is the honest limit, not a hole to paper over: `report` prints the `not checked` count beside the rates, and a step whose evidence is mostly `not checked` is not the clean run the number suggests.

**`agreed` counts only decisions a human answered.** For anything that ran unattended, `chosen == recommended` by construction — including those inflates the rate toward 1.0 and turns the analysis into "we automated it, so automating it was fine". The whole question is whether the recommendation matches what a human *would have* picked, and only asked decisions carry that evidence.

Both rates, never one. High agreement with poor outcomes means the human and the skill were wrong **together** — the most dangerous pattern the log can surface, and invisible when only agreement is tracked.

`manual_intervention` is the load-bearing field and the easiest to fudge. It is true whenever the user redirected, corrected, or took over after the decision — even slightly, even helpfully. **Only clean, uninterrupted successes are evidence.** Recording an assisted success as unassisted does not make the dial safer to raise; it makes the number that says so meaningless.

## Using the log

The log is read at exactly two moments, and both end with the user deciding.

### 1 · `task-routine report` — the scorecard

Reads the log, prints the table, changes nothing. This is the main use.

```
Dial evidence — 31 runs · 214 decisions · 198 with outcomes
83 of the 214 were asked; the rest ran unattended and carry no agreement evidence.
S2-test claims — 18 met · 3 unmet · 2 unclaimed · 1 not checked

step         asked   agreed   clean   affects
S2-test         22     0.95    0.91   manual → assisted    ✓ supported
S1-design       14     0.86    1.00   manual → assisted    — n too low (need 20)
P2-order        25     0.68    0.79   manual → assisted    ✗ against
S2-review       22     1.00    0.95   assisted → auto      ✓ supported

manual → assisted   1 supported · 1 short of data · 1 against
assisted → auto     1 supported

P2-order was overruled 8 times in 25. That is not an autonomy result — the ordering
recommendation is miscalibrated for this repo. Read the rationale field on the
overruled decisions before touching the dial.
```

The second header line is not decoration either: `asked` counts must be reconcilable with the total, or a reader cannot tell a 25-sample verdict from a 25-run one. Steps with no asked decisions do not appear at all — and their absence is not evidence.

**Hard stops and `P0-verify` never appear as rows.** They are `mode: "asked"` with no recommendation, so `agreed` is `null` by construction and scoring them would compute a rate over an empty population. They belong in the header count and in a line of their own — *"14 hard stops asked: 9 × H4-security, 3 × H1-outward, 2 × H2-destructive"* — because a run that stopped fourteen times and a run that stopped once must not read alike.

The `affects` column exists because the evidence is per step but the dial is global: a step that only runs unattended at `auto` says nothing about `manual → assisted`. Group the steps by the move they bear on, and answer the **move**, not the step.

### 2 · One line in Phase 4, when something newly qualifies

When a step passes both thresholds, say so once, as information:

```
S2-test now has 22 asked decisions at 0.95 agreed / 0.91 clean — `task-routine report` for the rest.
```

Not a pitch, not a prompt, and never an action. A skill that grades its own autonomy and then expands it has no gate at all.

### 3 · Diagnosing the recommendation, which is the more useful read

A low agreed rate is usually **not** a verdict about automation. It says the recommendation logic is wrong for this repo — the change-shape table doesn't match how this codebase is tested, or the ordering heuristic misreads its dependencies. That is actionable immediately, at any dial level, and fixing it helps the `manual` user as much as the `auto` one.

Scope is per project by construction, since the log lives under `<project-slug>`. A step can earn autonomy in one repo and not another, which is exactly what the per-project config file is for.

## What the log cannot tell you

- **Nothing before n.** Under 20 asked decisions, report the count and stop; a 3-for-3 streak is not evidence.
- **Nothing about decisions never offered.** Steps whose recommendation was suppressed never appear, so their absence is not a good record.
- **Nothing about severity.** Every line weighs the same. One reverted commit and one preference disagreement are both a single unclean decision, and the rates cannot see the difference — read the outcomes, not just the ratio.

A step that fails either threshold stays where it is. Report the numbers, not the verdict: the user raises the dial, this analysis only supplies the grounds.

## Never

- ❌ Rewrite or delete a line in the log
- ❌ Copy `recommended_index` out of a document instead of counting the array
- ❌ Log only unattended decisions
- ❌ Report `manual_intervention: false` when the user intervened
- ❌ Raise the dial from this analysis without asking
