# Example — one retro pass on the session that designed v2

An excerpted, condensed real retro. The session redesigned this very skill around a ledger — four adversarial review rounds (R1 · R2a · R2b · R3), 60 `ledger.py` tests, 53 mutations. The ledger already held verdicts from 31 earlier retros (the public skill has no import command — starting from an empty ledger, the baseline line says "no sample" and no probability proposals appear).

The run was recorded in Korean. The Remove output below is what the English `ledger.py` prints on the same ledger state (reconstructed and checked number for number against the recorded Korean output); only the note texts are translated, then cut at 80 characters the way the script cuts them.

**What this example shows**: the working text is raw material and only the two tables reach the user · copying `cards` output without editing it · attaching `stats` evidence to a reinforcement row · surfacing neighbouring past rejections in the caveats · rejection as a legitimate outcome.

> The rule names are ones this user published in earlier retros. Yours will differ — copy the shape, not the names.

---

## Working text (excerpt)

**Verdicts**
- `verify-your-evidence` partly-worked: reproducing red-team claims and 53 mutations worked. But the first answer called a result from ~8 independent samples "a winning streak does not predict anything" — R1 overturned it
- `evidence-before-decision` worked: before answering the "delete it if it works" proposal, ran it against 213 past verdicts and showed 12 counter-examples out of 17 first
- `check-your-guardrails` partly-worked: the v2 spec gave violations and crashes the same exit 1 — R1 and R2b caught it, v3 split it into exit 3
- `derive-dont-duplicate` partly-worked: kept rule state in both an event log and the file location (R2b blocker) — v3 derives it from the files
- `report-guideline` partly-worked: attached a run example, but asked the user to "answer rows 1-4" without saying what each answer does, and got "what does that mean?"
- (five more worked — `silent-failure-first` · `delegation-policy` · `spec-before-first-build` and others)

**4 axes**
- Went wrong (engineering): told the user a conclusion stronger than the sample · designed a double state · violation and crash shared exit 1 · edits silently failed to apply twice
- Went wrong (business): a decision request without per-answer effects cost one round trip
- Went well: disproved the user's proposal on real data · doubted a first all-green run (24/24) and found 5 gaps · cut always-loaded context by 14% (5,834 chars)
- Was hard: each round's fixes opened new holes · retro coverage of sessions is only 23%
- Learned: before putting a number on a table, check it varies between rows of the same kind · when asking for a decision, state what each answer does

**🟢**
- 1 "A number fixed by the trigger condition is not evidence" b-insights → rule reinforcement
- 2 "State per-answer effects in the GATE prompt" c-improvements → skill reinforcement
- 3 Double state a-mistakes → unclassified (covered by `derive-dont-duplicate`)
- 4 Mid-session isolation hole a-mistakes → unclassified (fixed in code, test added)

---

## Retro decisions — 2026-09-25 · projects

### Remove

Baseline: loaded-rule session failures 70/206 (p=0.34)

| # | rule | proposal | evidence | chars |
|---|---|---|---|---|
| 1 | `report-guideline` | fix-or-drop | current rev failed 4/5 · P=0.049 for an average rule · previous rev worked 0/0 | 2252 |

- failure behind 1: §"Stating an unmeasured item as a conclusion" ❌ — walked straight into it. Propo
- failure behind 1: Walked into it. Put a T3 saving of `~900 est. tok` into the proposal; measured 5
- failure behind 1: Attached the first-run table and an isolation-flow example, but asked the user t

4 isolated · no change this session

5 rules with no verdicts yet · 8140 chars total: `git-conventions`, `karpathy-guidelines`, `performance`, `rule-format`, `session-snapshot-rule`

### Add

Add-policy reference (not a per-candidate probability) — share of single-source nodes recorded again within the next 5 retros: 6/94 (0.06, 2026-07-01~ cohort)

| # | target | proposal | evidence | chars |
|---|---|---|---|---|
| 2 | `evidence-before-decision` | reinforce: one ❌ line in Do/Don't — "Do not attach a number whose value the trigger condition fixes. If rows of the same kind always get the same value, it is not information" | In this design, 4 of the 5 card probabilities first proposed were constants — isolate always 0.50, rewrite always 0.20, delete always 0.875 (R1 blocker) · observed once · current rev worked 2/3 · previous rev 15/23 | +128 |
| 3 | `session-retro/RETRO-FORMAT.md` | reinforce (skill): add one line per answer to the GATE prompt saying "what this answer actually does" | The first run showed only the tables and cost a round trip: "what does 'answer rows 1-4' mean?" · observed once · a skill file, not loaded every session | +155 |

Caveats
- 2: a neighbouring rejection exists — "do not test probabilistic calibration on a single sample". That one is about **sample size**; this one is about **a number bound to its trigger condition**, a different area. The rule's existing "❌ putting an unmeasured estimate in as a number" covers whether it was measured; this covers a measured value that is still a constant.
- 3: the same event as row 1's third failure. If row 1 is answered "fix", row 3 could be folded into it.

Answer by number — fix-or-drop takes fix / isolate / reject, other Remove rows take accept / reject, Add rows take accept / reject / edit. Rejecting and rewording are legitimate outcomes.

> Order note: Remove comes **first**. The failure lines end mid-word because the script cuts notes at 80 characters — leave them as printed.

---

## Outcome

The user answered: **"isolate 1, reject 2 and 3"** — the third option for a fix-or-drop row.

1. `ledger.py leaks report-guideline` — two project `CLAUDE.md` files carried the rule's gist. They were left in place, and the gate note says so.
2. `ledger.py gate --proposal isolate --decision accept --note "user GATE: chose isolate on fix-or-drop (failed 4/5, P=0.049)…"` — the file moved to `rules-probation/` and drops out of context from the next session. From now on every retro must give it a verdict (`irrelevant` if the situation never came up).
3. Add rows 2 and 3 rejected — one line each in project memory, not in the ledger. If a later retro raises the same proposal, this rejection shows up in its caveats.

> In the actual run the GATE prompt came with an extra "what each answer does" table. Row 3, which proposed making that table part of the format, was rejected — so the final message above uses the format's prompt sentence.
