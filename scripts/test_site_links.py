#!/usr/bin/env python3
"""Regression tests for repository-document links in the generated site."""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_invariants
from build_site import publish_repository_markdown_links


REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site" / "index.html"
GITHUB_BLOB = "https://github.com/mlvpatel/open-weight-agent-stack/blob/main/"


class GeneratedSiteLinkTests(unittest.TestCase):
    def main_html(self, document: str) -> str:
        """Body markup only. The global nav also contains page links."""
        match = re.search(r"<main\b[^>]*>(.*)</main>", document, re.S)
        self.assertIsNotNone(match, "generated page is missing main")
        return match.group(1)

    def published_html_links(self, fragment: str) -> list[str]:
        return re.findall(r'href="([\w.-]+\.html(?:#[^"]*)?)"', fragment)

    def build_site(self) -> str:
        result = subprocess.run(
            [sys.executable, "scripts/build_site.py"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return SITE.read_text(encoding="utf-8")

    def test_repository_markdown_links_use_stable_github_urls(self) -> None:
        """Pages serves only ``site/``; source docs must not become 404s."""
        html = self.build_site()

        self.assertIn(f'href="{GITHUB_BLOB}docs/VERIFICATION.md"', html)
        self.assertNotIn('href="docs/VERIFICATION.md"', html)
        index_main = self.main_html(html)
        self.assertIn('href="models.html"', index_main)
        self.assertNotIn(f'href="{GITHUB_BLOB}docs/MODELS.md"', html)
        self.assertNotIn('href="docs/MODELS.md"', html)

        architecture = self.main_html((REPO / "site" / "architecture.html").read_text(encoding="utf-8"))
        architecture_links = self.published_html_links(architecture)
        self.assertEqual(len(architecture_links), 30)
        self.assertTrue(all(link.startswith("index.html#") for link in architecture_links))
        self.assertIn("index.html#18-identity-delegation-and-authority", architecture_links)

        models = self.main_html((REPO / "site" / "models.html").read_text(encoding="utf-8"))
        self.assertEqual(
            self.published_html_links(models),
            [
                "index.html#22-task-to-model-routing",
                "index.html#2-what-can-you-actually-run",
                "index.html#27-sources-and-verification",
            ],
        )

    def test_converter_preserves_fragments_and_code_examples(self) -> None:
        markdown = (
            "[model](docs/MODELS.md#licence-notes)\n\n"
            "```markdown\n[example](docs/MODELS.md)\n```\n"
            "See `[inline](docs/MODELS.md)` in a span.\n"
            "````markdown\n[four](docs/ARCHITECTURE.md)\n````\n"
        )

        converted = publish_repository_markdown_links(markdown)

        self.assertIn("(models.html#licence-notes)", converted)
        self.assertIn("[example](docs/MODELS.md)", converted)
        self.assertIn("`[inline](docs/MODELS.md)`", converted)
        self.assertIn("[four](docs/ARCHITECTURE.md)", converted)

    def test_generated_site_link_invariant_passes(self) -> None:
        self.build_site()
        result = subprocess.run(
            [sys.executable, "scripts/check_invariants.py", "--only", "offline"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("generated-links:", result.stdout)

    def test_offline_group_never_runs_clock_or_network_checks(self) -> None:
        # npm test and the deploy gate must not depend on the date or on origin.
        called = []
        names = ("check_last_verified", "check_freshness_heartbeat",
                 "check_repo_description", "check_release_version")
        originals = {name: getattr(check_invariants, name) for name in names}
        try:
            for name in names:
                setattr(check_invariants, name, lambda *_args, _n=name: called.append(_n))
            check_invariants.FAILURES.clear()
            check_invariants.SUMMARY.clear()
            self.assertEqual(check_invariants.main(["--only", "offline"]), 0)
            self.assertEqual(called, [])
            check_invariants.SUMMARY.clear()
            check_invariants.main(["--only", "online"])
            self.assertEqual(called, list(names))
        finally:
            for name, function in originals.items():
                setattr(check_invariants, name, function)
            check_invariants.FAILURES.clear()
            check_invariants.SUMMARY.clear()

    def test_generated_site_invariant_rejects_unpublished_relative_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "site").mkdir()
            (repo / "site" / "index.html").write_text(
                '<a href="docs/MODELS.md">Models</a>', encoding="utf-8")
            original_repo = check_invariants.REPO
            check_invariants.REPO = repo
            check_invariants.FAILURES.clear()
            check_invariants.SUMMARY.clear()
            try:
                check_invariants.check_generated_site_links()
                self.assertEqual(len(check_invariants.FAILURES), 1)
                self.assertIn("does not publish", check_invariants.FAILURES[0])
            finally:
                check_invariants.REPO = original_repo
                check_invariants.FAILURES.clear()
                check_invariants.SUMMARY.clear()

    def test_evidence_markers_reject_bare_word(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "MANUAL.md").write_text("This number is indicative only.\n", encoding="utf-8")
            original_repo = check_invariants.REPO
            check_invariants.REPO = repo
            check_invariants.FAILURES.clear()
            check_invariants.SUMMARY.clear()
            try:
                check_invariants.check_evidence_markers()
                self.assertTrue(any("not a backticked marker" in item for item in check_invariants.FAILURES))
            finally:
                check_invariants.REPO = original_repo
                check_invariants.FAILURES.clear()
                check_invariants.SUMMARY.clear()

    def test_last_verified_rejects_stale_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "docs").mkdir()
            stale = "**Last verified:** 1 January 2020\n"
            (repo / "MANUAL.md").write_text(stale, encoding="utf-8")
            (repo / "docs" / "MODELS.md").write_text(stale, encoding="utf-8")
            original_repo = check_invariants.REPO
            original_limit = check_invariants.LAST_VERIFIED_MAX_AGE_DAYS
            check_invariants.REPO = repo
            check_invariants.LAST_VERIFIED_MAX_AGE_DAYS = 45
            check_invariants.FAILURES.clear()
            check_invariants.SUMMARY.clear()
            try:
                check_invariants.check_last_verified()
                self.assertTrue(any("days old" in item for item in check_invariants.FAILURES))
            finally:
                check_invariants.REPO = original_repo
                check_invariants.LAST_VERIFIED_MAX_AGE_DAYS = original_limit
                check_invariants.FAILURES.clear()
                check_invariants.SUMMARY.clear()


if __name__ == "__main__":
    unittest.main()
