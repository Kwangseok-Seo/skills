# Contributing

Thanks for the interest. This repo is small and opinionated — most contributions are skill additions or improvements to existing ones.

## Quick reference

- **Skills live in**: `skills/<name>/SKILL.md` (flat layout for now; categories may come later).
- **Languages**: every skill ships in two variants — `<name>` (English, ground truth) and `<name>-ko` (Korean mirror).
- **Plugin manifest**: `.claude-plugin/plugin.json` lists every skill explicitly under `skills`.
- **License**: MIT. By contributing, you agree your work is released under the same license.

## Adding a new skill

1. Read [docs/adding-a-skill.md](docs/adding-a-skill.md) for the full spec.
2. Create `skills/<name>/SKILL.md` (English) and `skills/<name>-ko/SKILL.md` (Korean).
3. Add both paths to `.claude-plugin/plugin.json` under `skills`.
4. Add a row to the **Available skills** table in both `README.md` and `README.ko.md`.
5. Open a PR.

## PR checklist

- [ ] `SKILL.md` frontmatter has `name` and `description` fields.
- [ ] `description` includes concrete trigger phrases (good: "consolidate memory, dream, clean up memory"; bad: "for memory work").
- [ ] No hard-coded user-specific paths (`C:\Users\<...>`, `/home/<...>`); use `~/...` instead.
- [ ] No dependency on personalized system prompts. The skill must work for any Claude Code user out of the box.
- [ ] English (`<name>`) and Korean (`<name>-ko`) variants are semantically equivalent.
- [ ] `.claude-plugin/plugin.json` is valid JSON (`python -m json.tool < .claude-plugin/plugin.json`).
- [ ] README tables, plugin manifest, and skill directory names all agree.

## Improving an existing skill

Same checklist applies. **Update both language variants in the same PR** — drift between `<name>` and `<name>-ko` is the most common source of bugs here.

## Issues

Bug reports and feature requests welcome. For "this skill doesn't trigger when I say X", include the exact prompt you used so the trigger keywords can be tuned.
