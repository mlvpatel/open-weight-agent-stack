#!/usr/bin/env python3
"""Regression tests for the upstream-freshness contract and debounce.

Run: python3 scripts/test_watch_upstream.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import urllib.error
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


def available(license_name: str) -> dict:
    return {"status": "available", "metadata": {
        "available": True,
        "license": license_name,
        "license_name": None,
        "gated": False,
    }}


def missing() -> dict:
    return {"status": "missing", "metadata": {"available": False}}


def transient(reason: str) -> dict:
    return {"status": "indeterminate", "reason": reason}


def drive(sequence: list[dict], tmp: Path) -> list[tuple[int, dict, str]]:
    """Run main once per supplied observation without using the network."""
    original_state_path = w.STATE_PATH
    original_models = w.WATCHED_MODELS
    original_project_model = w.project_model
    original_dependencies = w.project_dependencies
    original_latest_npm = w.latest_npm
    w.STATE_PATH = tmp / "state.json"
    w.WATCHED_MODELS = ("test/model",)
    iterator = iter(sequence)
    w.project_model = lambda _repo: next(iterator)
    w.project_dependencies = lambda: {}
    w.latest_npm = lambda _name: None
    results = []
    cwd = Path.cwd()
    try:
        os.chdir(tmp)
        for _ in sequence:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = w.main()
            state = json.loads(w.STATE_PATH.read_text())
            results.append((code, state, out.getvalue()))
    finally:
        os.chdir(cwd)
        w.STATE_PATH = original_state_path
        w.WATCHED_MODELS = original_models
        w.project_model = original_project_model
        w.project_dependencies = original_dependencies
        w.latest_npm = original_latest_npm
    return results


def drive_dependencies(sequence: list[str | None], tmp: Path) -> list[tuple[int, dict, str]]:
    """Run dependency-only observations without touching the network."""
    original_state_path = w.STATE_PATH
    original_models = w.WATCHED_MODELS
    original_project_model = w.project_model
    original_dependencies = w.project_dependencies
    original_latest_npm = w.latest_npm
    w.STATE_PATH = tmp / "state.json"
    w.WATCHED_MODELS = ()
    iterator = iter(sequence)
    w.project_model = lambda _repo: transient("not-used")
    w.project_dependencies = lambda: {"example": "1.0.0"}
    w.latest_npm = lambda _name: next(iterator)
    results = []
    cwd = Path.cwd()
    try:
        os.chdir(tmp)
        for _ in sequence:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = w.main()
            results.append((code, json.loads(w.STATE_PATH.read_text()), out.getvalue()))
    finally:
        os.chdir(cwd)
        w.STATE_PATH = original_state_path
        w.WATCHED_MODELS = original_models
        w.project_model = original_project_model
        w.project_dependencies = original_dependencies
        w.latest_npm = original_latest_npm
    return results


def test_source_coverage_contract() -> None:
    errors = w.coverage_contract_errors()
    check("every declared checkpoint has a freshness classification", not errors,
          "; ".join(errors))
    check("current Devstral checkpoint is automatically tracked",
          "mistralai/Devstral-Small-2-24B-Instruct-2512" in w.WATCHED_MODELS)
    check("stale Devstral checkpoint is not tracked",
          "mistralai/Devstral-Small-2507" not in w.WATCHED_MODELS)
    coverage = w.load_model_coverage()
    removed = dict(coverage)
    removed["automated_models"] = [
        model for model in coverage["automated_models"]
        if model != "mistralai/Devstral-Small-2-24B-Instruct-2512"
    ]
    check("removing a source classification fails the contract",
          any("Devstral-Small-2-24B-Instruct-2512" in error
              for error in w.coverage_contract_errors(removed)))


def test_transport_failure_classification() -> None:
    original_urlopen = w.urllib.request.urlopen
    try:
        for code, expected in [(404, "missing"), (410, "missing"), (401, "indeterminate"),
                               (403, "indeterminate"), (429, "indeterminate"), (500, "indeterminate")]:
            def raise_http(*_args, _code=code, **_kwargs):
                raise urllib.error.HTTPError("https://example.invalid", _code, "error", None, None)
            w.urllib.request.urlopen = raise_http
            check(f"HTTP {code} is {expected}", w.fetch_json("https://example.invalid")["status"] == expected)
        for name, error in [
            ("timeout", TimeoutError()),
            ("DNS or connection failure", urllib.error.URLError("offline")),
        ]:
            def raise_transport(*_args, _error=error, **_kwargs):
                raise _error
            w.urllib.request.urlopen = raise_transport
            result = w.fetch_json("https://example.invalid")
            check(f"{name} is indeterminate", result["status"] == "indeterminate")
            check(f"{name} has no raw exception body", result.get("reason") in {"network", "transport-error"})
    finally:
        w.urllib.request.urlopen = original_urlopen


def test_state_migration_drops_retired_ids() -> None:
    models = ("new/model",)
    legacy_observed = {
        "new/model": {"available": True, "license": "mit"},
        "mistralai/Devstral-Small-2507": {"available": True, "license": "apache-2.0"},
        "__deps__": {"puppeteer": "1.0.0"},
    }
    legacy_pending = {
        "new/model: license changed from 'mit' to 'apache-2.0'": 1,
        "mistralai/Devstral-Small-2507: license changed": 1,
        "dep:puppeteer:2.0.0": 1,
        "invalid": "not-a-count",
    }
    first = w.normalise_state(legacy_observed, legacy_pending, models)
    second = w.normalise_state(legacy_observed, legacy_pending, models)
    check("state migration retains usable current baselines",
          first[0]["new/model"]["license"] == "mit")
    check("state migration removes stale Devstral baseline",
          "mistralai/Devstral-Small-2507" not in first[0])
    check("state migration removes stale Devstral debounce",
          not any(key.startswith("mistralai/Devstral-Small-2507:") for key in first[1]))
    check("state migration is deterministic", first == second)


def test_stable_change_is_reported() -> None:
    with tempfile.TemporaryDirectory() as d:
        runs = drive([available("mit"), available("apache-2.0"), available("apache-2.0")], Path(d))
        codes = [code for code, _state, _out in runs]
        check("stable change: first run establishes baseline", codes[0] == 0)
        check("stable change: first differing observation is quiet", codes[1] == 0)
        check("stable change: second differing observation reports", codes[2] == 2,
              f"got exit codes {codes}")


def test_alternating_drift_requires_identical_consecutive_observations() -> None:
    with tempfile.TemporaryDirectory() as d:
        runs = drive(
            [available("mit"), available("apache-2.0"), available("gpl-3.0"),
             available("apache-2.0"), available("apache-2.0")],
            Path(d),
        )
        check("alternate model values do not reuse an old pending count",
              [code for code, _state, _out in runs[:4]] == [0, 0, 0, 0])
        check("second consecutive identical model value reports",
              runs[-1][0] == 2)
    with tempfile.TemporaryDirectory() as d:
        runs = drive_dependencies(["2.0.0", "3.0.0", "2.0.0", "2.0.0"], Path(d))
        check("alternate dependency values do not reuse an old pending count",
              [code for code, _state, _out in runs[:3]] == [0, 0, 0])
        check("second consecutive identical dependency value reports",
              runs[-1][0] == 2)
    with tempfile.TemporaryDirectory() as d:
        runs = drive_dependencies(["2.0.0", None, "2.0.0"], Path(d))
        check("indeterminate dependency lookup preserves pending count",
              runs[-1][0] == 2)


def test_flap_and_unchanged_are_quiet() -> None:
    with tempfile.TemporaryDirectory() as d:
        runs = drive(
            [available("mit"), available("apache-2.0"), available("mit"), available("apache-2.0"), available("mit")],
            Path(d),
        )
        check("flapping change is never reported", all(code == 0 for code, _state, _out in runs))
        check("flapping change clears pending state", runs[-1][1]["pending"] == {})
    with tempfile.TemporaryDirectory() as d:
        runs = drive([available("mit"), available("mit"), available("mit")], Path(d))
        check("unchanged upstream stays quiet", all(code == 0 for code, _state, _out in runs))
        check("unchanged upstream leaves no pending state", runs[-1][1]["pending"] == {})


def test_definitive_removal_debounces() -> None:
    with tempfile.TemporaryDirectory() as d:
        runs = drive([available("mit"), missing(), missing()], Path(d))
        codes = [code for code, _state, _out in runs]
        check("404 or 410 removal is reported after two differing observations", codes == [0, 0, 2],
              f"got {codes}")
        check("confirmed removal becomes the new baseline",
              runs[-1][1]["observed"]["test/model"] == {"available": False})


def test_transient_failure_preserves_baseline() -> None:
    with tempfile.TemporaryDirectory() as d:
        runs = drive([available("mit"), transient("http-429"), transient("network"), available("mit")], Path(d))
        state_after_failure = runs[2][1]
        check("transient failures never report disappearance", all(code == 0 for code, _state, _out in runs))
        check("transient failures retain last known metadata",
              state_after_failure["observed"]["test/model"]["license"] == "mit")
        check("transient failures do not create debounce state", state_after_failure["pending"] == {})
        check("transient failure logs a clear indeterminate warning",
              "indeterminate (http-429); keeping last known state" in runs[1][2])


def test_transient_failure_without_baseline_and_recovery() -> None:
    with tempfile.TemporaryDirectory() as d:
        runs = drive([transient("timeout")], Path(d))
        check("transient failure without baseline does not invent availability",
              "test/model" not in runs[0][1]["observed"])
        check("transient failure without baseline stays quiet", runs[0][0] == 0)
    with tempfile.TemporaryDirectory() as d:
        runs = drive([available("mit"), available("apache-2.0"), transient("http-503"), available("apache-2.0")], Path(d))
        check("transient interruption does not reset a real change debounce", runs[-1][0] == 2)
        check("recovery reports the persistent change", "confirmed change" in runs[-1][2])


def main() -> int:
    print("watch_upstream freshness contract:")
    test_source_coverage_contract()
    test_transport_failure_classification()
    test_state_migration_drops_retired_ids()
    test_stable_change_is_reported()
    test_alternating_drift_requires_identical_consecutive_observations()
    test_flap_and_unchanged_are_quiet()
    test_definitive_removal_debounces()
    test_transient_failure_preserves_baseline()
    test_transient_failure_without_baseline_and_recovery()
    if FAILURES:
        print(f"\n{len(FAILURES)} test(s) failed", file=sys.stderr)
        return 1
    print("\nall freshness tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
