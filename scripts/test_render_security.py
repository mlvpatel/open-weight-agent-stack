#!/usr/bin/env python3
"""Injection tests for the markdown renderer.

These exist because the first implementation escaped with quote=False and then
interpolated the result into href="...", so a link URL containing a double
quote closed the attribute and injected a live event handler into the published
site. Every payload below produced executable markup before the fix.

Run: python3 scripts/test_render_security.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.render import _inline, render  # noqa: E402

FAILURES: list[str] = []

# Markdown inputs that must not produce live markup. Escaped text is fine:
# &lt;img onerror=...&gt; is inert content, so the test parses the output and
# judges real elements and real attributes rather than matching substrings.
PAYLOADS = [
    ("attribute break-out", '[click](" onmouseover="alert(1))'),
    ("attribute break-out, single quote", "[click](' onfocus='alert(1))"),
    ("javascript scheme", "[click](javascript:alert(1))"),
    ("javascript scheme, mixed case", "[click](JaVaScRiPt:alert(1))"),
    ("data uri", "[x](data:text/html,<script>alert(1)</script>)"),
    ("vbscript scheme", "[x](vbscript:msgbox(1))"),
    ("raw script tag", "<script>alert(1)</script>"),
    ("img onerror", '<img src=x onerror="alert(1)">'),
    ("quote in link label", '[a"b](https://example.com)'),
    ("svg onload", "<svg onload=alert(1)>"),
    ("iframe injection", '<iframe src="javascript:alert(1)"></iframe>'),
    ("code span cannot escape", "`</code><script>alert(1)</script>`"),
    ("nested link in label", '[[x](javascript:alert(1))](https://ok.com)'),
]

ALLOWED_TAGS = {"a", "strong", "em", "code"}
DANGEROUS_SCHEMES = ("javascript:", "data:", "vbscript:")


def audit(fragment: str) -> list[str]:
    """Return concrete problems found in rendered output."""
    from html.parser import HTMLParser

    problems: list[str] = []

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag not in ALLOWED_TAGS:
                problems.append(f"emitted <{tag}>, which the renderer must never produce")
            for name, value in attrs:
                if name.lower().startswith("on"):
                    problems.append(f"event handler {name}= on <{tag}>")
                if name.lower() in ("href", "src") and value:
                    v = value.strip().lower().replace("\t", "").replace("\n", "")
                    if v.startswith(DANGEROUS_SCHEMES):
                        problems.append(f"{name}={value[:40]} uses an executable scheme")

    P().feed(fragment)
    return problems

# Links that must keep working. Over-blocking would break the manual.
ALLOWED = [
    ("https", "[x](https://example.com/a?b=c&d=e)", "https://example.com"),
    ("http", "[x](http://example.com)", "http://example.com"),
    ("fragment", "[x](#22-task-to-model-routing)", "#22-task-to-model-routing"),
    ("relative md", "[x](docs/MODELS.md)", "docs/MODELS.md"),
    ("relative parent", "[x](../MANUAL.md#5-master-architecture)", "../MANUAL.md"),
    ("mailto", "[x](mailto:someone@example.com)", "mailto:someone@example.com"),
]


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  pass  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        FAILURES.append(name)


def main() -> int:
    print("renderer injection resistance:")
    for name, md in PAYLOADS:
        out = _inline(md)
        problems = audit(out)
        check(name, not problems, f"{problems}: {out[:90]}")

    print("\nlegitimate links still work:")
    for name, md, expected in ALLOWED:
        out = _inline(md)
        check(name, f'href="{expected}' in out or expected in out,
              f"expected {expected} in {out[:90]}")

    print("\nfull-document render:")
    body, _ = render("# T\n\n[bad](\" onclick=\"alert(1))\n\nplain text\n", "%%init%%\n")
    # the document renderer emits structural tags too, so only judge attributes
    from html.parser import HTMLParser
    found: list[str] = []

    class D(HTMLParser):
        def handle_starttag(self, tag, attrs):
            for n, v in attrs:
                if n.lower().startswith("on"):
                    found.append(f"{n} on <{tag}>")
                if n.lower() in ("href", "src") and v and v.strip().lower().startswith(DANGEROUS_SCHEMES):
                    found.append(f"{n}={v[:30]}")

    D().feed(body)
    check("document render blocks handler injection", not found, str(found))

    if FAILURES:
        print(f"\n{len(FAILURES)} test(s) failed", file=sys.stderr)
        return 1
    print("\nall renderer security tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
