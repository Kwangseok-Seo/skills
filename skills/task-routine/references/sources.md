# sources — the task-source adapter

> Read when resolving tasks (Phase 1). Output shapes are in `PHASE-FORMAT.md`; this file is the contract and the two shipped implementations.

## The contract

An adapter answers three things. Everything else in the skill is written against these and nothing else.

| Member | Returns | Used by |
|---|---|---|
| `locality` | `"local"` or `"remote"` | **decides the tier of `S3-done`** — this is not cosmetic |
| `list()` | ordered `[{ id, title, done, ref }]` | Phase 1 |
| `complete(id)` | applied, or deferred | Step 3 |

- `id` — **stable across runs.** The checkpoint, the decision log, and `--resume` all key on it.
- `title` — one line, what the task is.
- `done` — already finished; these are filtered out, not re-run.
- `ref` — what goes in the commit message, or `null`.

### locality drives the tier, and that is the whole asymmetry

```
S3-done, whose tier is data rather than policy:

locality == "local"   marking done is a file edit    → auto-eligible, written through immediately
locality == "remote"  marking done is a tracker write → manual-only, recorded pending, flushed in Phase 4
```

Writing this as a property of the *source* rather than a rule about *GitHub* is what keeps it correct when a third adapter arrives. A new adapter declares its locality and inherits the right behaviour without anyone editing Step 3.

### Stable ids, and what happens when they move

For a file-backed source, **do not use line numbers**: checking off item 2 rewrites the file and every id below it shifts. Derive the id from the item's text (a short slug or hash of the title). When the title is not ASCII, **use the hash**: a slug of a non-Latin title is a string with no visible relationship to the item it names, which is worse than an opaque id that admits as much.

That trades one failure for a smaller one: editing a task's wording changes its id, so the old id disappears and a new one appears. **Report it, never resolve it silently:**

```
Pending id no longer in source: cache-list-responses
Closest match: "Cache list responses with a TTL" (new id: cache-list-responses-with-a-ttl)
Same task, renamed?
```

Silently matching by similarity would mark the wrong task done; silently dropping it would lose a completed task's record. Asking costs one prompt.

## `markdown` — the default adapter

```json
{ "adapter": "markdown", "path": "TODO.md" }
```

- `locality`: `local`
- Tasks are GitHub-flavoured checkboxes at any nesting depth: `- [ ]` open, `- [x]` done.
- Nested items under a task are its detail, not separate tasks. Pass them along in `title` context; do not flatten them into the list.
- `ref`: `null` — a local file has no external reference to cite.
- `complete(id)`: **re-read the file, then** rewrite that one line's `[ ]` to `[x]`. Touch nothing else — reformatting the file turns a one-character change into a diff nobody can review, and writing back the copy `list()` held since Phase 1 deletes whatever the user added to the checklist while the run was going. Those lines were never committed, so nothing can give them back.

```markdown
## Sprint

- [x] Extract the pagination helper
- [ ] Add a sort parameter to the list API
  - accept `sort=field:asc|desc`
  - reject unknown fields with 400
- [ ] Cache list responses
```

→ two open tasks; the two indented lines are detail on the first.

## `github` — issue task lists

```json
{ "adapter": "github", "repo": "owner/name", "issue": 142, "token_env": "GITHUB_TOKEN" }
```

- `locality`: `remote`
- Requires `gh` from the probe. Absent → say so and fall back to asking for a source; **never** silently switch to a local file the user did not name.
- `list()`: read the issue body, parse the same checkbox syntax.
- ids: text-derived, exactly as above — a checkbox inside an issue body has no id of its own, and the issue number identifies the issue, not the item.
- `ref`: `#142` (or `owner/name#142` when the repo differs from the current one).
- `complete(id)`: edit the issue body. This is a tracker write — it is held `pending` and flushed once, in Phase 4, after a single prompt.

Read with `gh issue view <n> --json body,title`. Write with `gh issue edit <n> --body-file -`. Rewrite only the checkbox characters; a body round-tripped through a formatter loses whatever the humans put there.

Measured against a real issue, in exactly those two forms: a body carrying CRLF endings, a trailing-space hard break, a tab-indented line, non-ASCII text, an emoji, an HTML comment, a whitespace-only line and no final newline came back **byte-identical** — 204 bytes out and back, its three CRs intact — with the checkbox character as the only difference. The transport normalises none of it, which is what makes the rule above enforceable: anything a round-trip loses here was lost by the code in between, not by GitHub.

## Adding an adapter

Only these need answering:

1. **What is `locality`?** Get this wrong in the safe direction if unsure — `remote` costs one prompt per run, `local` wrongly declared writes to a tracker unattended.
2. **Where do ids come from, and do they survive an edit?** If the source hands out real ids (an issue key, a row id), use them and stop worrying. If not, derive from text and accept the rename report above.
3. **What is `ref`?** Whatever a reader of `git log` would want in order to find the task again.

Two adapters are specified but not implemented here — `jira` (issue key + checklist) and `url` (a fetched markdown document). Both are straightforward once the three questions are answered; neither ships because neither can be verified against a real instance from a public repository, and an adapter nobody could test is worse than an adapter nobody wrote.
