# Retrospective output format

The shape of a session retro **as printed into the conversation**. This is not a file you save — it lives in the session transcript, and if you seal the session it is preserved verbatim in the snapshot body.

## Skeleton

```md
## 0. Scorecard: previously published rules

| rule (published) | reuse this session | verdict |
|---|---|---|
| `rule-name` (n sessions ago) | {where and how — a concrete event} | worked / partly worked / did not work |

## 1. What went well
**Engineering** — {2-4 bullets, each anchored to an event}
**Business** — {2-4 bullets}

## 2. What went wrong
**Engineering** / **Business**

## 3. What was hard
{a paragraph each — not faults, but where the cost was high}

## 4. What was learned
{numbered items, written so the next session can act on them}

## 5. 🟢 promotion verdict

| # | node | category | verdict | route |
|---|---|---|---|---|
| 1 | {one line} | b-insights | 🟢 candidate (rule) | `~/.claude/rules/` |
| 4 | {one line} | e-recurring | unclassified | {reason} |

**The GATE is yours.** {ask which to publish — state that rejecting or rewording is fine}
```

## Section discipline

### 0. Reuse scorecard

- **This must be the first section**, ahead of what went right or wrong. The reasoning is in SKILL.md.
- Do not just name the rule — write **where and how**. "Applied" is not a verdict.
- **Do not hide a failure.** If a rule existed and you still walked into the thing it warns about, record that event. When it repeats, fixing the rule's wording or location beats stacking a new rule on top.
- Rules irrelevant to this session do not go on the table — otherwise it becomes an inventory rather than a scorecard.
- If nothing has been published yet, write one line saying so and move on. An empty table is worse than no table.

### 1-3. Went well / went wrong / was hard

- Every bullet anchors to an **observable event in this session**. Quote numbers, output, or error text whenever you can.
- **An empty mistakes axis means a shallow retro.** Put the agent's own mistakes first.
- Hard is not wrong. Hard is **where the cost was high**, and it is the candidate for changing tools next time.
- Lens split: engineering = code, design, measurement. Business = users, progress, artifact shape, collaboration friction (on a learning project, learning efficiency).

### 4. What was learned

- Write sentences **the next session can act on**: not "learned about X" but "when X, do Y".
- These items are the raw material for the step 5 candidates. If a candidate appears that is not in this section, the earlier sections were too thin.

### 5. Verdict table

- The judgment is **binary**: `🟢 candidate (type)` / `unclassified`. No intensity grades.
- **Every unclassified item gets a reason.** An unclassified item without one is buried, not triaged.
- The category column uses the five corpus category names — `a-mistakes` / `b-insights` / `c-improvements` / `d-deferred` / `e-recurring`. They are defined in SKILL.md step 6; use them even if you keep no corpus, because they force you to say *what kind* of thing this is.
- Add **caveats** under the table: past rejections, boundaries against a neighbouring rule, wording to be careful about at publish time.

## Length

The whole thing need not fit one screen, but **if a table degrades into an inventory, the retro failed**. Two to four items per section is the healthy range. Items that keep piling up are a signal the session should have been split.

## Anti-patterns

- ❌ Unverifiable phrasing like "tests passed, went well"
- ❌ "Nothing in particular" on the mistakes axis
- ❌ Putting the reuse scorecard last — there it does not get read
- ❌ Presenting 🟢 candidates as clickable options — reading is not forced, so the gate becomes a rubber stamp
- ❌ Listing code diffs — a retro is not what you did, it is **what you now know**
