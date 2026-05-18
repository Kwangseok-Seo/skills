#!/usr/bin/env python3
"""Convert a Claude Code JSONL transcript to readable markdown.

Usage:
    python convert_transcript.py <path-to-transcript.jsonl>

Writes markdown to stdout. user/assistant turns become `## role` headers;
tool uses and tool results are folded into code blocks. Tool output longer
than MAX_TOOL_OUTPUT is truncated with a marker.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MAX_TOOL_OUTPUT = 4000


def render_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        inner = content.get("content")
        if inner is not None:
            return render_content(inner)
        text = content.get("text")
        if text:
            return text
        return json.dumps(content, ensure_ascii=False, indent=2)
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type")
                if btype == "text":
                    parts.append(block.get("text", ""))
                elif btype == "tool_use":
                    name = block.get("name", "?")
                    inputs = block.get("input", {})
                    parts.append(
                        f"**[tool_use: {name}]**\n```json\n"
                        f"{json.dumps(inputs, ensure_ascii=False, indent=2)}\n```"
                    )
                elif btype == "tool_result":
                    raw = block.get("content", "")
                    text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
                    if len(text) > MAX_TOOL_OUTPUT:
                        text = text[:MAX_TOOL_OUTPUT] + "\n\n[tool output truncated]"
                    parts.append(f"**[tool_result]**\n```\n{text}\n```")
                else:
                    parts.append(json.dumps(block, ensure_ascii=False))
            else:
                parts.append(str(block))
        return "\n\n".join(parts)
    return str(content)


def transcript_to_markdown(path: Path) -> str:
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        role = msg.get("type") or msg.get("role") or "unknown"
        content = msg.get("message") or msg.get("content") or msg
        body = render_content(content)
        if not body.strip():
            continue
        out.append(f"## {role}\n\n{body}\n")
    return "\n".join(out)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    if len(sys.argv) != 2:
        print("usage: convert_transcript.py <transcript.jsonl>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"not found: {path}", file=sys.stderr)
        return 1
    sys.stdout.write(transcript_to_markdown(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
