#!/usr/bin/env python3
"""Regression contracts for security workflows and release gates."""
from __future__ import annotations

import re
import json
from pathlib import Path
from urllib.parse import urlsplit


REPO = Path(__file__).resolve().parents[1]
CODEQL = REPO / ".github" / "workflows" / "codeql.yml"
VALIDATE = REPO / ".github" / "workflows" / "validate.yml"
MANUAL = REPO / "MANUAL.md"
CODEQL_ACTION_SHA = "5595ccaf912efad79be6eef63a5619ff05969be3"
CHECKOUT_ACTION_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"


def read(path: Path) -> str:
    return path.read_text()


def fail(message: str) -> None:
    raise AssertionError(message)


def accepts_status(specification: str, status: int) -> bool:
    """Return whether a lychee status specification accepts ``status``."""
    for token in (part.strip() for part in specification.split(",")):
        if "..=" in token:
            start, end = token.split("..=", 1)
            if (not start or status >= int(start)) and (not end or status <= int(end)):
                return True
        elif ".." in token:
            start, end = token.split("..", 1)
            if (not start or status >= int(start)) and (not end or status < int(end)):
                return True
        elif token and status == int(token):
            return True
    return False


def contains_markdown_host(document: str, target_host: str) -> bool:
    """Return whether Markdown text contains an HTTP(S) URL for an exact host."""
    normalized_target = target_host.rstrip(".").lower()
    targets = re.findall(r"https?://[^\s<>\"']+", document, flags=re.IGNORECASE)
    for target in targets:
        candidate = target.rstrip(".,;:!?)]}")
        try:
            hostname = urlsplit(candidate).hostname
        except ValueError:
            continue
        if hostname is not None and hostname.rstrip(".").lower() == normalized_target:
            return True
    return False


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
    for rejected in (403, 429):
        if accepts_status(accept_match.group(1), rejected):
            fail(f"link checking must not accept HTTP {rejected} as evidence that a source exists")

    manual = read(MANUAL)
    if contains_markdown_host(manual, "docs.vllm.ai"):
        fail("vLLM evidence links must not use the hosted docs endpoint that rate-limits CI")
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


def test_status_acceptance_parser_covers_exact_codes_and_ranges() -> None:
    for specification in ("403", "400..500", "..=429", "429.."):
        if not accepts_status(specification, 403 if "403" in specification else 429):
            fail(f"status parser failed to recognize {specification!r}")
    if accepts_status("200,201,202,204,206,301,302,308", 403):
        fail("status parser incorrectly accepted HTTP 403")


def test_markdown_host_matching_is_exact() -> None:
    lookalike = "[lookalike](https://docs.vllm.ai.example.invalid/path)"
    if contains_markdown_host(lookalike, "docs.vllm.ai"):
        fail("host matching must not treat a lookalike subdomain as docs.vllm.ai")
    valid_forms = (
        "[inline](https://docs.vllm.ai/en/latest/)",
        "[titled](<HTTPS://DOCS.VLLM.AI./en/latest/> \"vLLM docs\")",
        "[reference]: https://docs.vllm.ai/en/latest/ 'vLLM docs'",
        "<https://docs.vllm.ai/en/latest/>",
    )
    for target in valid_forms:
        if not contains_markdown_host(target, "docs.vllm.ai"):
            fail(f"host matching must recognize exact target form: {target}")


if __name__ == "__main__":
    test_codeql_workflow_is_pinned_and_scans_repo_languages()
    test_browser_gate_blocks_deploy_when_it_fails()
    test_browser_gate_is_hermetic_and_surfaces_mermaid_failures()
    test_link_checker_uses_stable_primary_sources_without_accepting_failures()
    test_status_acceptance_parser_covers_exact_codes_and_ranges()
    test_markdown_host_matching_is_exact()
    print("security workflow contracts pass")
