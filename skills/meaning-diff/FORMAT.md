# Meaning diff format — shared by both modes

`review` and `pr` mode build the same analysis and differ only in how they render it. Everything a reader needs to trust a row lives here: the row, its tag, and what counts as evidence for that tag.

## Row

A row is one line, or a few adjacent lines that read as one sentence (a signature split over lines, an `if`/`else` pair returning mirrored values). Rows follow the **after** version's line order; a removed line sits where it used to be. Every line of the function is covered by some row — including unchanged ones, because an unchanged line is where a meaning change hides.

- **Grouping.** Every line that is not `same`, and every ★ candidate, gets its own row. A run of consecutive `same` lines with no ★ candidate may collapse into one row (`A9 same, 17 lines — builds the order request`).
- **Plain reads go with their consumer.** A line that only reads or assigns a value (`point = float(p['point'])`) takes the tag of the row that uses the value, not a tag of its own, unless the value itself changed.

Each row carries:

| Field | Content |
|---|---|
| id | functions in scope are lettered `A`, `B`, … in the order section 1 lists them; rows — not source lines — are numbered within each function in the after version's order, one id per row even when the row spans several lines (`A3`, `A12`). A removed row takes the id of the row it preceded with a `−` suffix (`A7−`) |
| before code / after code | the exact text, or *(none)* when absent on that side |
| before sentence / after sentence | what the line does **in this function at this point** — not a paraphrase of the syntax. Include when it is reached and where its inputs come from when those changed |
| tag | one of the six below, plus ⚠ when it applies |
| context | optional: a fact from outside the function that the row's meaning depends on (section 4) |
| tests | test ids (`T1`, `T4`) from the test matrix, or the one-line reason no test could run |

## Tags — text × meaning

Two questions per row: *did the text change?* and *did the meaning change?* Meaning includes **when the line is reached** and **what its inputs can be**, not only what it computes.

| | meaning same | meaning changed |
|---|---|---|
| **only in after** | — | `new` |
| **only in before** | — | `removed` |
| **text same** | `same` | `★ same text, new meaning` |
| **text changed** | `text only` | `changed` |

- **Text includes indentation where indentation is syntax** (Python, YAML, Haskell, Makefiles). A line that only moved into or out of a block changed its text — it is `changed` or ★, never `same`.
- `★` is the reason this format exists. A line whose text did not change never appears in an ordinary diff, yet a new guard above it, a new caller, or a changed producer of its input can change when it runs or what it sees. A line is ★ when **some input now produces a different observable effect through it** — a different return value, a call made or skipped, a different value passed on. Look for it on every unchanged line that sits after a new or changed branch, that reads a value whose producer changed, and on **unchanged call sites of a changed function**.
- `⚠ ask` is not a seventh cell. It is added to any row whose correctness depends on something the diff does not settle — a swallowed error that collides with a valid value, a magic number without a stated reason, an ordering that a caller's query decides, two values from separate queries that are assumed to agree. A ⚠ row always produces a question in section 6.

## Evidence — what a tag needs before it is stated as fact

A tag the analysis *infers* and a tag a test *showed* look the same on the page unless you mark them. Run the tests in section 5 and apply:

- **strong** — the before-failure is an assertion, reached through an entry point both versions share
- **weak** — the before-failure only shows the feature is missing (see below); say whether a mutant caught it
- **inferred** — no test ran; the tag carries `(inferred)`

The terminal summary and the page state one of these three for every `new`/`changed`/`★` row.

| Tag | Evidence that confirms it |
|---|---|
| `new`, `changed`, `★` | a test that **fails on before and passes on after** |
| `removed` | a test that **passes on before and fails on after**, or a note that the behavior is unreachable now and why |
| `same`, `text only` | a test that **passes on both** |
| any tag on a non-executable line (comment, docstring, annotation not checked at runtime) | none — write *no behavior* in the tests cell |
| `⚠` | a test that **pins the current after behavior** — it shows what happens, not whether that is right. The author answers that |

- **Test through what both versions share.** A test that calls a new parameter fails on before with `TypeError` / `AttributeError` / `ImportError` — that proves the API is new, not that the behavior is right. Strong evidence comes from a test whose entry point exists **unchanged in both versions** (usually the caller) and whose before failure is an assertion. Prefer that test for every ★.
- **Mutation for weak rows.** For each `new`/`changed`/`★` row whose only before-failure is feature absence, make one mutant: change one token on that row (an index, an operator, a constant) in a copy of after, run all tests, and report which ones catch it. At most 3 mutants; a weak row beyond that stays marked *not covered*. A test that still passes under a row's mutation does not support that row.
- **Mocked boundaries.** When tests replace a producer with a mock that raises or returns directly, they cannot see the arguments sent to it; a mutant on such an argument is caught only by a call assertion. Say so under known limits, and do not count the behavioral tests as evidence for that argument.
- **After must be all-pass first.** If any test fails on after, the harness is wrong (a bad stub, a wrong path) or the test is — fix that before reading the before or mutant columns. A before-failure next to a broken after is not evidence.
- **No run, no ★.** Without a test result, write the tag as `★ (inferred)` / `changed (inferred)`. Never state an inferred tag as confirmed.
- **Cannot run.** If the function needs a database, a broker, wall-clock time, or a network and cannot be isolated with plain stubs, leave its test cells empty and write the reason in one line. Stubbing an *uninstalled module* is fine — list each stubbed module on the page — as long as every symbol the row under test uses keeps its role in the stub (an exception class stays raisable and catchable; a constant keeps its value). A test that stubs away the line under question is not evidence for that line.
- **Tests are review evidence, not a contribution.** They live outside the repository (review mode) or are added only with the author's consent (pr mode). While reviewing, name each test after its row (`test_A5_buy_holds_between_threshold_and_anchor`); if it is committed, rename it after the behavior.

## The six sections

| # | Section | Built by |
|---|---|---|
| 1 | Function scope | `git diff -W` — mechanical, not the model |
| 2 | Line meaning diff | rows as above, one block per function |
| 3 | Path diagram | Mermaid `flowchart` before and after; color only nodes tagged `new` / `changed` / `★`; a dashed node for outside context that feeds a branch |
| 4 | Context outside the diff | callers of the function and producers of values the `new`/`changed`/`★` rows read |
| 5 | Test matrix | one row per test: id, name, row ids, input → expected, before, after, one column per mutant |
| 6 | Questions | review: *ask the author*. pr: *answered before you ask* and *known limits* |
