#!/usr/bin/env python3
"""Contracts for truthful human, AI-assistance, and automation attribution."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
CONTRIBUTORS = REPO / "CONTRIBUTORS.md"
README = REPO / "README.md"
CONTRIBUTING = REPO / "CONTRIBUTING.md"


def section(text: str, start: str, end: str | None = None) -> str:
    """Return a required Markdown section, or an empty string if malformed."""
    if start not in text:
        return ""
    body = text.split(start, 1)[1]
    if end is None:
        return body
    if end not in body:
        return ""
    return body.split(end, 1)[0]


class ContributorAttributionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contributors = CONTRIBUTORS.read_text(encoding="utf-8") if CONTRIBUTORS.exists() else ""
        self.readme = README.read_text(encoding="utf-8")
        self.contributing = CONTRIBUTING.read_text(encoding="utf-8")

    def test_readme_exposes_the_attribution_record(self) -> None:
        contributors = section(
            self.readme,
            "## Contributors and AI assistance",
            "## Licence and citation",
        )
        self.assertIn("[GitHub Contributors graph]", contributors)
        self.assertIn("/graphs/contributors", contributors)
        self.assertIn("[AI-assistance record](CONTRIBUTORS.md)", contributors)

    def test_human_maintainer_retains_accountability(self) -> None:
        human = section(self.contributors, "## Human maintainer", "## AI-assisted development")
        self.assertIn("Malav Patel", human)
        self.assertRegex(human, r"(?i)final.*responsib")

    def test_only_evidenced_ai_assistants_are_listed(self) -> None:
        ai = section(self.contributors, "## AI-assisted development", "## Repository automation")
        rows = re.findall(r"^\| \[([^]]+)\]", ai, re.MULTILINE)
        self.assertEqual(rows, ["Claude Fable 5", "OpenAI Codex"])
        self.assertIn("Co-authored-by", ai)
        self.assertIn("repository disclosure", ai)
        self.assertNotIn("signed repository disclosure", ai)

    def test_ai_tools_are_not_impersonated_as_github_accounts(self) -> None:
        ai = section(self.contributors, "## AI-assisted development", "## Repository automation")
        self.assertNotRegex(ai, r"https://github\.com/(?:claude|openai|codex)(?:[/)#]|$)")

    def test_automation_is_not_mislabeled_as_llm_contribution(self) -> None:
        automation = section(self.contributors, "## Repository automation", "## Attribution policy")
        self.assertIn("Dependabot", automation)
        self.assertIn("freshness watcher", automation)
        self.assertRegex(automation, r"(?i)not.*AI.*co-author")

    def test_policy_explains_github_graph_and_non_authorship(self) -> None:
        policy = section(self.contributors, "## Attribution policy")
        flat_policy = " ".join(policy.split())
        self.assertIn("commit authors and co-authors", flat_policy)
        self.assertIn("email address associated with a GitHub account", flat_policy)
        self.assertIn("top 100", flat_policy)
        self.assertIn("default branch", flat_policy)
        self.assertRegex(flat_policy, r"(?i)merge commits and empty commits.*not counted")
        self.assertRegex(flat_policy, r"(?i)not.*legal authorship")
        self.assertRegex(flat_policy, r"(?i)models.*manual.*not contributors")

    def test_contribution_guide_requires_ai_disclosure_and_human_review(self) -> None:
        policy = section(self.contributing, "## AI-assisted contributions", "## What gets declined")
        self.assertIn("CONTRIBUTORS.md", policy)
        self.assertRegex(policy, r"(?i)disclose.*material AI assistance")
        self.assertRegex(policy, r"(?i)human.*verif")


if __name__ == "__main__":
    unittest.main()
