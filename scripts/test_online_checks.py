#!/usr/bin/env python3
"""Offline tests for the online check group: git and gh are faked, never called."""
from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_invariants as ci  # noqa: E402


def completed(code: int = 0, stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=code, stdout=stdout, stderr="")


def fake_git(fetch_code: int, state: str | None):
    """subprocess.run stand-in: a fetch result, then the state file contents."""
    def run(args, **_kwargs):
        if args[:2] == ["git", "fetch"]:
            return completed(fetch_code)
        return completed(0, state) if state is not None else completed(128)
    return run


class OnlineChecks(unittest.TestCase):
    def setUp(self) -> None:
        ci.FAILURES.clear()
        ci.SUMMARY.clear()

    def tearDown(self) -> None:
        ci.FAILURES.clear()
        ci.SUMMARY.clear()

    def heartbeat(self, fetch_code: int, state: str | None, in_ci: bool = False) -> None:
        with mock.patch.dict(os.environ, {}, clear=False), \
                mock.patch.object(ci.subprocess, "run", fake_git(fetch_code, state)):
            os.environ.pop("GITHUB_ACTIONS", None)
            if in_ci:
                os.environ["GITHUB_ACTIONS"] = "true"
            ci.check_freshness_heartbeat()

    def test_heartbeat_outcomes(self) -> None:
        today = date.today()
        cases = [
            (json.dumps({"last_run": today.isoformat()}), None),
            (json.dumps({"last_run": (today - timedelta(days=30)).isoformat()}), "30 days ago"),
            (json.dumps({"last_run": (today + timedelta(days=2)).isoformat()}), "future"),
            (json.dumps({"last_run": "yesterday"}), "not an ISO timestamp"),
            (json.dumps({}), "no last_run"),
            ("{not json", "not valid JSON"),
            (None, "has no .github/upstream-state.json"),
        ]
        for state, expected in cases:
            with self.subTest(expected=expected):
                self.setUp()
                self.heartbeat(0, state)
                if expected is None:
                    self.assertEqual(ci.FAILURES, [])
                else:
                    self.assertTrue(any(expected in f for f in ci.FAILURES), ci.FAILURES)

    def test_heartbeat_fetch_failure_skips_locally_and_fails_in_ci(self) -> None:
        self.heartbeat(1, None)
        self.assertEqual(ci.FAILURES, [])
        self.assertIn("skipped", ci.SUMMARY[-1])
        self.setUp()
        self.heartbeat(1, None, in_ci=True)
        self.assertTrue(any("could not fetch" in f for f in ci.FAILURES))

    def test_repo_description_and_release(self) -> None:
        m = SimpleNamespace(section_count=27, diagram_count=20)
        version = json.loads((ci.REPO / "package.json").read_text(encoding="utf-8"))["version"]
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SKIP_REPO_DESCRIPTION", None)
            with mock.patch.object(ci, "gh", return_value="27 sections and 19 diagrams"):
                ci.check_repo_description(m)
            self.assertTrue(any("says 19 diagrams" in f for f in ci.FAILURES))
            self.setUp()
            with mock.patch.object(ci, "gh", return_value=""):
                ci.check_repo_description(m)
            self.assertTrue(any("no description" in f for f in ci.FAILURES))
            for tag, expected in ((f"v{version}", None), ("v0.0.1", None), ("v999.0.0", "GitHub release is")):
                self.setUp()
                with mock.patch.object(ci, "gh", return_value=tag):
                    ci.check_release_version()
                if expected is None:
                    self.assertEqual(ci.FAILURES, [], tag)
                else:
                    self.assertTrue(any(expected in f for f in ci.FAILURES), ci.FAILURES)


if __name__ == "__main__":
    unittest.main()
