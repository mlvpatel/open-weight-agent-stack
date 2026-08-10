#!/usr/bin/env python3
"""Regression tests for the debounce in watch_upstream.

These exist because the first implementation inverted its own purpose: it
suppressed the stable change it was written to catch, and reported only the
transient flap it was written to suppress. The bug was invisible to a passing
CI run, so the behaviour is now pinned by test.

Run: python3 scripts/test_watch_upstream.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import watch_upstream as w  # noqa: E402

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  pass  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        FAILURES.append(name)


def drive(sequence, tmp: Path):
    """Run main() once per entry, with fetch_json stubbed to that entry's licence.
    Returns the list of (exit_code, pending_snapshot)."""
    w.STATE_PATH = tmp / "state.json"
    w.WATCHED_MODELS = ["test/model"]
    results = []
    for lic in sequence:
        w.fetch_json = lambda url, _l=lic: (
            {"license": _l, "cardData": {}} if "huggingface" in url else {"version": "1.0.0"}
        )
        w.project_dependencies = lambda: {}
        cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp)
            code = w.main()
        finally:
            os.chdir(cwd)
        state = json.loads(w.STATE_PATH.read_text())
        results.append((code, dict(state["pending"])))
    return results


def test_stable_change_is_reported():
    """A real change that persists must be reported on the second observation."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        # baseline mit, then apache twice (a real upstream relicence)
        runs = drive(["mit", "apache-2.0", "apache-2.0"], tmp)
        codes = [c for c, _ in runs]
        check("stable change: first run establishes baseline", codes[0] == 0)
        check("stable change: second run does not report yet", codes[1] == 0,
              f"got {codes[1]}")
        check("stable change: THIRD run reports it (exit 2)", codes[2] == 2,
              f"got exit codes {codes}")


def test_flap_is_not_reported():
    """A value that changes and reverts must never be reported."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        runs = drive(["mit", "apache-2.0", "mit", "apache-2.0", "mit"], tmp)
        codes = [c for c, _ in runs]
        check("flapping change is never reported", all(c == 0 for c in codes),
              f"got exit codes {codes}")


def test_no_change_is_quiet():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        runs = drive(["mit", "mit", "mit"], tmp)
        codes = [c for c, _ in runs]
        check("unchanged upstream stays quiet", all(c == 0 for c in codes),
              f"got exit codes {codes}")
        check("unchanged upstream leaves no pending state", runs[-1][1] == {},
              f"pending={runs[-1][1]}")


def main() -> int:
    print("watch_upstream debounce:")
    test_stable_change_is_reported()
    test_flap_is_not_reported()
    test_no_change_is_quiet()
    if FAILURES:
        print(f"\n{len(FAILURES)} test(s) failed", file=sys.stderr)
        return 1
    print("\nall debounce tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
