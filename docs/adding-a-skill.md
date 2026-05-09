# Adding a skill

This is the long form of [CONTRIBUTING.md](../CONTRIBUTING.md). It covers the conventions this repo follows on top of the official [Claude Code plugin spec](https://code.claude.com/docs/en/plugins-reference).

## Layout

```
skills/
├── <name>/
│   └── SKILL.md          # English (ground truth)
└── <name>-ko/
    └── SKILL.md          # Korean mirror
```

Both directories must be listed in `.claude-plugin/plugin.json` under `"skills"`. The `name` field inside each `SKILL.md` frontmatter must match the directory name.

Auxiliary files (helper scripts, references) are allowed inside the skill directory and are picked up automatically when the plugin is installed.

## SKILL.md frontmatter

```yaml
---
name: <directory-name>          # required, matches directory
description: "<one-line, with concrete trigger keywords>"
---
```

### Writing a good `description`

The `description` is what the agent uses to decide whether to invoke this skill. Two hard rules:

1. **Be specific about *what the skill does***, not just the topic. "For memory work" is too vague; "Reflective consolidation pass over `~/.claude/memory/` — merges new signals into topic files, prunes contradictions, tightens the MEMORY.md index" tells the agent exactly when to fire.
2. **Include the exact phrases users will type.** End the description with something like: "Use when the user says: 'X', 'Y', 'Z'." For Korean variants, include the Korean phrases verbatim.

### Good vs bad

| | Good | Bad |
|--|------|-----|
| What | "Memory consolidation pass over `~/.claude/memory/`" | "Helps with memory" |
| Trigger | "Use when user says: 'clean up memory', 'consolidate memory', 'dream'" | (no trigger phrases) |
| Args | Document any args explicitly: "(none) = current project; `user` = user-scope; `all` = both" | Args left undocumented |

## Standalone rule

Skills published here must not depend on the contributor's personalized environment:

- **No hard-coded absolute paths** like `C:\Users\<name>\...` or `/home/<name>/...`. Use `~/.claude/...` instead.
- **No references to personalized system prompts.** If your skill needs a memory schema, embed the schema in the body of `SKILL.md` itself.
- **OS-neutral examples.** When showing shell commands, give both bash and PowerShell variants when they meaningfully differ.

## ko/en sync rules

The English variant (`<name>`) is the **ground truth**. The Korean variant (`<name>-ko`) must be a semantic mirror.

When updating a skill:

1. Edit the English version first.
2. Translate the change into the Korean version in the **same PR**.
3. Verify the trigger keywords in the Korean `description` are natural Korean — don't word-for-word translate English triggers.

The Korean variant's `description` should include common Korean phrasings of the user's intent (e.g. "메모리 정리해줘", "메모리 통합", "인덱스 정돈"), even when the English variant only lists English phrasings.

## Plugin manifest update

Every new skill needs an explicit entry in `.claude-plugin/plugin.json`:

```json
{
  "skills": [
    "./skills/dream",
    "./skills/dream-ko",
    "./skills/<your-new-skill>",
    "./skills/<your-new-skill>-ko"
  ]
}
```

Validate the JSON before committing:

```bash
python -m json.tool < .claude-plugin/plugin.json > /dev/null && echo OK
```

## Testing locally

Before opening a PR, install the plugin from your local clone and verify both variants trigger:

1. In Claude Code, run `/plugin install <local-path>` (or use a local marketplace).
2. Type an English prompt that should trigger your skill — confirm `<name>` fires (not `<name>-ko`).
3. Type a Korean prompt — confirm `<name>-ko` fires.
4. Run the skill end-to-end at least once and confirm it works on a fresh `~/.claude/memory/` (or whatever filesystem state it expects).

If both variants fire on the same prompt, the descriptions are too overlapping — tighten the language-specific keywords.
