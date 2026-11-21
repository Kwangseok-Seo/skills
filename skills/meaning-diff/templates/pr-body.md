<!--
  meaning-diff PR body template. Replace every {{PLACEHOLDER}}, repeat rows, delete these comments.
  GitHub renders tables, ```mermaid fences and <details>. Keep the whole body under 65,536 characters.
  Inside table cells write a literal pipe as \| (also inside `code`), and keep each cell on one line.

  "What changed in meaning" is one ```diff block per function in scope. GitHub colors a diff fence by
  the first character of each line, so the block shows the meaning change without the Files tab:
    `+` green   after-only line (new, or the after side of changed / text only)
    `-` red     before-only line (removed, or the before side of changed / text only)
    `!` orange  ★ row: same text, new meaning. Put it on every line of the row.
    ` ` plain   same
    `#` grey    annotation, not code. Always at column 0, never after `+`/`-` (that colors it as code).
  - Lines follow the after version's order; a removed line sits where it used to be.
  - A row's annotation goes on the line(s) right below the row's last code line:
      #  A4 new — <after sentence>  [T1 T3 strong]
      #  A5 ★ before: <before sentence>
      #       after:  <after sentence>  cause: A4  [T1 strong · T10 pin]
    `changed` takes the before/after pair too. ⚠ and (inferred) go after the tag. Do not pad with
    spaces to align the test ids; CJK width breaks the alignment.
  - Core functions (FORMAT.md) show every line. In a peripheral function, a run of `same` lines with no
    ★ candidate collapses into one annotation line:
      #  A1 same (23 lines) — <what the run does>
    A long body inside one row of a peripheral function may be shortened to `...  <what it does> (N lines)` with that row's prefix.
  - If the code itself contains ```, open the block with ```` instead.
-->
## Summary

{{TWO_OR_THREE_SENTENCES: what the change does, and the one meaning change a reviewer must not miss}}

Scope (`git diff -W {{BASE}}..{{HEAD}}`): {{FUNCTIONS_IN_SCOPE, core ones in bold}}

## What changed in meaning

`+` added · `-` removed · `!` **same text, new meaning (★)** · plain = same · `#` = annotation, not code · `[T…]` = tests and evidence strength · `⚠` = answered below

<!-- one block per function in scope -->
**{{LETTER}}** `{{FUNCTION}}` — {{core — whole method | peripheral — same runs folded}}

```diff
 {{UNCHANGED_LINE}}
#  {{ROW_ID}} same ({{N}} lines) — {{WHAT_THE_RUN_DOES}}
+{{ADDED_LINE}}
#  {{ROW_ID}} new — {{AFTER_SENTENCE}}  [{{T_IDS}} {{STRENGTH}}]
!{{STAR_LINE}}
#  {{ROW_ID}} ★ before: {{BEFORE_SENTENCE}}
#       after:  {{AFTER_SENTENCE}}  cause: {{CAUSE_ROW_IDS}}  [{{T_IDS}} {{STRENGTH}}]
-{{BEFORE_LINE}}
+{{AFTER_LINE}}
#  {{ROW_ID}} changed — before: {{BEFORE_SENTENCE}} · after: {{AFTER_SENTENCE}}  [{{T_IDS}} {{STRENGTH}}]
```

{{IF_ANY_★: one line per ★ row saying why the ordinary diff hides it}}

```mermaid
flowchart TD
  {{AFTER_FLOW}}
  %% outside context: X["DB error → []"]:::warn -.-> C
  classDef new fill:#d6f0de,stroke:#1d6b3a,color:#123d22
  classDef changed fill:#d6f0de,stroke:#1d6b3a,color:#123d22
  classDef star fill:#ffe8b0,stroke:#8a5a00,color:#4a3000
  classDef warn fill:#fbd9c8,stroke:#9c3b12,color:#5a200a,stroke-dasharray:4 3
```

## Context outside the diff

- `{{FILE}}` ({{caller | producer}}): {{WHAT_IT_DECIDES_FOR_WHICH_ROW}}

## Tests

Same tests on the parent (`{{BASE}}`), this branch (`{{HEAD}}`), and one mutant per weakly evidenced row ({{MUTANT_LIST: mutant-1 = row A5, recent[2] → recent[0]; …}}). Stubbed modules: {{STUBS or none}}.

<!-- one mutant column per mutant -->
| Id | Test | Rows | Before | After | mutant-1 |
|---|---|---|:-:|:-:|:-:|
| {{T_ID}} | `{{TEST_NAME}}` | {{ROW_IDS}} | {{FAIL (reason) / PASS}} | {{PASS}} | {{caught / not caught}} |
| **Total** | | | {{BEFORE_TOTAL}} | {{AFTER_TOTAL}} | {{MUTANT_1_TOTAL}} |

{{WHICH_EVIDENCE_IS_WEAK_AND_WHAT_THE_MUTATION_SHOWED}}

## Answered before you ask

- **{{QUESTION}}** {{AUTHOR_ANSWER}}

## Known limits

- {{LIMIT}}

<details><summary>Test code</summary>

```{{LANG}}
{{TEST_CODE}}
```

</details>
