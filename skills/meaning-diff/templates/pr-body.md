<!--
  meaning-diff PR body template. Replace every {{PLACEHOLDER}}, repeat rows, delete these comments.
  GitHub renders tables, ```mermaid fences and <details>. Keep the whole body under 65,536 characters.
  Inside table cells write a literal pipe as \| (also inside `code`), and keep each cell on one line.
-->
## Summary

{{TWO_OR_THREE_SENTENCES: what the change does, and the one meaning change a reviewer must not miss}}

Scope (`git diff -W {{BASE}}..{{HEAD}}`): {{FUNCTIONS_IN_SCOPE}}

## What changed in meaning

Rows that are not `same`. Tags: `new` · `removed` · `text only` · `changed` · `★ same text, new meaning` · `⚠` = answered below.

| Row | Tag | Before | After | Tests |
|---|---|---|---|---|
| {{ROW_ID}} | {{TAG}} | {{BEFORE_SENTENCE}} | {{AFTER_SENTENCE}} | {{T_IDS}} |

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

<details><summary>All rows</summary>

| Row | Tag | Before code | After code | Before | After |
|---|---|---|---|---|---|
| {{ROW_ID}} | {{TAG}} | `{{BEFORE_CODE}}` | `{{AFTER_CODE}}` | {{BEFORE_SENTENCE}} | {{AFTER_SENTENCE}} |

</details>

<details><summary>Test code</summary>

```{{LANG}}
{{TEST_CODE}}
```

</details>
