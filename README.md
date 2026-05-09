# skills

> Multilingual Claude Code skills, starting with `dream` — a memory consolidation pass.

A small, opinionated collection of [Claude Code](https://docs.claude.com/en/docs/claude-code) skills published as a single plugin. Each skill ships in two language variants — English and Korean — so the one that matches how you actually talk to your agent triggers cleanly.

[한국어 README](README.ko.md)

## Quickstart

Inside Claude Code, add this repo as a plugin marketplace and install:

```text
/plugin marketplace add Kwangseok-Seo/skills
/plugin install kwangseok-seo-skills@Kwangseok-Seo/skills
```

Or copy the skills manually:

```bash
git clone https://github.com/Kwangseok-Seo/skills.git
cp -r skills/skills/dream     ~/.claude/skills/dream
cp -r skills/skills/dream-ko  ~/.claude/skills/dream-ko
```

## Available skills

| Skill       | Lang | Description                                                 |
|-------------|:----:|-------------------------------------------------------------|
| `dream`     | en   | Memory consolidation pass over `~/.claude/memory/`          |
| `dream-ko`  | ko   | Korean variant of `dream`                                   |

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

## Why ko / en variants?

A skill triggers from its `description` keywords. A single bilingual SKILL.md doubles the prompt cost and confuses the matcher. Two skills with separate descriptions trigger correctly in their own language and stay easy to maintain. The English variant (`dream`) is the **ground truth**; the Korean variant (`dream-ko`) mirrors it. Both must stay in sync — see [docs/adding-a-skill.md](docs/adding-a-skill.md#kken-sync-rules).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/adding-a-skill.md](docs/adding-a-skill.md).

## License

[MIT](LICENSE) © Kwangseok-Seo
