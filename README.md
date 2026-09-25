# skills

> Multilingual Claude Code skills. `dream` for memory consolidation, `session-seal` for resumable session snapshots, `session-retro` for gated session retrospectives, `to-html` for gated HTML visualization, `task-routine` for driving a checklist to commits with an autonomy dial.

A small, opinionated collection of [Claude Code](https://docs.claude.com/en/docs/claude-code) skills published as a single plugin. Each skill ships in two language variants — English and Korean — so the one that matches how you actually talk to your agent triggers cleanly.

[한국어 README](README.ko.md)

## Quickstart

Inside Claude Code, add this repo as a plugin marketplace and install:

```text
/plugin marketplace add Kwangseok-Seo/skills
/plugin install kwangseok-seo-skills@Kwangseok-Seo/skills
```

Or copy the skills manually:

bash (macOS / Linux / Git Bash):

```bash
git clone https://github.com/Kwangseok-Seo/skills.git
cp -r skills/skills/dream            ~/.claude/skills/dream
cp -r skills/skills/dream-ko         ~/.claude/skills/dream-ko
cp -r skills/skills/session-seal     ~/.claude/skills/session-seal
cp -r skills/skills/session-seal-ko  ~/.claude/skills/session-seal-ko
cp -r skills/skills/session-retro    ~/.claude/skills/session-retro
cp -r skills/skills/session-retro-ko ~/.claude/skills/session-retro-ko
cp -r skills/skills/to-html          ~/.claude/skills/to-html
cp -r skills/skills/to-html-ko       ~/.claude/skills/to-html-ko
cp -r skills/skills/task-routine     ~/.claude/skills/task-routine
cp -r skills/skills/task-routine-ko  ~/.claude/skills/task-routine-ko
```

PowerShell (Windows):

```powershell
git clone https://github.com/Kwangseok-Seo/skills.git
Copy-Item -Recurse skills/skills/dream            ~/.claude/skills/dream
Copy-Item -Recurse skills/skills/dream-ko         ~/.claude/skills/dream-ko
Copy-Item -Recurse skills/skills/session-seal     ~/.claude/skills/session-seal
Copy-Item -Recurse skills/skills/session-seal-ko  ~/.claude/skills/session-seal-ko
Copy-Item -Recurse skills/skills/session-retro    ~/.claude/skills/session-retro
Copy-Item -Recurse skills/skills/session-retro-ko ~/.claude/skills/session-retro-ko
Copy-Item -Recurse skills/skills/to-html          ~/.claude/skills/to-html
Copy-Item -Recurse skills/skills/to-html-ko       ~/.claude/skills/to-html-ko
Copy-Item -Recurse skills/skills/task-routine     ~/.claude/skills/task-routine
Copy-Item -Recurse skills/skills/task-routine-ko  ~/.claude/skills/task-routine-ko
```

## Available skills

| Skill              | Lang | Description                                                                       |
|--------------------|:----:|-----------------------------------------------------------------------------------|
| `dream`            | en   | Memory consolidation pass over `~/.claude/memory/`                                |
| `dream-ko`         | ko   | Korean variant of `dream`                                                         |
| `session-seal`     | en   | Seal the current session as `<cwd>/.claude/sessions/<title>.md` with Why/How      |
| `session-seal-ko`  | ko   | Korean variant of `session-seal`                                                  |
| `session-retro`    | en   | Gated session retrospective — prunes rules on ledger evidence, publishes lessons  |
| `session-retro-ko` | ko   | Korean variant of `session-retro`                                                 |
| `to-html`          | en   | Gated HTML visualization (Compare / Tune / Learn patterns) with token-cost warning |
| `to-html-ko`       | ko   | Korean variant of `to-html`                                                        |
| `task-routine`     | en   | Drives a task checklist to commits, one at a time, with an autonomy dial           |
| `task-routine-ko`  | ko   | Korean variant of `task-routine`                                                   |

### `dream` — what it does

`dream` is a **manual** reflective pass. When you run it, the agent:

1. **Orients** — reads the existing `MEMORY.md` index and frontmatter of topic files (no full-body reads).
2. **Gathers signal** — looks at the 1–3 most recently modified transcripts for new information worth saving.
3. **Consolidates** — merges new signals into existing topic files, converts relative dates to absolute, deletes refuted facts.
4. **Prunes & indexes** — keeps `MEMORY.md` under 200 lines, removes pointers to stale files.

Three modes:

| Args     | Scope                                                           |
|----------|-----------------------------------------------------------------|
| (none)   | Current project's memory directory                              |
| `user`   | `~/.claude/memory/` (cross-project signals only)                |
| `all`    | `user` pass + every project memory directory, one by one        |

### `session-seal` — what it does

`session-seal` is also **manual**. When you run it (e.g. `/session-seal`, "seal this session"), the agent:

1. **Locates** the active JSONL transcript under `~/.claude/projects/`.
2. **Converts** it to readable markdown via the bundled `convert_transcript.py`.
3. **Scans** the 3 most recent sealed snapshots' frontmatter for chain candidates.
4. **Proposes** Why / How / filename / tags / chain links in a single round, and waits for your confirmation.
5. **Writes** the sealed file to `<cwd>/.claude/sessions/YYYY-MM-DD - {short why}.md`. The body is the raw conversation, kept verbatim.

Why / How are the two-line abstraction that lets a future session resume in seconds — `Why` is the session's intent, `How` is the approach. `continues-why` and `continues-how` are optional wikilinks back to the previous sealed snapshot whose intent / approach this session continues.

To put snapshots elsewhere (e.g. a personal wiki), set `SESSION_SEAL_DIR` in your environment. Auto-recall on session start is intentionally not bundled — see the skill's "Customization" section if you want it.

### `session-retro` — what it does

`session-retro` is a **manual** pass you run before closing a session — and, if you also seal sessions, before `/session-seal`. Rules cost context every session, so it decides what to *remove* as carefully as what to add. When you run it, the agent:

1. **Records a verdict per rule** — worked / partly-worked / did-not-work, each with the concrete event, for the rules that bore on the session, plus every isolated rule. The bundled `ledger.py` appends them to a CSV ledger at `~/.claude/session-retro/`.
2. **Analyses 4 axes × 2 lenses** and **judges binary** — went well / went wrong / was hard / was learned, each anchored to an observable event (the mistakes axis is never empty); each node is either a 🟢 candidate or `unclassified` with a stated reason. This is working text you need not read.
3. **Shows you two tables, Remove first** — Remove rows come from `ledger.py cards`, never from the agent's own estimates: *isolate* a rule that keeps working (move it out of context and see if the behaviour holds without it), *fix-or-drop* one that keeps failing, *restore* an isolated rule that failed, *archive* one that held up, *rarely-relevant* for one retros never touch. Isolate and fix-or-drop rows carry a probability counted from the ledger against the average rule. Then Add: new rules and reinforcements.
4. **Stops at a human GATE** — you answer by row number; rejecting or rewording is an explicitly valid outcome, and rejections are recorded so the same proposal does not come back every retro.
5. **Executes only what you accepted** — moves rule files between `~/.claude/rules/`, `rules-probation/` and `rules-archive/` (location is state), and publishes rules following the bundled `RULE-FORMAT.md` (target 1.5–3K characters).

The skill bundles `RETRO-FORMAT.md` (output shape), `RULE-FORMAT.md` (rule file shape), `ledger.py` with its tests (Python 3.8+), and `examples/worked-example.md` (a real retro, end to end). It assumes one rule per file under `~/.claude/rules/`. With an empty ledger there is no baseline yet, so no probability proposals appear until verdicts accumulate. The Korean variant keeps its own ledger at `~/.claude/session-retro-ko/`, since verdicts are stored in each variant's language. Optional: `SESSION_RETRO_DIR` moves the ledger, `SESSION_SEAL_DIR` adds sealed-session counts, `SESSION_RETRO_CORPUS` points at a cross-session retrospective corpus (step 8, skipped by default).

### `to-html` — what it does

`to-html` converts content into a **single self-contained HTML file** — but only when visualization actually adds value. When you run it, the agent:

1. **Resolves input** — takes a file path, the last assistant turn, or pasted text. Asks once if nothing is given.
2. **Classifies + estimates** — fits the content to one of three patterns (**Compare** options in a grid / **Tune** values interactively / **Learn** a concept with diagram+code+caveats), estimates token size, and warns that HTML output is typically ~5× the markdown equivalent (Pascal Filiteri's measurement).
3. **Gates on value** — if value is low or no pattern fits, presents alternatives (markdown summary / ASCII table / Mermaid block / proceed anyway) and **waits for your decision**. Never silently falls back.
4. **Asks once for tool preference** — defaults to Tailwind CDN (+ Mermaid / Chart.js when needed); honors any toolset you name (e.g. inline-only for offline use).
5. **Writes one HTML file** — to `<cwd>/.claude/to-html/YYYY-MM-DD-HHmm-{slug}.html`. CDN-only deps, opens by double-click. **Never auto-opens** the file.

Override the save directory with the `TO_HTML_DIR` environment variable. The framing (three patterns, 5× cost warning) is taken from Anthropic / Tariq Sipha's published guidance — see the skill's "Sources" section.

### `task-routine` — what it does

`task-routine` takes a checklist and drives each item to a commit through **a design loop → a build loop → a commit**. On first run it asks four questions and writes a config; after that:

1. **Probes** what is actually installed — CLIs, skills, agents, plugins — every run, because a stored capability list goes stale the moment you install or remove something.
2. **Resolves** tasks through a pluggable source adapter: a local markdown checklist, or a GitHub issue. The adapter's `locality` (`local` / `remote`) is what decides whether marking a task done is a file edit or a tracker write.
3. **Designs with a review loop** — an *independent* reviewer (a different vendor's CLI, else a different model, else a fresh context) that receives the plan and never the design conversation. A reviewer handed the designer's argument returns agreement, not review.
4. **Builds in one loop** — implement → verify → review, sharing one budget of 3, with review running only after a passing verify. Cleanup appears at the exit, and only when the loop ran more than once.
5. **Commits, and stops there.** No push, no PR, no merge, no retrospective.

The distinguishing feature is the **autonomy dial**: `manual` / `assisted` (default) / `auto`, where a decision runs unattended only when *the level allows it* **and** *its risk tier is auto-eligible*. Four classes are asked about at every level including `auto` — anything outward-facing, destructive local work, tracker writes, and any of five security signals — and **a check that cannot run counts as a stop, never as a pass.**

Every recommendation, choice, and outcome is appended to a decision log as its own line (never edited in place). `task-routine report` turns that log into a scorecard per decision point, and the agreement rate is computed only over decisions a *human* answered — including unattended ones would make the analysis prove that automating was fine because it was automated. Raising the dial is always the user's move.

Override the state directory with `TASK_ROUTINE_DIR`. State lives outside the repo on purpose, so an unattended run cannot commit its own log.

## Why ko / en variants?

A skill triggers from its `description` keywords. A single bilingual SKILL.md doubles the prompt cost and confuses the matcher. Two skills with separate descriptions trigger correctly in their own language and stay easy to maintain. The English variant (`dream`) is the **ground truth**; the Korean variant (`dream-ko`) mirrors it. Both must stay in sync — see [docs/adding-a-skill.md](docs/adding-a-skill.md#kken-sync-rules).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/adding-a-skill.md](docs/adding-a-skill.md).

## License

[MIT](LICENSE) © Kwangseok-Seo
