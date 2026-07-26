---
name: session-retro
description: "Session retrospective — first scores whether previously published rules actually got reused, then analyses the session across 4 axes (went well / went wrong / was hard / learned) x 2 lenses (engineering / business), and finally puts promotion candidates in front of a human GATE before publishing anything as a rule, skill, or ADR. Run it before sealing the session. Args: (none) = one full pass; free text = an axis or scope hint. Use when the user says: 'session retro', 'retro', 'retrospective', 'look back at this session', 'what did we learn', 'turn the lessons into a rule'."
---

<what-to-do>

Run one retrospective pass before closing the session. The order is fixed — **reuse scorecard -> 4 axes x 2 lenses -> 🟢 verdict -> human GATE -> publish -> (optional) corpus node.**

Output format follows [RETRO-FORMAT.md](./RETRO-FORMAT.md). A full worked example is in [examples/worked-example.md](./examples/worked-example.md).

**Nothing is published without the human GATE.** That one line is why this skill exists — self-graded auto-approval hardens a false recommendation into an always-loaded rule.

</what-to-do>

<supporting-info>

## When this runs

Before the session ends, while the conversation is still live. Artifacts that come out of the retro (rules, ADRs) are published *inside* the session, so the record of publishing them stays in the transcript.

If you use the bundled `session-seal` skill, run this **before** sealing — the sealed snapshot then carries the evidence for whatever was published.

## Where rules go

This skill publishes always-on guardrails as markdown files in `~/.claude/rules/*.md`, which Claude Code loads as global instructions across projects.

If your setup does not pick that directory up, append the rule to `~/.claude/CLAUDE.md` instead, or use whatever always-loaded location you already keep. Only the destination moves; everything below is unchanged.

## Step 1 — Show the reuse scorecard first

**The first section is not what went right or wrong this session. It is whether the rules published last time actually got used.** Reuse is the point, not publication, and putting the scorecard up front puts the brakes on "let's add one more rule".

Global rules are already in context, so reviewing them costs nothing. Pick the rules that should have applied to this session, and for each:

- **Where and how it was reused**, as a concrete event — never a bare list of rule names
- A verdict: **worked / partly worked / did not work**. If a rule existed and you walked into the very thing it warns about, write that down — that is the signal to fix the rule
- Rules irrelevant to this session do not go on the table at all

**Nothing published yet (first run)?** Say so in one line and go to step 2. Do not manufacture a table.

When a rule keeps not working, its wording is weak or it sits in the wrong place. Consider fixing the existing one before stacking a new one on top.

## Step 2 — 4 axes x 2 lenses

Axes: **what went well / what went wrong / what was hard / what was learned.** Lenses: **engineering / business.**

- Every item is **anchored to an observable event in this session**. "Be more careful next time" is not an item — if you cannot write what you observed and what changed, leave it out.
- **Never leave the mistakes axis empty.** A session with no mistakes means the retro is shallow. Put the agent's own mistakes first.
- The business lens is not about money. It is **users, progress, the shape of the artifact, collaboration friction**. On a learning project, learning efficiency lands here.
- Hard is not wrong. Hard means **where the cost was high**, and it is the candidate for changing tools next time.

## Step 3 — 🟢 verdict

The judgment is **binary**: `🟢 candidate (type: rule|skill|guardrail)` or `unclassified`. No intensity grades (🟡⚪) — a low grade buries an item permanently while creating the illusion it was reviewed.

- **`unclassified` does not mean worthless, it means not triaged yet.** Write a one-line reason (e.g. *already covered by an existing rule*, *the compiler always catches this, low guardrail value*).
- **Always run the duplicate check against global rules.** They are in context: free and accurate. Overlap with other projects' memory or notes is a partial view and risks false negatives, so keep it out of the verdict and check at publish time.
- Do not use frequency as importance. A one-off insight can outrank a repeated annoyance.

Route the artifact with this table:

| If the node is… | Artifact | Format authority |
|---|---|---|
| An always-on behavioural guardrail | **rule** (`~/.claude/rules/*.md`) | [RULE-FORMAT.md](./RULE-FORMAT.md) |
| A repeatable procedure with inputs and outputs | **skill** | your skill-authoring tool (e.g. `skill-creator`) |
| An irreversible, surprising, real trade-off decision | **ADR** (in the repo) | your project's ADR format, else the mini-spec below |
| A fact about reuse, or user feedback | **memory** | the bundled `dream` skill |
| Multi-agent orchestration | **workflow** | only if your harness supports one |
| Already enforced by an existing rule | **nothing** — observe only, unclassified | — |

**ADR mini-spec**, enough to write one when the project has no format of its own:

- First sentence = the decision + why + the cost you accept. If the decision is a rejection, say NO explicitly.
- One paragraph is the default. Add sections only when they earn their place.
- Write one only when all three hold: reversal is expensive AND it is surprising without context AND a real trade-off existed. Obvious, local, reversible decisions are not ADRs.

## Step 4 — Human GATE

Present the 🟢 candidates **in prose** and ask for accept / reject / edit.

- **Do not reduce this to clicking options.** Reading has to be forced, or the gate becomes a rubber stamp. For each candidate make "what was observed, and why is it rule-worthy" visible at a glance.
- State explicitly that rejecting or rewording is a legitimate outcome.
- If the user has **rejected this area before**, say so next to the candidate. A rejected proposal must not return through the side door under a new name.

## Step 5 — Publish

Build only what was accepted. Each artifact follows its format authority — **read it** before writing.

- Rules are **loaded into context every session**. Length is a standing cost, so respect the size discipline in [RULE-FORMAT.md](./RULE-FORMAT.md).
- After publishing, leave one line in project memory: what was published, and what was left unclassified and why. That is the raw material for step 1 next session.

## Step 6 (optional) — Record a corpus node

Only worth doing if you keep a retrospective store that spans sessions. If you do not, stop at step 5.

Nodes are filed under five categories:

| Category | Holds |
|---|---|
| `a-mistakes` | Something that went wrong and could have gone otherwise |
| `b-insights` | Something learned that changes future behaviour |
| `c-improvements` | A process or tooling change worth making |
| `d-deferred` | An agreement postponed, plus the condition for revisiting it |
| `e-recurring` | A pattern that has now shown up across several sessions |

These names are also the category column in [RETRO-FORMAT.md](./RETRO-FORMAT.md)'s verdict table, so keep them even if you skip the corpus itself.

Back-link each published artifact from its node as `✅ published (rule:<file>, date)`. If you also seal sessions, write the node **after** sealing, so the node's sources point at a sealed snapshot rather than a session still in flight.

## Never

- ❌ Publish a rule or skill without the human GATE
- ❌ Put an abstract exhortation with no reproducible evidence on the list
- ❌ Leave the mistakes axis empty
- ❌ Introduce intensity grades (🟡⚪) — keep the verdict binary
- ❌ Copy an existing single authority (your project's ADR format, your corpus node schema) into this skill

</supporting-info>
