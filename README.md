# skills

> Multilingual Claude Code skills. `dream` for memory consolidation, `session-seal` for resumable session snapshots, `to-html` for gated HTML visualization.

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
cp -r skills/skills/to-html          ~/.claude/skills/to-html
cp -r skills/skills/to-html-ko       ~/.claude/skills/to-html-ko
```

PowerShell (Windows):

```powershell
git clone https://github.com/Kwangseok-Seo/skills.git
Copy-Item -Recurse skills/skills/dream            ~/.claude/skills/dream
Copy-Item -Recurse skills/skills/dream-ko         ~/.claude/skills/dream-ko
Copy-Item -Recurse skills/skills/session-seal     ~/.claude/skills/session-seal
Copy-Item -Recurse skills/skills/session-seal-ko  ~/.claude/skills/session-seal-ko
Copy-Item -Recurse skills/skills/to-html          ~/.claude/skills/to-html
Copy-Item -Recurse skills/skills/to-html-ko       ~/.claude/skills/to-html-ko
```

## Available skills

| Skill              | Lang | Description                                                                       |
|--------------------|:----:|-----------------------------------------------------------------------------------|
| `dream`            | en   | Memory consolidation pass over `~/.claude/memory/`                                |
| `dream-ko`         | ko   | Korean variant of `dream`                                                         |
| `session-seal`     | en   | Seal the current session as `<cwd>/.claude/sessions/<title>.md` with Why/How      |
| `session-seal-ko`  | ko   | Korean variant of `session-seal`                                                  |
| `to-html`          | en   | Gated HTML visualization (Compare / Tune / Learn patterns) with token-cost warning |
| `to-html-ko`       | ko   | Korean variant of `to-html`                                                        |

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

### `to-html` — what it does

`to-html` converts content into a **single self-contained HTML file** — but only when visualization actually adds value. When you run it, the agent:

1. **Resolves input** — takes a file path, the last assistant turn, or pasted text. Asks once if nothing is given.
2. **Classifies + estimates** — fits the content to one of three patterns (**Compare** options in a grid / **Tune** values interactively / **Learn** a concept with diagram+code+caveats), estimates token size, and warns that HTML output is typically ~5× the markdown equivalent (Pascal Filiteri's measurement).
3. **Gates on value** — if value is low or no pattern fits, presents alternatives (markdown summary / ASCII table / Mermaid block / proceed anyway) and **waits for your decision**. Never silently falls back.
4. **Asks once for tool preference** — defaults to Tailwind CDN (+ Mermaid / Chart.js when needed); honors any toolset you name (e.g. inline-only for offline use).
5. **Writes one HTML file** — to `<cwd>/.claude/to-html/YYYY-MM-DD-HHmm-{slug}.html`. CDN-only deps, opens by double-click. **Never auto-opens** the file.

Override the save directory with the `TO_HTML_DIR` environment variable. The framing (three patterns, 5× cost warning) is taken from Anthropic / Tariq Sipha's published guidance — see the skill's "Sources" section.

## Why ko / en variants?

A skill triggers from its `description` keywords. A single bilingual SKILL.md doubles the prompt cost and confuses the matcher. Two skills with separate descriptions trigger correctly in their own language and stay easy to maintain. The English variant (`dream`) is the **ground truth**; the Korean variant (`dream-ko`) mirrors it. Both must stay in sync — see [docs/adding-a-skill.md](docs/adding-a-skill.md#kken-sync-rules).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/adding-a-skill.md](docs/adding-a-skill.md).

## License

[MIT](LICENSE) © Kwangseok-Seo
