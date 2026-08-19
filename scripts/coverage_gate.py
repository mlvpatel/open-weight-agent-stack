#!/usr/bin/env python3
"""Measure executed Python lines and branch transitions in production scripts.

This uses only the standard library, so the coverage gate has no unpinned
package-manager dependency. It executes the repository regression suite
in-process under one combined ``sys.settrace`` pass, measures real trace
events, and reports every production module. Test modules, generated
assets, and this measurement harness itself are excluded; all functional
Python scripts and library modules are included.

Two independent measurements are reported:

* Line coverage (gated): the fraction of executable source lines visited at
  least once. This is the pre-existing measurement and it is still what the
  aggregate 80% and per-file 40% thresholds enforce.
* Branch-transition coverage (measured only, additive): for every ``if``,
  ``for``, ``while``, ``try`` and short-circuiting ``and``/``or`` in a
  module, the set of statically-possible (line, next-line) control-flow
  edges that branch point can produce, intersected with the edges actually
  observed during the same regression run. This exists because line
  coverage alone can show every line as "visited" while an entire branch of
  conditional logic (an ``else``, an exception handler, a loop that never
  iterates) never executes -- state-machine-heavy code such as
  ``observe_model()`` in ``scripts/watch_upstream.py`` is exactly the shape
  this is meant to surface. No threshold is enforced on this number yet;
  it is reported so it is visible rather than silently absent.

Run: python3 scripts/coverage_gate.py
"""
from __future__ import annotations

import ast
import dis
import os
import runpy
import sys
import types
from pathlib import Path
from types import CodeType


REPO = Path(__file__).resolve().parent.parent
MINIMUM_PERCENT = 80.0
PER_FILE_PERCENT = 40.0


def regression_scripts(repo: Path) -> tuple[str, ...]:
    """Every scripts/test_*.py module except this harness's own test file."""
    return tuple(sorted(
        path.name for path in (repo / "scripts").glob("test_*.py")
        if path.name != "test_coverage_gate.py"
    ))


TEST_SCRIPTS = regression_scripts(REPO)


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
    return code_lines(compile(path.read_text(encoding="utf-8"), str(path), "exec"))


def run_script(path: Path) -> int:
    """Run a standalone regression script in-process and return its exit code."""
    old_argv = sys.argv[:]
    preserved = {name: module for name, module in sys.modules.items()
                 if name in {"watch_upstream", "check_invariants", "build_site"}}
    try:
        sys.argv = [str(path)]
        runpy.run_path(str(path), run_name="__main__")
    except SystemExit as exit_status:
        return int(exit_status.code or 0)
    finally:
        sys.argv = old_argv
        for name, module in preserved.items():
            sys.modules[name] = module
        for name in list(sys.modules):
            if name.startswith("watch_upstream") and name not in preserved:
                sys.modules.pop(name, None)
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


def line_coverage(counts: dict[tuple[str, int], int], targets: list[Path]) -> dict[Path, tuple[int, int]]:
    """Return visited and executable line totals for each production module."""
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


# ---------------------------------------------------------------------------
# Branch-transition coverage (additive; see module docstring)
#
# Static side: walk each module's AST and, for every If/For/While/Try node
# and every BoolOp, record the (line, next-line) edges that branch point can
# produce. Runtime side: trace the same regression run with a line-event
# tracer and record the (prev_line, current_line) pairs actually observed.
# The reported fraction is the intersection over the static set.
# ---------------------------------------------------------------------------

_FRAME_BOUNDARY = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)


class _BlockSlot:
    """Where a statement sits inside its immediate parent's statement list."""

    __slots__ = ("parent", "field", "index")

    def __init__(self, parent: ast.AST, field: str, index: int) -> None:
        self.parent = parent
        self.field = field
        self.index = index


def _build_block_positions(tree: ast.AST) -> tuple[dict[int, _BlockSlot], dict[int, ast.Try]]:
    """Map every statement to its slot in an enclosing body, and every
    ``except`` handler to the ``Try`` that owns it (handlers live in
    ``Try.handlers``, not in a body/orelse/finalbody list, so they need
    their own lookup to redirect a "successor of the last statement in this
    handler" query to the owning ``Try``'s own successor).
    """
    positions: dict[int, _BlockSlot] = {}
    handler_owner: dict[int, ast.Try] = {}
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            statements = getattr(node, field, None)
            if not isinstance(statements, list):
                continue
            for index, statement in enumerate(statements):
                if isinstance(statement, ast.stmt):
                    positions[id(statement)] = _BlockSlot(node, field, index)
        if isinstance(node, ast.Try):
            for handler in node.handlers:
                handler_owner[id(handler)] = node
    return positions, handler_owner


def _successor_line(
    node: ast.stmt,
    positions: dict[int, _BlockSlot],
    handler_owner: dict[int, ast.Try],
) -> int | None:
    """First line reached immediately after ``node`` under normal control
    flow, or ``None`` when that would fall off a function/class/module.

    That ``None`` case (a frame return rather than a same-frame line event)
    is not something line-level tracing can ever observe as a transition
    target, so it is left out of the static set entirely rather than kept
    in as a permanently-unreachable entry.
    """
    current: ast.AST = node
    while True:
        slot = positions.get(id(current))
        if slot is None:
            owner = handler_owner.get(id(current))
            if owner is None:
                return None
            current = owner
            continue
        statements = getattr(slot.parent, slot.field)
        if slot.index + 1 < len(statements):
            return statements[slot.index + 1].lineno
        if isinstance(slot.parent, _FRAME_BOUNDARY):
            return None
        current = slot.parent


def _add_branch_edges(
    node: ast.If | ast.For | ast.AsyncFor | ast.While,
    positions: dict[int, _BlockSlot],
    handler_owner: dict[int, ast.Try],
    transitions: set[tuple[int, int]],
) -> None:
    """Edges for If/For/While: enter the body, or take the other path
    (``elif``/``else``/loop-``else`` when present, otherwise whatever
    statement follows the whole construct).
    """
    branch_line = node.lineno
    if node.body:
        transitions.add((branch_line, node.body[0].lineno))
    if node.orelse:
        transitions.add((branch_line, node.orelse[0].lineno))
        return
    successor = _successor_line(node, positions, handler_owner)
    if successor is not None:
        transitions.add((branch_line, successor))


def _add_try_edges(node: ast.Try, transitions: set[tuple[int, int]]) -> None:
    """Edges for Try: the normal body path, each except handler, and the
    ``else`` clause (which runs only when the body raised nothing).
    """
    branch_line = node.lineno
    if node.body:
        transitions.add((branch_line, node.body[0].lineno))
    for handler in node.handlers:
        if handler.body:
            transitions.add((branch_line, handler.body[0].lineno))
    if node.orelse:
        transitions.add((branch_line, node.orelse[0].lineno))


def _add_boolop_edges(node: ast.BoolOp, transitions: set[tuple[int, int]]) -> None:
    """Inter-operand transitions for ``and``/``or`` short-circuiting.

    Only transitions between operands on *different* source lines are
    representable: line-event tracing fires once per distinct source line,
    so two operands sharing one physical line (the common case, e.g.
    ``if a and b:``) cannot be told apart by this method. Those pairs are
    skipped rather than counted as a branch that can never be exercised.
    """
    lines = [value.lineno for value in node.values]
    for left, right in zip(lines, lines[1:]):
        if left != right:
            transitions.add((left, right))


def static_branch_transitions(path: Path) -> set[tuple[int, int]]:
    """Every statically-possible (line, next-line) branch transition in a module."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    positions, handler_owner = _build_block_positions(tree)
    transitions: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While)):
            _add_branch_edges(node, positions, handler_owner, transitions)
        elif isinstance(node, ast.Try):
            _add_try_edges(node, transitions)
        elif isinstance(node, ast.BoolOp):
            _add_boolop_edges(node, transitions)
    return transitions


class TransitionTracer:
    """Single-pass ``sys.settrace`` tracer: per-line visit counts (the same
    shape ``line_coverage`` already consumed from ``trace.CoverageResults``)
    plus, per source file, the set of (prev_line, current_line) transitions
    actually observed. Transitions are tracked per call-frame so a return
    into a caller is never mistaken for a same-frame fall-through.
    """

    def __init__(self, ignore_dirs: tuple[str, ...] = ()) -> None:
        self._ignore_dirs = tuple(os.path.realpath(d) for d in ignore_dirs if d)
        self.counts: dict[tuple[str, int], int] = {}
        self.transitions: dict[str, set[tuple[int, int]]] = {}
        self._previous_line: dict[types.FrameType, int] = {}

    def _ignored(self, filename: str) -> bool:
        real = os.path.realpath(filename)
        return any(real == prefix or real.startswith(prefix + os.sep) for prefix in self._ignore_dirs)

    def _local_trace(self, frame: types.FrameType, event: str, arg: object):
        if event == "line":
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            self.counts[(filename, lineno)] = self.counts.get((filename, lineno), 0) + 1
            previous = self._previous_line.get(frame)
            if previous is not None:
                self.transitions.setdefault(filename, set()).add((previous, lineno))
            self._previous_line[frame] = lineno
            return self._local_trace
        if event in ("return", "exception"):
            self._previous_line.pop(frame, None)
            return None
        return self._local_trace

    def _global_trace(self, frame: types.FrameType, event: str, arg: object):
        if event != "call" or self._ignored(frame.f_code.co_filename):
            return None
        return self._local_trace

    def runfunc(self, func, *args, **kwargs):
        previous_tracer = sys.gettrace()
        sys.settrace(self._global_trace)
        try:
            return func(*args, **kwargs)
        finally:
            sys.settrace(previous_tracer)


def branch_coverage(
    static: dict[Path, set[tuple[int, int]]],
    observed: dict[str, set[tuple[int, int]]],
) -> dict[Path, tuple[int, int]]:
    """Exercised vs. statically-possible branch-transition counts per module."""
    result: dict[Path, tuple[int, int]] = {}
    for path, possible in static.items():
        exercised = possible & observed.get(str(path), set())
        result[path] = (len(exercised), len(possible))
    return result


def main() -> int:
    targets = production_modules(REPO)
    tracer = TransitionTracer(ignore_dirs=(sys.prefix, sys.base_prefix))
    status = tracer.runfunc(run_regressions, REPO)
    if status:
        return status

    coverage = line_coverage(tracer.counts, targets)
    print("Python production-line coverage:")
    for path, (visited, total) in coverage.items():
        percent = (visited * 100 / total) if total else 100.0
        print(f"  {path.relative_to(REPO)}: {visited}/{total} ({percent:.1f}%)")
    visited = sum(item[0] for item in coverage.values())
    total = sum(item[1] for item in coverage.values())
    percent = visited * 100 / total if total else 0.0
    print(f"Aggregate: {visited}/{total} ({percent:.1f}%), required >= {MINIMUM_PERCENT:.1f}%")

    branch_static = {path: static_branch_transitions(path) for path in targets}
    branches = branch_coverage(branch_static, tracer.transitions)
    print("Python branch-transition coverage (measured only, no threshold enforced):")
    for path, (exercised, possible) in branches.items():
        branch_percent = (exercised * 100 / possible) if possible else 100.0
        print(f"  {path.relative_to(REPO)}: {exercised}/{possible} ({branch_percent:.1f}%)")
    branch_exercised = sum(item[0] for item in branches.values())
    branch_possible = sum(item[1] for item in branches.values())
    branch_percent_total = (branch_exercised * 100 / branch_possible) if branch_possible else 100.0
    print(
        f"Aggregate branch-transition coverage: {branch_exercised}/{branch_possible} "
        f"({branch_percent_total:.1f}%)"
    )

    if not meets_threshold(coverage, MINIMUM_PERCENT):
        print("coverage gate failed", file=sys.stderr)
        return 1
    weak = []
    for path, (visited, total) in coverage.items():
        percent = (visited * 100 / total) if total else 100.0
        if total and percent < PER_FILE_PERCENT:
            weak.append(f"{path.relative_to(REPO)} {percent:.1f}%")
    if weak:
        print("per-file coverage floor failed: " + "; ".join(weak), file=sys.stderr)
        return 1
    print("coverage gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
