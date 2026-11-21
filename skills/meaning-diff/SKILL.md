---
name: meaning-diff
description: "Line-by-line meaning diff of a code change: walks every line of each changed function, writes what it does before and after, and flags lines whose text did not change but whose meaning did (★) — the lines an ordinary diff never shows. Backs each flag with tests run on the before code, the after code, and a mutation. Two modes: `review` (default — for a reviewer reading someone else's commit or PR; writes a self-contained HTML review page) and `pr` (for the author; writes a GitHub PR body in Markdown). Use when the user says: 'meaning diff', 'review this commit line by line', 'what changed in meaning', 'semantic review of this PR', 'write the PR body', 'PR description with meaning diff'."
---

# Meaning diff — review the meaning of every line, not only the changed ones

A reviewer reads a change one line at a time inside the method, but a diff shows only the lines whose text changed. A line that kept its text while a new guard above it changed **when it runs** is invisible — and that is often where the bug is.

This skill rebuilds each changed function as a table of rows, one sentence per line for before and for after, tags each row, and proves the tags with tests run on both versions. The shared format — rows, tags, evidence rules — is in [FORMAT.md](FORMAT.md). Read it before step 2.

## Arguments

| Args | Mode | Target |
|---|---|---|
| `[review] <target>` | review (default) | a commit (`61d683d`), a range (`main..feature`), a branch, or a PR number (`#123`, needs `gh`) |
| `pr [<base>]` | pr | the current branch against `<base>` (default: the repo's default branch) |
| `pr <base>..<branch>` | pr | a branch that is not checked out |
| (none) | review | `HEAD` |

Free text after the target narrows scope: `review #123 only is_close_all`.

## Procedure

### 0. Resolve base and head

- commit `X` → base `X^`, head `X`
- range `A..B` → base `merge-base A B`, head `B`
- PR `#N` → `gh pr view N --json baseRefOid,headRefOid`, then `git fetch origin <both>` if missing
- `pr` mode → base `merge-base <base> HEAD`, head `HEAD` (or `<branch>` when given). If the working tree has uncommitted changes, say so and analyze the commits only

Print the resolved `base..head` and the changed files before going further.

### 1. Function scope (mechanical)

```bash
git diff -W <base> <head> -- <files>        # add -w only where indentation is not syntax
```

`-W` extends each hunk to the whole enclosing function — as git sees it. Without a diff driver git takes any unindented line as a function header, so in Python a method's hunk grows to its whole class. If the repo's `.gitattributes` sets no driver for the language, pass one for this command only: write `*.py diff=python` (git also ships `java`, `cpp`, `csharp`, `golang`, `rust`, `ruby`, `php`, `kotlin`, …) to a temp file and run `git -c core.attributesFile=<that file> diff -W …`. `-w` drops whitespace-only changes, which removes noise in C-like languages but **hides real changes** where indentation is syntax (Python, YAML, Haskell, Makefiles): a line moved from an `elif` into a nested `if` would show as unchanged. List the functions that appear, lettered `A`, `B`, … — these letters prefix the row ids. Include unchanged call sites of a changed function when the caller's behavior can differ; they are where ★ most often hides. Skip files that are not code (lock files, generated files, docs) and say which.

If more than **5** functions changed, list them all with a one-line summary and cover the ones whose control flow or return values changed; name the skipped ones and why. The user can ask for any of them afterwards.

### 2. Line meaning diff

For each function in scope, read the **whole** before and after versions (`git show <base>:<path>`, `git show <head>:<path>`), not only the hunk, and build rows per FORMAT.md. Every line of the function is covered by a row; only runs of plain `same` lines may be grouped. The ★ search is the core work: for every unchanged line, ask whether it now runs under different conditions or sees different inputs.

### 3. Path diagram

One Mermaid `flowchart TD` for before and one for after per function whose control flow changed. Nodes are branches and returns, labeled with their row ids. Color with the template's `classDef`s: `new`/`changed` green, `star` amber, `warn` for outside context — a dashed node with a dotted edge (`X -.-> C`) into the branch it feeds.

### 4. Context outside the diff

For each function in scope:

- **Callers** — search the repo for its name; show how each caller builds the arguments that the `new`/`changed`/`★` rows read.
- **Producers** — for each such argument, open the function that produces it. Look hardest at **failure paths that return a value a success could also return** (`[]`, `None`, `0`, `-1`, `""`): the caller cannot tell "nothing found" from "lookup failed", and a guard built on that value switches off silently. Mark such a row ⚠.

Keep each excerpt to the lines that matter and highlight the deciding token.

### 5. Tests — before, after, mutation

Write tests that each point at rows (FORMAT.md, Evidence), numbered `T1`, `T2`, …. For every ★, include a test that enters through code both versions share — usually the caller — so the before-failure is an assertion rather than a missing parameter. Then run the **same** test file against each version, never touching the user's working tree:

```bash
git worktree add --detach <tmp>/before   <base>
git worktree add --detach <tmp>/after    <head>
git worktree add --detach <tmp>/mutant-1 <head>   # edit one token on a weak row; up to 3 mutants
```

- Keep the test file **outside** the worktrees and point the runner at each one. If it imports the project's own test helpers (`from tests.helpers import …`), copy it into each worktree's test package for the run and delete it right after, so the worktree is clean again. For Python: `cd <worktree> && PYTHONPATH=<worktree> PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider <abs-path-to-testfile>` (PowerShell: set `$env:PYTHONPATH` and `$env:PYTHONDONTWRITEBYTECODE` first). The two cache switches keep the worktrees free of untracked files so they can be removed without force. Use the project's own runner and dependencies.
- If a dependency is not installed, stub the module per FORMAT.md (symbols the tested rows use keep their role) and list the stubs on the page. To call a method whose class has a heavy constructor, build the object with `Cls.__new__(Cls)` and set only the attributes the method reads. **Run after first: it must be all-pass** before the before and mutant columns mean anything.
- **Check each mutant before running it:** `git -C <mutant> diff --stat` must show exactly the one line you meant to change. A mutation that matched twice or not at all leaves a copy of after, and every test then reads as *not caught* — a false result, not a weak one.
- Record pass/fail per test per column, and for each failure the one-line reason (`TypeError`, assertion).
- Clean up without `--force`: revert each mutant (`git -C <path> checkout -- .`), then `git worktree remove <path>` for every worktree, then `git worktree prune` and `git worktree list` to confirm. If a removal is refused, show `git -C <path> status` to the user instead of forcing it. Never link (symlink, junction) a worktree to anything outside it — a forced removal follows links and deletes their targets.

If the function cannot be run in isolation, skip this step for it, leave the cells empty, and keep the inferred tags marked `(inferred)`.

### 6. Questions

Each ⚠ row becomes one question: the question in one line, then what happens now (from its pinning test) and why it might be wrong.

## Output — review mode

One self-contained HTML file built from [templates/review.html](templates/review.html): header, legend, the six sections in order, the test code in a `<details>`. Write it to `<repo>/.claude/meaning-diff/<short-sha>-review.html` (for a PR: `pr-<N>-review.html`). If `.claude/` is not ignored by git in that repo, say so, since the file will appear as untracked.

If the host offers a tool that publishes HTML pages (for example Claude's Artifact tool), offer to publish it there too; otherwise give the file path. Do not open it automatically.

Close with a short terminal summary: the ★ rows with their evidence strength, the ⚠ questions, and the test totals per column (`before 6F/4P · after 10P · mutant-1 2F/8P`).

## Output — pr mode

One Markdown file from [templates/pr-body.md](templates/pr-body.md), written to `<repo>/.claude/meaning-diff/<branch>-pr.md` (with `/` in the branch name replaced by `-`) and printed. The reader is a reviewer skimming a PR page, so:

- The summary table lists only rows that are **not** `same`. The full row table goes in a `<details>`.
- Section 6 becomes **Answered before you ask** (the ⚠ questions with the author's answer — ask the user for each answer; leave `TODO(author)` only if they decline) and **Known limits**.
- GitHub renders ```` ```mermaid ```` blocks, tables, and `<details>`; nothing else from the HTML page carries over. The PR body limit is 65,536 characters — if over, move the full row table and test code out and say so.

Then offer, separately and only on an explicit yes:

1. **Post it** — `gh pr edit <N> --body-file <file>` for an existing PR, or `gh pr create --body-file <file>`. This publishes the text; do not run it without a yes.
2. **Commit the tests** — move them into the repo's test directory, renamed after the behavior instead of the row id.

## Rules

- **The before column is evidence only when it ran.** Never fill a before/after/mutant cell from reasoning.
- **Do not modify the analyzed repository** except the output file and what the user says yes to in the pr-mode offers — no other commits, no stashes, no checkouts in the user's working tree. Worktrees go under a temporary directory.
- **Questions are for the author, not verdicts.** A ⚠ test pins what happens; it does not say the behavior is wrong.
- **Scale the depth to the change.** A rename-only change gets a short page saying so: every row `text only`, tests on both sides, no ★.
