# Example — a two-milestone session retro

One real retro pass, de-identified. The project: a small CLI tool, built in a language the developer was learning at the same time. Two milestones closed in a single session — auth/config, then manifest validation.

**What this example demonstrates**: putting the scorecard first, not hiding a "tripped anyway" verdict, giving every unclassified item a reason, and surfacing a past rejection at the GATE. Outcome: all three 🟢 candidates published.

> The rule names in section 0 are ones *this* project had published in earlier retros. Yours will be different — what to copy is the shape of the verdicts, not the names.

---

## 0. Scorecard: previously published rules

| rule (published) | reuse this session | verdict |
|---|---|---|
| `evidence-before-decision` (3 sessions ago) | Measured the upstream API's three auth states before asking about auth policy · opened this session by inventorying 9 kinds of broken manifest instead of guessing · settled 3 local, reversible questions alone and reported them | **Worked strongly.** The first action this session was "only two problems are known, the rest is guesswork, so measure first" — that would not have happened without this rule |
| `verify-your-evidence` (2 sessions ago) | Checked the public API intended as a test target and found it returning 503, then swapped it · verified 3 claims with a demo before writing them down · re-measured a case that had nearly passed as "exit 0" with stdout discarded | **Worked, but tripped once** — a probe script broke on a YAML syntax error and its garbled output was presented once as "the measurement". Exactly the third failure mode this rule names: the harness itself is wrong |
| `adr-rationale-realization` (3 sessions ago) | Checked the 3 properties the ADR claimed against actual run output, and said so in the report | Worked |
| memory `milestone-adr-gate-check` | Both milestones published their ADR **inside** the milestone; the rejected candidates were recorded with reasons | The retroactive-documentation failure from 2 sessions ago did not repeat |

> Placement note: this table is the **first section**. Pushed further down, it does not get read.
> Verdict note: `verify-your-evidence` tripping once was not hidden — that is the only signal for deciding whether the rule's wording needs work.

## 1. What went well

**Engineering**

- **Taking inventory changed the design.** Starting from guesswork would have caught only the 2 known issues. Measuring surfaced something more dangerous than a crash: *a name collision between manifests prints help text to stdout and exits 0*.
- **Reserved words were not hard-coded — the CLI was asked instead.** Side effect: collisions between manifests were caught by the same check, with no extra code.
- **A circular import was read as a design signal, not an obstacle to route around.** Where the compiler stopped us was the module boundary.

**Business**

- The user proposed "validation first", outside the roadmap, and it was accepted immediately — backlog pressure was the real signal, the roadmap was not.
- When the user switched to "just write it, I'll read the code to understand", the mode switched with them on the spot.

## 2. What went wrong

**Engineering**

- **Failed to clean up imports — third session running.** Removed code without removing its imports and broke the build. The compiler always catches it, so the cost is one round trip, but three in a row is a habit problem.
- **The probe script itself was wrong.** The evidence got built, and the evidence did not get verified.

**Business**

- **Misjudged the Socratic intensity — "I don't follow" came back twice.** What was actually stuck was placement, not the concept, and the same layer got explained twice.
- **Asked for 7 repetitions of one pattern to be hand-written.** The learning value was concentrated in the first two or three.

## 3. What was hard

The framework's lazy initialisation made the winner of a name collision vary case by case, so nothing could be predicted without measuring it. Separately, an external public API reset its data mid-session and the measurement table had to be rebuilt from scratch.

## 4. What was learned

1. **The most dangerous failure is not the loud one, it is the one that exits 0.**
2. **Derived logic should reference the same source and the same operation as the real thing.**
3. **A compiler error caught a logic bug** — had the unused-variable warning been silenced, the bug would have survived.
4. **Identify what kind of stuck it is before explaining again** — re-explaining the same layer fails the second time too.
5. **An execution trace beats an explanation** — one table of state changes did more than two rounds of prose.

## 5. 🟢 promotion verdict

| # | node | category | verdict | route |
|---|---|---|---|---|
| 1 | A silent failure (`exit 0`) is more dangerous than a loud one (a crash) | b-insights | **🟢 candidate (rule)** | `~/.claude/rules/` |
| 2 | Derived logic references the same source and operation as the real thing | b-insights | **🟢 candidate (rule)** | `~/.claude/rules/` |
| 3 | Identify the kind of stuck (concept vs placement) and switch explanation layers | c-improvements | **🟢 candidate (rule)** | `~/.claude/rules/` |
| 4 | Import cleanup missed 3 sessions running, breaking the build | e-recurring | **unclassified** | The compiler always catches it — low guardrail value, observe only |
| 5 | External public APIs change even mid-session | a-mistakes | **unclassified** | Already covered by `verify-your-evidence` |

**Caveat** — a previously deferred agreement says *"a learning-cycle skill is not triggered by friction merely recurring"*. Candidate 3 is a different artifact from that skill (an always-on guardrail, not a procedure), so it goes up as a candidate — but the overlap is stated openly. What is different this time is that the friction was not **recurring**; a way to resolve it was **found**.

**The GATE is yours.** Which of 1, 2, 3 should be published? (All / some / none — rejecting or rewording is equally fine.)

---

## Outcome

User accepted: **all of them.** Published as `silent-failure-first.md`, `derive-dont-duplicate.md`, `diagnose-the-stuck-layer.md`.

The 2 unclassified items were kept as observations with their reasons. One line went into project memory recording what was published — raw material for the next retro's section 0.

> Candidate 3's rule body got this in its `Scope` section: *"this is an always-on guardrail, not a learning-cycle procedure — turning it into a procedure happens only when the user asks directly."* That sentence is the device that stops a rejected proposal from re-entering through the side door under a new name.
