#!/usr/bin/env python3
"""A small CommonMark-subset renderer for MANUAL.md.

Deliberately stdlib-only. The manual uses a bounded set of constructs, so a
focused renderer beats a dependency here: it adds no supply-chain surface, runs
on any Python the repository already requires, and cannot drift from the theme.

Supported: ATX headings, paragraphs, pipe tables, ordered and unordered lists,
fenced code (mermaid becomes a figure), blockquotes, horizontal rules, and the
inline set (strong, emphasis, code, links, autolinks).
"""
from __future__ import annotations

import html
import re

from .manual import slug


def _inline(text: str) -> str:
    """Inline markdown to HTML. Code spans are extracted first so their
    contents are never re-interpreted as markup."""
    spans: list[str] = []

    def stash(m):
        spans.append(f"<code>{html.escape(m.group(1))}</code>")
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)


def _table(rows: list[str]) -> str:
    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    head = cells(rows[0])
    body = [cells(r) for r in rows[2:]]
    out = ['<div class="table-wrap"><table><thead><tr>']
    out += [f'<th scope="col">{_inline(c)}</th>' for c in head]
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>")
        for i, c in enumerate(row):
            tag = 'th scope="row"' if i == 0 else "td"
            close = "th" if i == 0 else "td"
            out.append(f"<{tag}>{_inline(c)}</{close}>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def render(md: str, mermaid_init: str) -> tuple[str, int]:
    """Return (html, figure_count). Mermaid fences become numbered figures."""
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    fig = 0
    in_section = False

    def close_section():
        nonlocal in_section
        if in_section:
            out.append("</section>")
            in_section = False

    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.startswith("```"):
            lang = line[3:].strip()
            j = i + 1
            buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j])
                j += 1
            body = "\n".join(buf)
            if lang == "mermaid":
                fig += 1
                out.append(
                    f'<figure class="plate"><div class="plate-body">'
                    f'<pre class="mermaid">{html.escape(mermaid_init + body, quote=False)}</pre></div>'
                    f'<figcaption><span class="fno">Fig. {fig:02d}</span></figcaption></figure>'
                )
            else:
                out.append(f"<pre><code>{html.escape(body)}</code></pre>")
            i = j + 1
            continue

        m = re.match(r"^(#{1,4})\s+(.+)$", line)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            if level == 1:
                out.append(f"<h1>{_inline(text)}</h1>")
            elif level == 2:
                close_section()
                out.append(f'<section id="{slug(text)}" class="reveal">')
                in_section = True
                out.append(f'<div class="sec-head"><h2>{_inline(text)}</h2></div>')
            else:
                out.append(f'<h{level} id="{slug(text)}">{_inline(text)}</h{level}>')
            i += 1
            continue

        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1].strip()):
            j = i
            rows = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(lines[j])
                j += 1
            out.append(_table(rows))
            i = j
            continue

        if re.match(r"^---+$", line.strip()):
            out.append("<hr>")
            i += 1
            continue

        if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
            ordered = bool(re.match(r"^\s*\d+\.\s+", line))
            tag = "ol" if ordered else "ul"
            items = []
            j = i
            pat = r"^\s*\d+\.\s+(.*)$" if ordered else r"^\s*[-*]\s+(.*)$"
            while j < len(lines):
                mm = re.match(pat, lines[j])
                if mm:
                    items.append(mm.group(1))
                elif lines[j].startswith("  ") and items:
                    items[-1] += " " + lines[j].strip()
                else:
                    break
                j += 1
            out.append(f"<{tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + f"</{tag}>")
            i = j
            continue

        if line.startswith(">"):
            buf = []
            j = i
            while j < len(lines) and lines[j].startswith(">"):
                buf.append(lines[j].lstrip("> ").rstrip())
                j += 1
            out.append(f"<blockquote><p>{_inline(' '.join(buf))}</p></blockquote>")
            i = j
            continue

        buf = [line]
        j = i + 1
        while j < len(lines) and lines[j].strip() and not re.match(
            r"^(#{1,4}\s|\||```|>|\s*[-*]\s|\s*\d+\.\s|---+$)", lines[j]
        ):
            buf.append(lines[j])
            j += 1
        out.append(f"<p>{_inline(' '.join(x.strip() for x in buf))}</p>")
        i = j

    close_section()
    return "\n".join(out), fig
