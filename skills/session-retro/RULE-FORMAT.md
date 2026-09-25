# Global rule file format

The shape of an always-on guardrail published to `~/.claude/rules/*.md`. **One rule = one file** — the ledger tracks state (loaded · isolated · archived) by file location and revision by file content, so never merge several rules into one file.

**The core constraint: these files are loaded into context every single session.** Length is a standing cost, and a wrong rule is standing contamination. So they must be short, strong, and falsifiable.

## Skeleton

```md
# {title — the guardrail in one line. A dash-subtitle is fine}

## Guardrail

**{One sentence. Imperative. Behaviour must change from reading just this line.}**

## {optional: failure-mode table / decision table / layers}

{If the rule branches by condition, use a table. Columns are usually `mode | check | measurement`.
 One good table can absorb the Why and Do/Don't below — if it does, delete those sections.}

## Why

{Measured evidence. Project, date, observed value. Not "why is this true" but "what did I see that made me decide this".
 Skip it if the table's `measurement` column already carries it.}

## Do / Don't

- ✅ {concrete action}
- ❌ {concrete action}

{Skip it if the table's `check` column already carries the ✅ and the mode names carry the ❌.}

## Scope

{Where it applies, where it does not. Always write the "does not".}

## Related

{The paired rule. Draw the boundary in one line — "that one is X, this one is Y".}

## Source

{The session, and the corpus node if you keep one}
```

## Discipline

### The one-line guardrail

- **Imperative or assertion.** Not "it is good to X" but "do X".
- Reading that line alone must change the next action. If it does not, it is a sentiment, not a rule.
- Do not let the title and the guardrail say the same thing twice — the title is for indexing, the guardrail is for acting.

### Why is measured, not argued

- **Project name + date + observed value.** "Generally this is how it goes" is not evidence.
- Since a later observation may overturn the rule, write it in a **falsifiable** form.
- If a counter-example appeared in the same session, record that too. A rule that records only one side overfits.

### Scope must state where it does not apply

A rule with no exclusion fires everywhere and becomes noise. If you cannot write "this is when I don't use it", it is a preference, not a rule.

### Related states the boundary

When a neighbouring rule exists, say **what is different in one line**. Without a boundary, both get blurry.

> e.g. `verify-your-evidence` vs `evidence-before-decision` — "that one says produce evidence before deciding, this one asks whether that evidence actually proves the claim".

### Amending an existing rule lands in one place

When adding a new measurement to an already-published rule, **do not add to several sections at once.** One insight landing in Why, the table, Do, and Don't multiplies the increment by four.

- **A new mode** → one row in the table (fill `mode | check | measurement` inside that row).
- **A variation on an existing mode** → update that row. Not a new one.
- Do not grow a paragraph in Why. Append only the session name to Source.
- If the rule has no table, add one line to Do/Don't — and once the modes exceed three, fold them into a table.

### Length

- **Target 1.5-3K characters.** Count characters, not bytes: in multibyte scripts a byte count runs roughly 3x higher and will mislead you.
- Over that, split it in two or compress into a table. Narrative, commentary, and publication metadata go first — they are text that does not change behaviour in an always-loaded file.
- Unusually long files are acceptable only when **scope is narrow** (a domain coding convention, say). Firing only inside one stack justifies the standing cost. **Broad scope plus long body is the opposite, and is always a compression target.**

### Filename

- Lowercase kebab-case. **It carries a claim or a command** — `silent-failure-first`, `verify-your-evidence`, `derive-dont-duplicate`.
- Avoid topic-only names (`errors`, `testing`). The filename alone should reveal what it enforces.

## Shapes that have worked

Rather than inventing a new layout, reach for one of these:

- **One failure-mode table replacing everything.** Six ways a thing breaks, folded into `mode | check | measurement`, with Why and Do/Don't deleted because the table already said it.
- **A severity table built from measurements.** Cases ranked by what was observed, so the ordering itself is the argument.
- **A prescription table keyed by condition.** "If the stuck layer is X, do Y" — four rows, no prose.
- **A rule that carries its own counter-example.** The measurement that supports it *and* the case where it did not apply, in the same file, to stop it overfitting.

## After publishing

- If you keep a retrospective corpus, close the corresponding 🟢 node with `✅ published (rule:<filename>, date)` and back-link it.
- Leave one line in project memory recording the publication — the history the next retro checks for past decisions. Reuse itself is counted by the ledger.

## Anti-patterns

- ❌ Unevidenced generalities ("code should be readable")
- ❌ Encoding what a compiler or linter already catches (no guardrail value, only standing cost)
- ❌ Putting a project-specific rule in the global layer (that belongs in the repo's `CLAUDE.md`)
- ❌ No scope exclusion
- ❌ Republishing a proposal the user rejected, under a new name
- ❌ **Stating the same instruction in two grammars** (table `check` cell = Do item = negation of the Don't)
- ❌ **Loading text that does not change behaviour into always-on context** — narrative and publication metadata belong in the retro corpus
