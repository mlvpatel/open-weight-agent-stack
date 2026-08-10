#!/usr/bin/env python3
"""Regression contract for the stdlib Python coverage gate.

Run: python3 scripts/test_coverage_gate.py
"""
from __future__ import annotations

import unittest
from pathlib import Path

import coverage_gate


REPO = Path(__file__).resolve().parent.parent


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


if __name__ == "__main__":
    unittest.main()
