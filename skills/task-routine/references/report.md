# report — reading the decision log

> Read **only** on the `report` argument, which prints this and exits. A run that drives tasks writes the log (`telemetry.md`) but never scores it — the one exception is Phase 4's single qualifying line, whose thresholds stay in `telemetry.md` §Scoring a step. Both readings end with the user deciding; nothing here is an action.

## `task-routine report` — the scorecard

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

## Diagnosing the recommendation, which is the more useful read

A low agreed rate is usually **not** a verdict about automation. It says the recommendation logic is wrong for this repo — the change-shape table doesn't match how this codebase is tested, or the ordering heuristic misreads its dependencies. That is actionable immediately, at any dial level, and fixing it helps the `manual` user as much as the `auto` one.

Scope is per project by construction, since the log lives under `<project-slug>`. A step can earn autonomy in one repo and not another, which is exactly what the per-project config file is for.

## What the log cannot tell you

- **Nothing before n.** Under 20 asked decisions, report the count and stop; a 3-for-3 streak is not evidence.
- **Nothing about decisions never offered.** Steps whose recommendation was suppressed never appear, so their absence is not a good record.
- **Nothing about severity.** Every line weighs the same. One reverted commit and one preference disagreement are both a single unclean decision, and the rates cannot see the difference — read the outcomes, not just the ratio.

A step that fails either threshold stays where it is. Report the numbers, not the verdict: the user raises the dial, this analysis only supplies the grounds.

