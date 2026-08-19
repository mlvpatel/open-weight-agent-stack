#!/usr/bin/env python3
"""Tests for tilde-style (~~~) code fence handling in the markdown renderer.

render()'s fence state machine used to recognize only triple-backtick fences
(a plain ``line.startswith("```")`` check). scripts/build_site.py already
handles both CommonMark fence styles -- 3+ backticks or 3+ tildes, closed only
by a line of the same character -- via its own _FENCE_OPEN/_split_fences
logic. render() lacked the equivalent: a tilde-fenced block would fall through
to paragraph handling, leaking the literal "~~~" marker lines into a <p> as
escaped text instead of becoming a <pre><code> block.

MANUAL.md has zero tilde fences today (see the `grep -c '~~~'` check in the
project's fix instructions), so this defect could not be caught by rendering
the real manual. These tests construct tilde-fenced markdown directly.

Run: python3 scripts/test_render_fences.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.render import render  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  pass  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        FAILURES.append(name)


def main() -> int:
    print("tilde fence basics:")
    body, _ = render(
        "# T\n\nIntro paragraph.\n\n~~~python\ndef f():\n    return 1\n~~~\n\nAfter fence text.\n",
        "%%init%%\n",
    )
    check(
        "code content survives unmangled inside pre/code",
        "<pre><code>def f():\n    return 1</code></pre>" in body,
        body,
    )
    check("no stray tilde markers leak into the output", "~~~" not in body, body)
    check(
        "paragraph after the fence stays a separate <p>, not swallowed",
        "<p>After fence text.</p>" in body,
        body,
    )
    check(
        "intro paragraph before the fence is untouched",
        "<p>Intro paragraph.</p>" in body,
        body,
    )

    print("\ntilde fence body may contain literal backticks:")
    body2, _ = render(
        "# T\n\n~~~text\nHere are backticks: ```not a nested fence```\n~~~\n\nDone.\n",
        "%%init%%\n",
    )
    check(
        "backticks inside a tilde fence are kept as plain code text",
        "Here are backticks: ```not a nested fence```" in body2,
        body2,
    )
    check(
        "a run of backticks inside a tilde fence does not close it early",
        "<p>Done.</p>" in body2,
        body2,
    )
    check("no stray tilde markers leak into the output", "~~~" not in body2, body2)

    print("\ntilde-fenced mermaid still becomes a numbered figure:")
    body3, count = render(
        "# T\n\n~~~mermaid\nflowchart LR\nA[ok]\n~~~\n",
        "%%{init: {}}%%\n",
    )
    check("mermaid figure is counted", count == 1, str(count))
    check(
        "mermaid source lands inside pre.mermaid",
        '<pre class="mermaid">' in body3 and "flowchart LR" in body3,
        body3,
    )
    check("no stray tilde markers leak into the output", "~~~" not in body3, body3)

    print("\nbacktick fences are unaffected (regression guard):")
    body4, count4 = render(
        "# T\n\n```mermaid\nflowchart LR\nA[ok]\n```\n\nAfter.\n",
        "%%{init: {}}%%\n",
    )
    check("backtick mermaid figure still counted", count4 == 1, str(count4))
    check(
        "backtick fence still closes on a backtick line, paragraph follows",
        "<p>After.</p>" in body4,
        body4,
    )
    body5, _ = render("# T\n\n```\nplain code\n```\n", "%%init%%\n")
    check(
        "plain backtick code fence still renders as pre/code",
        "<pre><code>plain code</code></pre>" in body5,
        body5,
    )

    if FAILURES:
        print(f"\n{len(FAILURES)} test(s) failed", file=sys.stderr)
        return 1
    print("\nall tilde-fence tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
