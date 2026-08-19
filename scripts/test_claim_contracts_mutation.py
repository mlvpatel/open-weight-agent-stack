#!/usr/bin/env python3
"""Mutation harness for scripts/test_claim_contracts.py.

Passing pinned checks is not proof they are load-bearing: a check with a typo'd
file key, a phrase that is ANDed with an always-true clause, or a substring
that no longer appears anywhere relevant would still print "pass" and nobody
would notice. This script proves each check is load-bearing (would actually
turn RED on a real regression) by mutating an in-memory copy of the exact
source text each check reads, re-running that check's own boolean expression
against the mutated copy, and asserting it now evaluates to False.

Method
------
1. Parse scripts/test_claim_contracts.py with `ast` and pull out the literal
   `checks = [...]` list from inside `main()`, without executing `main()`
   (so nothing is printed and the real files are read exactly once, the same
   way the real script reads them).
2. For every check, walk its boolean-expression AST and collect every
   "assertion" it depends on:
     - `includes(file, phrase)` / `excludes(file, phrase)` calls, and
     - the raw `phrase in TEXT[file]` / `phrase not in TEXT[file]` form used
       by one check that does not go through the helpers.
   A `TEXT[file].replace(...)` comparator (used by exactly one check) is not
   a read of live file content, it is a self-contained tautology, so it is
   recorded separately as non-mutable and reported, not mutation-tested.
3. For each assertion, in isolation, build a fresh in-memory copy of the
   original TEXT dict, mutate only the one file entry it reads (strip the
   phrase for a positive/includes assertion, append the phrase for a
   negative/excludes assertion), then `eval` the *check's full expression*
   (not just the one assertion) against the mutated dict, using local
   `includes`/`excludes`/`TEXT` bound to the mutated copy. Assert the whole
   check now evaluates to False.
4. A check is CONFIRMED load-bearing only if every one of its assertions,
   mutated one at a time, flips the check to False. If any assertion does
   not flip the result, that check is SUSPECT: it is pinned in name only.

Mutation happens entirely on in-memory string copies. The files on disk
(MANUAL.md, docs/MODELS.md, etc.) are read once and never written back to,
which matters here because other lanes may have these same files open
concurrently.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTRACTS_PATH = REPO / "scripts" / "test_claim_contracts.py"


def load_original_text() -> dict[str, str]:
    """Read the same files, the same way, that test_claim_contracts.py reads them."""
    namespace: dict[str, object] = {"__name__": "_claim_contracts_source", "__file__": str(CONTRACTS_PATH)}
    source = CONTRACTS_PATH.read_text(encoding="utf-8")
    module_ast = ast.parse(source, filename=str(CONTRACTS_PATH))
    # Execute every top-level statement except the `if __name__ == "__main__":`
    # guard, so FILES/TEXT are built exactly as the real script builds them,
    # but main() is never invoked (no printing, no exit code).
    top_level = [
        node
        for node in module_ast.body
        if not (isinstance(node, ast.If) and _is_main_guard(node))
    ]
    exec(compile(ast.Module(body=top_level, type_ignores=[]), str(CONTRACTS_PATH), "exec"), namespace)
    return dict(namespace["TEXT"])  # type: ignore[arg-type]


def _is_main_guard(node: ast.If) -> bool:
    test = node.test
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
    )


def find_checks_list(source: str) -> list[tuple[str, ast.expr]]:
    """Return [(check_name, expr_ast), ...] from the literal `checks = [...]` in main()."""
    module_ast = ast.parse(source, filename=str(CONTRACTS_PATH))
    main_def = next(
        node for node in ast.walk(module_ast)
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    checks_assign = next(
        node for node in ast.walk(main_def)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "checks"
    )
    assert isinstance(checks_assign.value, ast.List)
    result = []
    for elt in checks_assign.value.elts:
        assert isinstance(elt, ast.Tuple) and len(elt.elts) == 2
        name_node, expr_node = elt.elts
        assert isinstance(name_node, ast.Constant) and isinstance(name_node.value, str)
        result.append((name_node.value, expr_node))
    return result


class Assertion:
    __slots__ = ("kind", "file", "phrase", "positive", "node")

    def __init__(self, kind: str, file: str, phrase: str, positive: bool, node: ast.AST):
        self.kind = kind          # "includes_call" | "excludes_call" | "raw_compare"
        self.file = file
        self.phrase = phrase
        self.positive = positive  # True: check requires phrase PRESENT. False: requires ABSENT.
        self.node = node

    def label(self) -> str:
        verb = "includes" if self.positive else "excludes"
        short = self.phrase if len(self.phrase) <= 60 else self.phrase[:57] + "..."
        return f'{verb}("{self.file}", "{short}")'


def _is_plain_text_subscript(node: ast.expr) -> str | None:
    """If node is exactly TEXT["file"], return "file", else None."""
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "TEXT"
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    ):
        return node.slice.value
    return None


def collect_assertions(expr: ast.expr) -> tuple[list[Assertion], list[str]]:
    """Walk a check's expression and collect mutable assertions plus notes on
    non-mutable (tautological) comparisons found along the way."""
    assertions: list[Assertion] = []
    notes: list[str] = []
    for node in ast.walk(expr):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("includes", "excludes"):
            args = node.args
            if len(args) == 2 and all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in args):
                file_arg, phrase_arg = args[0].value, args[1].value
                positive = node.func.id == "includes"
                assertions.append(Assertion(f"{node.func.id}_call", file_arg, phrase_arg, positive, node))
            else:
                notes.append(f"non-literal args to {node.func.id}(...) could not be mutation-tested")
        elif isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            if isinstance(op, (ast.In, ast.NotIn)) and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                comparator = node.comparators[0]
                file_key = _is_plain_text_subscript(comparator)
                if file_key is not None:
                    assertions.append(
                        Assertion("raw_compare", file_key, node.left.value, isinstance(op, ast.In), node)
                    )
                else:
                    notes.append(
                        f'"{node.left.value[:40]}..." compared against a derived expression, '
                        "not a direct file read, so it cannot be mutated by editing source text "
                        "(likely a self-contained tautology)"
                    )
    return assertions, notes


def eval_expr(expr: ast.expr, text_dict: dict[str, str]) -> bool:
    includes = lambda file, phrase: phrase in text_dict[file]  # noqa: E731
    excludes = lambda file, phrase: phrase not in text_dict[file]  # noqa: E731
    expr_module = ast.Expression(body=expr)
    ast.fix_missing_locations(expr_module)
    code = compile(expr_module, "<check-expr>", "eval")
    return bool(eval(code, {"includes": includes, "excludes": excludes, "TEXT": text_dict, "__builtins__": {}}))


def mutate(original: dict[str, str], assertion: Assertion) -> dict[str, str]:
    mutated = dict(original)
    if assertion.positive:
        # Requires the phrase present. Delete every occurrence.
        mutated[assertion.file] = mutated[assertion.file].replace(assertion.phrase, "")
    else:
        # Requires the phrase absent. Insert it.
        mutated[assertion.file] = mutated[assertion.file] + " " + assertion.phrase
    return mutated


def main() -> int:
    source = CONTRACTS_PATH.read_text(encoding="utf-8")
    original_text = load_original_text()
    checks = find_checks_list(source)

    print(f"mutation-testing {len(checks)} pinned check(s) in {CONTRACTS_PATH.relative_to(REPO)}:\n")

    confirmed = 0
    suspect_checks: list[tuple[str, list[Assertion]]] = []
    total_assertions = 0
    total_notes: list[str] = []

    for name, expr in checks:
        # Sanity: the check must currently pass against the real, unmutated text.
        baseline = eval_expr(expr, original_text)
        if not baseline:
            print(f"  ERROR  {name}: check does not currently pass against real files, skipping mutation")
            suspect_checks.append((name, []))
            continue

        assertions, notes = collect_assertions(expr)
        total_notes.extend(f"{name}: {n}" for n in notes)
        total_assertions += len(assertions)

        if not assertions:
            print(f"  ERROR  {name}: no mutation-testable includes()/excludes() assertion found")
            suspect_checks.append((name, []))
            continue

        failing_assertions: list[Assertion] = []
        for assertion in assertions:
            mutated_text = mutate(original_text, assertion)
            # Sanity: the mutation must actually flip the single assertion in isolation.
            isolated_before = assertion.phrase in original_text[assertion.file]
            isolated_after = assertion.phrase in mutated_text[assertion.file]
            if isolated_before == isolated_after:
                print(f"  ERROR  {name}: mutation of {assertion.label()} did not change file content")
                failing_assertions.append(assertion)
                continue
            result = eval_expr(expr, mutated_text)
            if result:
                # The whole check still reports True even though this one
                # assertion's target text was mutated away/in. That assertion
                # is not load-bearing for this check's outcome.
                failing_assertions.append(assertion)

        if failing_assertions:
            print(f"  SUSPECT  {name}")
            for a in failing_assertions:
                print(f"           does not gate on {a.label()}")
            suspect_checks.append((name, failing_assertions))
        else:
            print(f"  confirmed  {name}  ({len(assertions)} assertion(s), all load-bearing)")
            confirmed += 1

    print(f"\n{confirmed}/{len(checks)} checks confirmed load-bearing across {total_assertions} mutated assertions")

    if total_notes:
        print("\nnotes (non-mutable comparisons found, not counted as failures):")
        for n in total_notes:
            print(f"  - {n}")

    if suspect_checks:
        print(f"\n{len(suspect_checks)} check(s) are SUSPECT (mutation did not force a failure):", file=sys.stderr)
        for name, _ in suspect_checks:
            print(f"  - {name}", file=sys.stderr)
        return 1

    print("\nall pinned checks are confirmed load-bearing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
