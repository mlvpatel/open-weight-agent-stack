#!/usr/bin/env python3
"""Exercise the non-network production paths used by the local quality gate."""
from __future__ import annotations

import base64
import hashlib
import os
import shutil
import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_site
import check_invariants
import extract_diagrams
from lib import manual, render


REPO = Path(__file__).resolve().parent.parent


def copy_build_fixture(directory: str) -> Path:
    repo = Path(directory)
    (repo / "MANUAL.md").write_text((REPO / "MANUAL.md").read_text(encoding="utf-8"), encoding="utf-8")
    shutil.copytree(REPO / "assets", repo / "assets")
    shutil.copytree(REPO / "docs", repo / "docs")
    shutil.copytree(REPO / "site", repo / "site")
    return repo


def inline_script_span(template: str) -> tuple[int, int, int, int]:
    opening = template.index("<script>\n")
    body = opening + len("<script>")
    closing = template.index("</script>", body)
    return opening, body, closing, closing + len("</script>")


class ProductionPathTests(unittest.TestCase):
    def test_manual_model_measures_the_repository_source(self) -> None:
        parsed = manual.load()

        self.assertEqual(parsed.section_count, 27)
        self.assertEqual(parsed.diagram_count, 20)
        self.assertGreater(parsed.link_count, parsed.unique_links)
        self.assertIn("1-how-to-read-this-manual", parsed.anchors)
        self.assertEqual(manual.slug("A Test: Heading!"), "a-test-heading")

    def test_renderer_handles_each_supported_block_type(self) -> None:
        markdown = (
            "# Title\n\n## 1. Section\n\n### Detail\n\n"
            "paragraph **bold** *emphasis* `code` [link](https://example.com)\n\n"
            "- one\n  continued\n- two\n\n1. first\n2. second\n\n"
            "> quoted\n> text\n\n---\n\n"
            "| Head | Value |\n| --- | --- |\n| Row | data |\n\n"
            "```text\nplain\n```\n\n```mermaid\ngraph TD\nA-->B\n```\n"
        )

        output, figures = render.render(markdown, "%%{init: {}}%%\n")

        self.assertEqual(figures, 1)
        for expected in ("<h1>", "<section", "<h3", "<p>", "<ul>", "<ol>",
                         "<blockquote>", "<hr>", "<table>", "<pre><code>", "mermaid"):
            self.assertIn(expected, output)

    def test_generated_artifacts_and_invariants_hold_without_network(self) -> None:
        original_site = (REPO / "site" / "index.html").read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            repo = copy_build_fixture(directory)
            self.assertEqual(build_site.build(repo), 0)
            self.assertIn("Content-Security-Policy", (repo / "site" / "index.html").read_text(encoding="utf-8"))
        self.assertEqual((REPO / "site" / "index.html").read_bytes(), original_site)

    def test_csp_hash_accepts_mixed_case_inline_script_tags(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = copy_build_fixture(directory)
            template_path = repo / "site" / "template.html"
            template = template_path.read_text(encoding="utf-8")
            opening, body_start, closing, end = inline_script_span(template)
            script_body = template[body_start:closing]
            template_path.write_text(
                template[:opening] + "<ScRiPt>" + script_body + "</sCrIpT>" + template[end:],
                encoding="utf-8",
            )

            self.assertEqual(build_site.build(repo), 0)
            digest = base64.b64encode(hashlib.sha256(script_body.encode()).digest()).decode()
            self.assertIn(f"'sha256-{digest}'", (repo / "site" / "index.html").read_text(encoding="utf-8"))

    def test_csp_hash_rejects_multiple_inline_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = copy_build_fixture(directory)
            template_path = repo / "site" / "template.html"
            template_path.write_text(
                template_path.read_text(encoding="utf-8").replace(
                    "</body>", "<script>window.unexpected = true;</script>\n</body>", 1
                ),
                encoding="utf-8",
            )
            self.assertEqual(build_site.build(repo), 1)

    def test_csp_hash_rejects_missing_inline_script(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = copy_build_fixture(directory)
            template_path = repo / "site" / "template.html"
            template = template_path.read_text(encoding="utf-8")
            opening, _, _, end = inline_script_span(template)
            template_path.write_text(template[:opening] + template[end:], encoding="utf-8")
            self.assertEqual(build_site.build(repo), 1)

        original_env = os.environ.get("SKIP_REPO_DESCRIPTION")
        os.environ["SKIP_REPO_DESCRIPTION"] = "1"
        check_invariants.FAILURES.clear()
        check_invariants.SUMMARY.clear()
        try:
            self.assertEqual(check_invariants.main(), 0)
        finally:
            check_invariants.FAILURES.clear()
            check_invariants.SUMMARY.clear()
            if original_env is None:
                os.environ.pop("SKIP_REPO_DESCRIPTION", None)
            else:
                os.environ["SKIP_REPO_DESCRIPTION"] = original_env

    def test_diagram_extraction_matches_committed_sources(self) -> None:
        original_root = extract_diagrams.ROOT
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "MANUAL.md").write_text(
                (REPO / "MANUAL.md").read_text(encoding="utf-8"), encoding="utf-8")
            extract_diagrams.ROOT = root
            try:
                self.assertEqual(extract_diagrams.main(), 0)
                # NAMES is positional: entry N must be the manual's Nth mermaid block.
                # Spot-checking one entry passes even when a diagram inserted earlier in
                # the manual has shifted every later name onto the wrong content, so
                # check the whole alignment.
                parsed = manual.load().diagrams
                self.assertEqual(len(parsed), len(extract_diagrams.NAMES))
                for index, name in enumerate(extract_diagrams.NAMES):
                    self.assertEqual(
                        (root / "diagrams" / "src" / f"{name}.mmd").read_text(encoding="utf-8").strip(),
                        parsed[index].strip(),
                        f"{name}.mmd does not match the manual's diagram at position {index}: "
                        "extract_diagrams.NAMES is misaligned with MANUAL.md",
                    )
            finally:
                extract_diagrams.ROOT = original_root


if __name__ == "__main__":
    unittest.main()
