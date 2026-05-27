---
name: to-html
description: "Convert content (files, last output, pasted text) into a self-contained, human-readable HTML visualization — but only when it's worth it. First classifies the content against three patterns (Compare options side-by-side / Tune values interactively / Learn a concept with diagrams + code + caveats), estimates token cost (HTML output is typically ~5× the markdown equivalent), and offers alternatives when visualization adds no value. Defaults to Tailwind CDN + Mermaid + Chart.js, accepts a user-preferred toolset, and writes the result to `<cwd>/.claude/to-html/` without auto-opening. Use when the user says: 'to-html', 'convert to HTML', 'visualize as HTML', 'make an HTML grid', 'add a slider HTML', 'HTML study doc', 'render this as HTML'."
---

# To-HTML: visualize content as a single HTML file — when it's worth it

> *"HTML is the new Markdown."* — Tariq Sipha (Anthropic Claude Code team).
> Caveat from Pascal Filiteri's measurement: the same code review output was **1,140 tokens in Markdown and 5,480 tokens in HTML — roughly 5×**.

This skill helps the user convert content into a **single self-contained HTML file** when visualization actually adds value, and steers them back to Markdown (or another lighter format) when it doesn't. It is **manual** — it runs only when the user invokes it explicitly.

The output is always one file, no build step, no server. CDN-only dependencies so the file works by double-clicking it.

---

## When HTML is the right format (the three patterns)

Use HTML when the content fits one of these patterns. Otherwise Markdown is almost always cheaper and clearer.

| Pattern | What it does | One-line prompt the user might say |
|---------|--------------|------------------------------------|
| **Compare** | Lay out N options in a grid so they can be eyeballed at once. Designs, copy variants, layouts, plans. | *"Lay these out as an HTML grid so I can compare them side-by-side."* |
| **Tune** | Embed live controls (sliders, inputs, drag-and-drop) so the user can manipulate values and copy the result back. | *"Add an HTML slider so I can tune the value and copy it."* |
| **Learn** | A study page that fuses diagram + annotated code + caveats into one scrollable artifact. Concept explainers. | *"Make me a single HTML study doc with the diagram, annotated code, and caveats."* |

**Stop and use Markdown instead when:**

- The content is mostly prose / a single concept with no structure to surface.
- It's a checklist or todo list the user will *re-edit* (Markdown is editable, HTML is read-mostly).
- It's a code snippet (the editor's syntax highlighting already does the job).
- The content is under ~500 tokens — the HTML overhead is larger than the content.

---

## Workflow

### Phase 1 — Resolve input

Figure out *what* is being converted. Sources, in priority order:

1. **Explicit argument** to the skill (file path, glob, or a quoted block).
2. **The last assistant turn** — if the user says *"convert this to HTML"* with no other referent, they almost always mean the previous message.
3. **The user's current selection / clipboard** — only if the agent can read it.
4. **Ask the user.** Single combined question: *"What should I convert? (file path / last assistant output / paste it here)"*. Don't ask again.

Record the resolved source as `INPUT_DESC` (one line, used in the report).

### Phase 2 — Categorize + estimate

In one block, the agent reports to the user:

1. **Pattern fit** — which of {Compare, Tune, Learn, None} the input matches. Be honest; if it's none of the three, say so.
2. **Token estimate** — rough size of the input itself (`chars / 4` for English-leaning text, `chars / 2.5` for CJK-heavy text). Then a one-line cost warning citing the 5× HTML/Markdown multiplier from Pascal Filiteri's measurement.
3. **Visualization value** — High / Medium / Low judgment. Heuristics:

   | Signal in the input | Value |
   |---------------------|-------|
   | Structured comparison across ≥3 items | High → Compare |
   | Numeric values the user will *want to play with* | High → Tune |
   | Concept that needs diagram + code together | High → Learn |
   | Mostly flat prose | Low |
   | <500 input tokens | Low (overhead wins) |
   | Already a code listing | Low (editor wins) |

Present this as one block, e.g.:

```
Input: `notes/onboarding.md` (~2,800 tokens)
Pattern fit: Compare (6 onboarding variants)
HTML output will be ~5× the equivalent markdown output (Pascal Filiteri, measured).
Visualization value: High — grid layout will let you eyeball all 6 at once.

Proceed?  (1) yes, generate  (2) markdown summary instead  (3) ASCII table  (4) cancel
```

### Phase 3 — Gate (decide whether to proceed)

- **Value = High and the input is at least 500 tokens** → proceed straight to Phase 4 unless the user said otherwise.
- **Value = Low or pattern = None** → present alternatives and **wait for the user's decision**. Do not silently fall back to markdown; the user must choose. If there is no good alternative, say so and let the user decide.

Standard alternatives to offer:

- **Markdown summary** — distil the content into ~200–400 tokens of structured Markdown.
- **ASCII table** — for purely tabular data that fits in chat.
- **Mermaid block only** — if the only visualization need is a diagram.
- **Proceed anyway** — user's call; honor their intent.

Never ask the same question twice.

### Phase 4 — Tool preference

Default toolset (one line in the file `<head>`, all CDN, zero install):

- **Tailwind CSS (CDN)** — layout + typography. Always.
- **Mermaid (CDN)** — added only if the output will include diagrams.
- **Chart.js (CDN)** — added only if the output will include charts.
- **Vanilla JS** for sliders, drag-and-drop, copy-to-clipboard buttons (Tune pattern).

Ask the user **once**, in one combined line:

```
Default: Tailwind CDN (+ Mermaid / Chart.js if needed).  Any preferred toolset?
```

Honor anything the user names — alternative CSS frameworks, inline-only (no CDN, for offline / airgapped), specific chart libs. If they don't answer, use the default.

### Phase 5 — Generate + write

Build a **single self-contained `.html` file**:

- One file. No external assets besides the CDN script/link tags.
- All scripts at the end of `<body>` so the page renders first.
- For Tune-pattern outputs, every interactive control must have a **copy-to-clipboard button** next to it that copies the current value, so the user can paste it back to Claude.
- For Learn-pattern outputs, the structure is roughly: title → diagram (Mermaid) → annotated code blocks → "Caveats / gotchas" section at the bottom.
- For Compare-pattern outputs, use CSS grid with each option in its own card; equal-height cards; the user's evaluation criteria visible at the top.

Write the file to:

```
<save-dir>/YYYY-MM-DD-HHmm-{short-slug}.html
```

Where `<save-dir>` resolves as:

1. `$TO_HTML_DIR` if set in the environment, **else**
2. `<cwd>/.claude/to-html/`.

Create the directory if missing. Strip filesystem-unsafe characters from the slug: `:`, `/`, `\`, `?`, `*`, `"`, `<`, `>`, `|`.

**Do not open the file automatically.** Just report the path.

### Phase 6 — Report

Tell the user, in this exact shape:

```
✓ Wrote: <save-dir>/{filename}.html

Pattern: Compare | Tune | Learn
Input:   <one-line description of input>
Tools:   Tailwind CDN [+ Mermaid] [+ Chart.js] [+ user-named libs]
Est. output tokens: ~<n> (Markdown equivalent would be ~<n/5>)
```

Mention if any of Phase 3's alternatives were *also* generated alongside the HTML (rare, but allowed when the user explicitly asks for both).

---

## Stock prompts (drop-in, from the source article)

The skill is invoked when the user appends one of these (or similar) to their request. Recognize them as triggers and skip the "what should I convert?" question in Phase 1.

| Pattern | One-line prompt (English) |
|---------|---------------------------|
| Compare | *"...as an HTML grid so I can compare them side-by-side."* |
| Tune | *"...with a slider I can drag, and a copy button for the value."* |
| Learn | *"...as one HTML page with diagram, annotated code, and caveats."* |

---

## Don'ts

- **Don't auto-open the file.** Some users are on remote/headless boxes; some don't want their browser hijacked. Report the path and stop.
- **Don't silently fall back to Markdown** when value is Low — present alternatives and wait for the user's choice. Their judgment matters.
- **Don't generate HTML for a single short paragraph.** The 5× token cost is real; warn the user and recommend Markdown.
- **Don't pull arbitrary npm packages or local files.** Single self-contained file with CDN-only deps, full stop.
- **Don't ask the same question twice.** Pattern + estimate + alternatives go in *one* block. Tool preference goes in *one* line.
- **Don't auto-trigger.** Only run when the user invokes the skill explicitly.

---

## Customization

Defaults are intentionally simple. Edit this SKILL.md to change them:

- **Save directory** — set `TO_HTML_DIR` in the environment, or change Phase 5's default.
- **Default toolset** — Phase 4's CDN list. If you're frequently offline, switch to a Plain HTML/CSS default and document it here.
- **Slug length** — current convention is ≤40 chars of natural English/Korean; adjust in Phase 5 if filename collisions become annoying.

---

## Sources

This skill's heuristics come directly from Anthropic's published guidance and the surrounding community discussion:

- **Tariq Sipha** (Anthropic, Claude Code team) — the X post *"HTML is the new Markdown"* and the longer blog post listing five HTML use cases. This skill encodes the three most broadly useful (Compare / Tune / Learn).
- **Simon Willison** — commentary framing why Markdown originally won: brevity, not expressivity, in a smaller-context era.
- **Pascal Filiteri** — the measured token-cost comparison (1,140 vs 5,480 tokens for the same code review) that grounds the 5× warning in Phase 2.
- **Midnight Log** (YouTube `rTDzkJeO_lo`) — Korean-language summary that selects the same three patterns; this skill mirrors its framing.
