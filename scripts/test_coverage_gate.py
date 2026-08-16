#!/usr/bin/env python3
"""Regression contract for the stdlib Python coverage gate.

Run: python3 scripts/test_coverage_gate.py
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

import coverage_gate


REPO = Path(__file__).resolve().parent.parent


def regression_modules_on_disk() -> set[str]:
    return {path.name for path in (REPO / "scripts").glob("test_*.py")}


def rostered_regression_modules() -> set[str]:
    """Every regression module some roster actually runs.

    The roster is written down twice, once as the npm `test` command and once as
    `coverage_gate.TEST_SCRIPTS`, and the two deliberately differ: the coverage
    harness runs the modules whose execution it measures.  Neither list alone is
    the roster, so membership means appearing in at least one.
    """
    npm_test_command = json.loads((REPO / "package.json").read_text(encoding="utf-8"))["scripts"]["test"]
    rostered = {name for name in regression_modules_on_disk() if name in npm_test_command}
    rostered.update(coverage_gate.TEST_SCRIPTS)
    return rostered


class CoverageGateTests(unittest.TestCase):
    def test_target_selection_covers_every_repository_owned_production_module(self) -> None:
        targets = coverage_gate.production_modules(REPO)

        self.assertIn(REPO / "scripts" / "build_site.py", targets)
        self.assertIn(REPO / "scripts" / "check_invariants.py", targets)
        self.assertIn(REPO / "scripts" / "extract_diagrams.py", targets)
        self.assertIn(REPO / "scripts" / "watch_upstream.py", targets)
        self.assertIn(REPO / "scripts" / "lib" / "manual.py", targets)
        self.assertIn(REPO / "scripts" / "lib" / "render.py", targets)
        self.assertFalse(any(path.name.startswith("test_") for path in targets))

    def test_gate_rejects_a_low_actual_line_coverage_measurement(self) -> None:
        coverage = {REPO / "scripts" / "lib" / "manual.py": (1, 100)}

        self.assertFalse(coverage_gate.meets_threshold(coverage, 80.0))

    def test_every_regression_module_on_disk_is_run_by_some_roster(self) -> None:
        unrun = sorted(regression_modules_on_disk() - rostered_regression_modules())

        self.assertEqual(
            unrun,
            [],
            "these regression modules exist but no roster runs them, so they would "
            "pass CI without ever executing: "
            + ", ".join(unrun)
            + ". Add each to the npm test command in package.json or to "
            "TEST_SCRIPTS in scripts/coverage_gate.py.",
        )

    def test_no_roster_names_a_regression_module_that_does_not_exist(self) -> None:
        missing = sorted(set(coverage_gate.TEST_SCRIPTS) - regression_modules_on_disk())

        self.assertEqual(
            missing,
            [],
            "coverage_gate.TEST_SCRIPTS names modules that are not on disk, which "
            "fails the coverage run at import time: " + ", ".join(missing),
        )


if __name__ == "__main__":
    unittest.main()
