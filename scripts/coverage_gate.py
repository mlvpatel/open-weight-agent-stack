#!/usr/bin/env python3
"""Measure executed Python lines in the repository's production scripts.

This uses Python's standard-library ``trace`` module, so the coverage gate has
no unpinned package-manager dependency.  It executes the repository regression
suite in-process, measures real trace events, and reports every production
module.  Test modules, generated assets, and this measurement harness itself
are excluded; all functional Python scripts and library modules are included.

Run: python3 scripts/coverage_gate.py
"""
from __future__ import annotations

import dis
import os
import runpy
import sys
import trace
from pathlib import Path
from types import CodeType


REPO = Path(__file__).resolve().parent.parent
MINIMUM_PERCENT = 80.0
TEST_SCRIPTS = (
    "test_claim_contracts.py",
    "test_memory_catalogue.py",
    "test_render_security.py",
    "test_site_links.py",
    "test_watch_upstream.py",
    "test_sbom.py",
    "test_production_paths.py",
)


def production_modules(repo: Path) -> list[Path]:
    """Return every repository-owned functional Python module to measure."""
    scripts = repo / "scripts"
    excluded = {"coverage_gate.py"}
    return sorted(
        path.resolve()
        for path in scripts.rglob("*.py")
        if not path.name.startswith("test_")
        and path.name not in excluded
        and path.name != "__init__.py"
    )


def code_lines(code: CodeType) -> set[int]:
    """Collect executable source lines from a code object and nested functions."""
    lines = {line for _offset, line in dis.findlinestarts(code)}
    for constant in code.co_consts:
        if isinstance(constant, CodeType):
            lines.update(code_lines(constant))
    return lines


def executable_lines(path: Path) -> set[int]:
    return code_lines(compile(path.read_text(), str(path), "exec"))


def run_script(path: Path) -> int:
    """Run a standalone regression script in-process and return its exit code."""
    old_argv = sys.argv[:]
    try:
        sys.argv = [str(path)]
        runpy.run_path(str(path), run_name="__main__")
    except SystemExit as exit_status:
        return int(exit_status.code or 0)
    finally:
        sys.argv = old_argv
    return 0


def run_regressions(repo: Path) -> int:
    """Execute every offline regression script while tracing actual execution."""
    failures = []
    cwd = Path.cwd()
    try:
        os.chdir(repo)
        for name in TEST_SCRIPTS:
            code = run_script(repo / "scripts" / name)
            if code:
                failures.append(f"{name} exited {code}")
    finally:
        os.chdir(cwd)
    if failures:
        for failure in failures:
            print(f"coverage prerequisite failed: {failure}", file=sys.stderr)
        return 1
    return 0


def line_coverage(results: trace.CoverageResults, targets: list[Path]) -> dict[Path, tuple[int, int]]:
    """Return visited and executable line totals for each production module."""
    counts = results.counts
    output: dict[Path, tuple[int, int]] = {}
    for path in targets:
        executable = executable_lines(path)
        visited = {line for line in executable if counts.get((str(path), line), 0) > 0}
        output[path] = (len(visited), len(executable))
    return output


def meets_threshold(coverage: dict[Path, tuple[int, int]], threshold: float) -> bool:
    covered = sum(visited for visited, _total in coverage.values())
    total = sum(total for _visited, total in coverage.values())
    return bool(total) and (covered * 100 / total) >= threshold


def main() -> int:
    targets = production_modules(REPO)
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.prefix, sys.base_prefix])
    status = tracer.runfunc(run_regressions, REPO)
    if status:
        return status
    coverage = line_coverage(tracer.results(), targets)
    print("Python production-line coverage:")
    for path, (visited, total) in coverage.items():
        percent = (visited * 100 / total) if total else 100.0
        print(f"  {path.relative_to(REPO)}: {visited}/{total} ({percent:.1f}%)")
    visited = sum(item[0] for item in coverage.values())
    total = sum(item[1] for item in coverage.values())
    percent = visited * 100 / total if total else 0.0
    print(f"Aggregate: {visited}/{total} ({percent:.1f}%), required >= {MINIMUM_PERCENT:.1f}%")
    if not meets_threshold(coverage, MINIMUM_PERCENT):
        print("coverage gate failed", file=sys.stderr)
        return 1
    print("coverage gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
