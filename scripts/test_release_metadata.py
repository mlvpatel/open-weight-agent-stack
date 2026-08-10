#!/usr/bin/env python3
"""Offline consistency checks for the local release candidate metadata."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
VERSION = "1.1.1"
RELEASE_DATE = "2026-08-11"


class ReleaseMetadataTests(unittest.TestCase):
    def test_all_release_metadata_describes_the_same_local_candidate(self) -> None:
        package = json.loads((REPO / "package.json").read_text())
        lockfile = json.loads((REPO / "package-lock.json").read_text())
        sbom = json.loads((REPO / "sbom.cdx.json").read_text())
        citation = (REPO / "CITATION.cff").read_text()
        changelog = (REPO / "CHANGELOG.md").read_text()
        readme = (REPO / "README.md").read_text()

        self.assertEqual(package["version"], VERSION)
        self.assertEqual(lockfile["version"], VERSION)
        self.assertEqual(lockfile["packages"][""]["version"], VERSION)
        self.assertEqual(sbom["metadata"]["component"]["version"], VERSION)
        self.assertEqual(sbom["metadata"]["component"]["bom-ref"], f"open-weight-agent-stack@{VERSION}")
        self.assertEqual(re.findall(r"^\s*version: \"([^\"]+)\"$", citation, re.M), [VERSION, VERSION])
        self.assertIn(f"date-released: \"{RELEASE_DATE}\"", citation)
        self.assertIsNotNone(re.search(rf"^## {re.escape(VERSION)}\b", changelog, re.M))
        self.assertRegex(readme, rf"{re.escape(VERSION)}\s+(?:local )?release candidate", re.I)
        self.assertNotIn("GitHub release 1.1.1", readme)


if __name__ == "__main__":
    unittest.main()
