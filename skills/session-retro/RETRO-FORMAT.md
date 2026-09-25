# Retrospective output format

The shape of a retro **as printed into the conversation**. Verdicts are recorded in the ledger (the CSV `ledger.py` writes); analysis and decisions stay in the transcript, and if you seal the session they are preserved in the snapshot body.

The output has two parts — **working text** (steps 1-4, raw material the user need not read) and the **final message** (the two tables the user decides on).

## Working text (steps 1-4)

One line per item, two to four items per axis. Items that keep piling up are a signal the session should have been split.

```md
**Verdicts** — `{rule}` partly-worked: {event — what was done and where it slipped} · `{isolated rule}` (isolated) irrelevant: {the situation that calls for it never came up}
**4 axes** — went wrong (engineering): … · went well (business): … · was hard: … · learned: when X, do Y
**🟢** — 1 {one line} b-insights → rule · 2 {one line} a-mistakes → unclassified (covered by `{rule}`)
**rarely-relevant filtered** — `{rule}`: scope covers almost every implementation session → gate rarely-relevant:reject
```

- Categories are the five names — `a-mistakes` / `b-insights` / `c-improvements` / `d-deferred` / `e-recurring`. Defined in SKILL.md step 8.
- Every unclassified item gets a reason. An unclassified item without one is buried, not triaged.

## Final message

```md
## Retro decisions — {date} · {project}

### Remove
{ledger.py cards output verbatim — baseline line · table · failure lines · "isolated" line · "no verdicts yet" line. Only the filtered rarely-relevant rows drop out}

### Add
{the policy reference line from the end of the cards output}

| # | target | proposal | evidence | chars |
|---|---|---|---|---|
| 4 | `{rule}` | reinforce — update a table row | {event in one line} · current rev worked 1/3 · previous rev 15/28 | +180 |
| 5 | new `{filename}` | rule | {event in one line} · observed once | 1,900 |

Caveats — 5: {past rejections / boundary against a neighbouring rule / wording to be careful with at publish time}

Answer by number — fix-or-drop takes fix / isolate / reject, other Remove rows take accept / reject, Add rows take accept / reject / edit. Rejecting and rewording are legitimate outcomes.
```

## Discipline

### Remove

- Copy the `ledger.py cards` output **without editing it**. Do not rewrite or round any number.
- The only edit: dropping `rarely-relevant` rows whose rule has a broad `Scope` (reason in the working text, record via gate).
- With nothing to remove, keep the script's `None (read N ledger rows · M retros)` line as is — it tells an empty result from a run that never happened.
- Read P together with the window length. Do not turn a difference over a three-session window into a causal claim such as "the reinforcement did not help".

### Add

- Row numbers continue from the Remove table.
- A reinforcement row puts `ledger.py stats`' `current rev · previous rev` in the evidence column — the numbers that show whether the previous reinforcement raised the success rate.
- **chars column**: draft length for a new rule, the increment for a reinforcement. Measure with Python `len()` — characters, not bytes (in multibyte scripts a byte count runs roughly 3x higher).
- "observed k times" in the evidence column is the node's number of sources in your corpus (once, this session, if you keep no corpus) — state it as a fact and **never use it to sort or grade**.
- With no 🟢, write `None — {one-line reason}`.

## Anti-patterns

- ❌ Pasting the whole analysis into the final message — everything but the two tables lives in the working text
- ❌ A probability the script did not produce, like "promotion probability 0.7"
- ❌ Putting the Remove table after the Add table (see what to cut first)
- ❌ "Nothing in particular" on the mistakes axis
- ❌ Unverifiable evidence like "tests passed, went well"
- ❌ Presenting 🟢 candidates as option buttons (reading is not forced, so the gate becomes a rubber stamp)
- ❌ Listing code diffs — a retro is not what you did, it is **what you now know**
