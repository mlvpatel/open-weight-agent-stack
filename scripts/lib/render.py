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

# Human titles for published figures. Order matches extract_diagrams.NAMES
# and the mermaid fences in MANUAL.md. Captions are chrome, not new claims.
FIGURE_TITLES = (
    "Concentric rings",
    "Hardware paths",
    "Master architecture",
    "Request lifecycle",
    "Agent control loop",
    "RAG pipeline",
    "Model routing",
    "Prompt contract",
    "Trust boundaries",
    "Memory tiers",
    "Guardrails and evals",
    "Deployment topology",
    "Data lifecycle",
    "Serving budgets",
    "Identity delegation",
    "Threat write-paths",
    "Latency budget",
    "Technology catalogue",
    "Task-to-model quadrant",
    "Platform SDK",
)


# Only these may appear in an href. Anything else becomes inert text.
# javascript: and data: are the executable ones; vbscript: still works in some
# embedded engines. A relative path or fragment has no scheme at all.
_SAFE_SCHEME = re.compile(r"^(?:https?:|mailto:|#|/|\.{0,2}/|[\w.-]+\.md|[\w.-]+/)", re.I)


def _href(raw: str) -> str | None:
    """Return an attribute-safe href, or None if the URL is not safe to emit.

    The escaping here must include quotes. An earlier version escaped with
    quote=False and interpolated the result straight into href="...", so a link
    whose URL contained a double quote closed the attribute and everything after
    it became markup: [x](" onmouseover="alert(1)) produced a live event handler
    on the published site. That is stored XSS, and it is why this function
    exists instead of a regex replacement string.
    """
    url = raw.strip()
    if not url or not _SAFE_SCHEME.match(url):
        return None
    return html.escape(url, quote=True)


def _inline(text: str) -> str:
    """Inline markdown to HTML. Code spans are extracted first so their
    contents are never re-interpreted as markup."""
    spans: list[str] = []

    def stash(m):
        spans.append(f"<code>{html.escape(m.group(1), quote=True)}</code>")
        return f"\x00{len(spans) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    # quote=True, always. Link text is interpolated into markup too.
    text = html.escape(text, quote=True)

    def link(m):
        label, raw = m.group(1), m.group(2)
        # The URL arrives already entity-escaped by the pass above, so a quote
        # is &quot; here and cannot terminate the attribute. Unescape only to
        # judge the scheme, then re-escape for output.
        href = _href(html.unescape(raw))
        if href is None:
            return label          # unsafe scheme: keep the words, drop the link
        return f'<a href="{href}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
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
                title = FIGURE_TITLES[fig - 1] if fig <= len(FIGURE_TITLES) else ""
                number = f"Fig. {fig:02d}"
                label = f"{number}. {title}" if title else number
                studio = "dark" if fig % 2 else "light"
                title_html = f" {html.escape(title, quote=True)}" if title else ""
                out.append(
                    f'<figure class="plate" data-studio="{studio}" '
                    f'aria-label="{html.escape(label, quote=True)}">'
                    f'<div class="plate-body">'
                    f'<pre class="mermaid">{html.escape(mermaid_init + body, quote=False)}</pre>'
                    f'</div>'
                    f'<figcaption><span class="fno">{html.escape(number, quote=True)}</span>'
                    f'{title_html}</figcaption></figure>'
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
