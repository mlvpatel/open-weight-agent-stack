#!/usr/bin/env python3
"""Regression contracts for security workflows and release gates."""
from __future__ import annotations

import re
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CODEQL = REPO / ".github" / "workflows" / "codeql.yml"
VALIDATE = REPO / ".github" / "workflows" / "validate.yml"
CODEQL_ACTION_SHA = "5595ccaf912efad79be6eef63a5619ff05969be3"
CHECKOUT_ACTION_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"


def read(path: Path) -> str:
    return path.read_text()


def fail(message: str) -> None:
    raise AssertionError(message)


def test_codeql_workflow_is_pinned_and_scans_repo_languages() -> None:
    text = read(CODEQL)
    for expected in (
        "push:",
        "pull_request:",
        "schedule:",
        "workflow_dispatch:",
        "contents: read",
        "security-events: write",
        "language: javascript-typescript",
        "language: python",
        "build-mode: none",
        "queries: +security-extended,security-and-quality",
    ):
        if expected not in text:
            fail(f"CodeQL workflow is missing {expected!r}")

    uses = re.findall(r"uses:\s+github/codeql-action/(?:init|analyze)@([0-9a-f]{40})", text)
    if uses != [CODEQL_ACTION_SHA, CODEQL_ACTION_SHA]:
        fail("CodeQL init/analyze must both use the verified immutable v4.37.6 commit SHA")

    if "pull_request_target" in text:
        fail("CodeQL must not run untrusted fork code under pull_request_target")
    if "permissions: write-all" in text:
        fail("CodeQL must use least-privilege permissions")
    if f"actions/checkout@{CHECKOUT_ACTION_SHA}" not in text:
        fail("CodeQL checkout action must be pinned to the verified immutable commit")


def test_browser_gate_blocks_deploy_when_it_fails() -> None:
    text = read(VALIDATE)
    if "browser:" not in text or "npm run browser:check" not in text:
        fail("validate workflow must include the generated-site browser smoke gate")
    if "needs: [diagrams, html, links, invariants, generated, browser]" not in text:
        fail("Pages deploy must wait for the browser smoke gate")
    if "permit unprivileged user namespaces for the browser sandbox" not in text:
        fail("browser job must prepare Ubuntu user namespaces without disabling Chromium sandbox")
    browser_start = text.index("  browser:")
    invariants_start = text.index("  invariants:")
    browser_job = text[browser_start:invariants_start]
    if "kernel.apparmor_restrict_unprivileged_userns=0" not in browser_job:
        fail("browser job must mirror the diagram job user-namespace preparation")


def test_browser_gate_is_hermetic_and_surfaces_mermaid_failures() -> None:
    browser_test = read(REPO / "scripts" / "test_site_browser.cjs")
    template = read(REPO / "site" / "template.html")
    package = json.loads(read(REPO / "package.json"))
    for expected in (
        "http.createServer",
        "127.0.0.1",
        "/open-weight-agent-stack/",
        "--simulate-mermaid-failure",
        "failed requests",
        "all 18 Mermaid diagrams",
    ):
        if expected not in browser_test:
            fail(f"browser gate must include {expected!r}")
    for expected in (
        "startOnLoad: false",
        "await window.mermaid.run",
        "Mermaid failed to render diagrams",
        "textContent",
    ):
        if expected not in template:
            fail(f"template must make Mermaid failures visible using {expected!r}")
    browser_gate = package["scripts"].get("browser:check", "")
    if "browser:check:normal" not in browser_gate or "browser:check:failure" not in browser_gate:
        fail("browser:check must run both the normal and synthetic Mermaid-failure modes")
    if "--simulate-mermaid-failure" not in package["scripts"].get("browser:check:failure", ""):
        fail("the CI browser path must execute the synthetic Mermaid-failure assertion")


if __name__ == "__main__":
    test_codeql_workflow_is_pinned_and_scans_repo_languages()
    test_browser_gate_blocks_deploy_when_it_fails()
    test_browser_gate_is_hermetic_and_surfaces_mermaid_failures()
    print("security workflow contracts pass")
