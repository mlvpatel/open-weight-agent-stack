#!/usr/bin/env python3
"""Regression contracts for security workflows and release gates."""
from __future__ import annotations

import re
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
CODEQL = REPO / ".github" / "workflows" / "codeql.yml"
VALIDATE = REPO / ".github" / "workflows" / "validate.yml"
MANUAL = REPO / "MANUAL.md"
CODEQL_ACTION_SHA = "5595ccaf912efad79be6eef63a5619ff05969be3"
CHECKOUT_ACTION_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fail(message: str) -> None:
    raise AssertionError(message)


def links_to_host(document: str, host: str) -> bool:
    """True when the document links to exactly ``host`` (not a lookalike subdomain)."""
    return re.search(rf"https?://{re.escape(host)}\.?(?![\w.-])", document, re.I) is not None


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
    if "needs: [diagrams, invariants, generated, browser]" not in text:
        fail("Pages build must wait for every deterministic gate, including the browser smoke gate")
    if "permit unprivileged user namespaces for the browser sandbox" not in text:
        fail("browser job must prepare Ubuntu user namespaces without disabling Chromium sandbox")
    browser_start = text.index("  browser:")
    invariants_start = text.index("  invariants:")
    browser_job = text[browser_start:invariants_start]
    if "kernel.apparmor_restrict_unprivileged_userns=0" not in browser_job:
        fail("browser job must mirror the diagram job user-namespace preparation")


def job(text: str, name: str) -> str:
    """The body of one top-level job in a workflow file."""
    match = re.search(rf"^  {name}:\n(.*?)(?=^  [a-z][\w-]*:\n|\Z)", text, re.M | re.S)
    if not match:
        fail(f"workflow has no {name!r} job")
    return match.group(1)


def test_pages_deploy_is_split_dispatchable_and_offline_gated() -> None:
    text = read(VALIDATE)
    build, deploy = job(text, "build"), job(text, "deploy")
    # Upload and deploy in one job raced: deploy-pages saw no github-pages artifact.
    if "actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9" not in build:
        fail("the build job must upload the Pages artifact with the pinned action")
    if "actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128" not in deploy:
        fail("the deploy job must run the pinned deploy-pages action")
    if "upload-pages-artifact" in deploy or "deploy-pages" in build:
        fail("upload-pages-artifact and deploy-pages must run in separate jobs")
    # Re-running a failed attempt once left two github-pages artifacts in one run.
    if "name: ${{ steps.artifact.outputs.name }}" not in build or \
            "artifact_name: ${{ needs.build.outputs.artifact }}" not in deploy:
        fail("deploy must read the per-attempt artifact name from the build job's output")
    if "needs: build" not in deploy:
        fail("deploy must wait for the build job")
    if "workflow_dispatch" not in build:
        fail("a manual run on main must be able to redeploy, as SECURITY.md documents")
    if "pages: write" in build or "id-token: write" in build:
        fail("the build job must not hold Pages write or OIDC permissions")
    if "contents:" in deploy:
        fail("the deploy job needs no repository contents permission")
    # Clock- and network-dependent checks must not gate merges or the deploy.
    invariants = job(text, "invariants")
    if "check_invariants.py --only offline" not in invariants:
        fail("the required invariants job must run only the offline check group")
    if "check_invariants.py --only online" not in job(text, "drift"):
        fail("the scheduled drift job must run the online check group")
    if "links" in build:
        fail("an external link outage must not block the Pages deploy")
    report = job(text, "report")
    if "issues: write" not in report or "gh issue create" not in report:
        fail("scheduled failures must open or update a GitHub issue")


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
        # Bind to the single declared count rather than a spelled-out number, so this
        # assertion survives a change to the diagram count instead of becoming a
        # sixth place the number has to be edited.
        "EXPECTED_DIAGRAMS",
        "Mermaid diagrams",
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


def test_link_checker_uses_stable_primary_sources_without_accepting_failures() -> None:
    workflow = read(VALIDATE)
    accept_match = re.search(r"--accept\s+([0-9.,=]+)", workflow)
    if not accept_match:
        fail("link checking must declare its accepted HTTP statuses")
    accepted = accept_match.group(1)
    if ".." in accepted:
        fail("link checking must list exact HTTP statuses, not ranges that can hide 403 or 429")
    for rejected in ("403", "429"):
        if rejected in accepted.split(","):
            fail(f"link checking must not accept HTTP {rejected} as evidence that a source exists")

    manual = read(MANUAL)
    if links_to_host(manual, "docs.vllm.ai"):
        fail("vLLM evidence links must not use the hosted docs endpoint that rate-limits CI")
    if links_to_host(manual, "devin.ai"):
        fail("Devin evidence links must not use the marketing homepage that rate-limits CI")
    if "https://docs.devin.ai/" not in manual:
        fail("manual is missing official Devin documentation: https://docs.devin.ai/")
    precise_quantization_claim = (
        "vLLM supports quantized inference with AWQ, GPTQ/GPTQModel, and FP8 W8A8"
    )
    if precise_quantization_claim not in manual:
        fail("the vLLM quantization claim must use the terminology supported by its source")
    vllm_commit = "b2506d62aec7e6bccc5959b829221a7ae217abf3"
    for source_target in (
        "docs/features/quantization/README.md#L8-L57",
        "docs/serving/online_serving/openai_compatible_server.md#L1-L24",
    ):
        stable_url = f"https://github.com/vllm-project/vllm/blob/{vllm_commit}/{source_target}"
        if stable_url not in manual:
            fail(f"manual is missing immutable official vLLM evidence: {stable_url}")


if __name__ == "__main__":
    test_codeql_workflow_is_pinned_and_scans_repo_languages()
    test_browser_gate_blocks_deploy_when_it_fails()
    test_pages_deploy_is_split_dispatchable_and_offline_gated()
    test_browser_gate_is_hermetic_and_surfaces_mermaid_failures()
    test_link_checker_uses_stable_primary_sources_without_accepting_failures()
    print("security workflow contracts pass")
