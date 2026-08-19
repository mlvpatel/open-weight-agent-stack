#!/usr/bin/env python3
"""Regression contract for the stdlib Python coverage gate.

Run: python3 scripts/test_coverage_gate.py
"""
from __future__ import annotations

import json
import tempfile
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


class BranchTransitionCoverageTests(unittest.TestCase):
    """A synthetic module with one known if/else branch point, run under a
    controlled invocation that exercises only the true side, to prove the
    static extractor and the runtime tracer agree on exactly which
    transition pairs exist and which of those were actually observed.
    """

    # Line numbers matter here: line 2 is the branch point ("if x > 0:"),
    # line 3 is the true-branch body, line 5 is the else body.
    SYNTHETIC_SOURCE = (
        "def classify(x):\n"
        "    if x > 0:\n"
        "        result = 'positive'\n"
        "    else:\n"
        "        result = 'non-positive'\n"
        "    return result\n"
    )

    def _write_synthetic_module(self, directory: Path) -> Path:
        path = directory / "synthetic_branch_module.py"
        path.write_text(self.SYNTHETIC_SOURCE, encoding="utf-8")
        return path

    def _load_classify(self, path: Path):
        namespace: dict[str, object] = {}
        code = compile(self.SYNTHETIC_SOURCE, str(path), "exec")
        exec(code, namespace)
        return namespace["classify"]

    def test_static_branch_transitions_finds_both_edges_of_an_if_else(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write_synthetic_module(Path(tmp))
            transitions = coverage_gate.static_branch_transitions(path)

        self.assertEqual(transitions, {(2, 3), (2, 5)})

    def test_branch_coverage_reports_half_when_only_the_true_branch_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            module_path = self._write_synthetic_module(Path(tmp))
            static = {module_path: coverage_gate.static_branch_transitions(module_path)}
            classify = self._load_classify(module_path)

            tracer = coverage_gate.TransitionTracer()
            tracer.runfunc(classify, 5)  # only the true branch: x > 0

        coverage = coverage_gate.branch_coverage(static, tracer.transitions)
        exercised, possible = coverage[module_path]

        self.assertEqual(possible, 2)
        self.assertEqual(exercised, 1)
        self.assertEqual(exercised / possible, 0.5)
        self.assertIn((2, 3), tracer.transitions[str(module_path)])
        self.assertNotIn((2, 5), tracer.transitions[str(module_path)])

    def test_branch_coverage_reports_full_when_both_branches_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            module_path = self._write_synthetic_module(Path(tmp))
            static = {module_path: coverage_gate.static_branch_transitions(module_path)}
            classify = self._load_classify(module_path)

            tracer = coverage_gate.TransitionTracer()
            tracer.runfunc(classify, 5)
            tracer.runfunc(classify, -5)

        coverage = coverage_gate.branch_coverage(static, tracer.transitions)

        self.assertEqual(coverage[module_path], (2, 2))

    def test_transition_tracer_also_reproduces_plain_line_visit_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            module_path = self._write_synthetic_module(Path(tmp))
            classify = self._load_classify(module_path)

            tracer = coverage_gate.TransitionTracer()
            tracer.runfunc(classify, 5)

        # Line 3 (the true branch) was visited; line 5 (the else branch) was not.
        self.assertGreater(tracer.counts.get((str(module_path), 3), 0), 0)
        self.assertEqual(tracer.counts.get((str(module_path), 5), 0), 0)

    def test_branch_coverage_is_reported_for_every_repository_production_module(self) -> None:
        targets = coverage_gate.production_modules(REPO)

        static = {path: coverage_gate.static_branch_transitions(path) for path in targets}
        result = coverage_gate.branch_coverage(static, observed={})

        self.assertEqual(set(result), set(targets))
        for path in targets:
            exercised, possible = result[path]
            self.assertEqual(exercised, 0)  # no observations were supplied
            self.assertGreaterEqual(possible, 0)


if __name__ == "__main__":
    unittest.main()
