# Security policy

This repository publishes a documentation manual and the small toolchain that builds it. It ships no runtime software that you would deploy or execute in production, so the realistic threats are narrower than a generic software project, and this policy tries to be honest about which ones they are rather than copying a template.

## What counts as a vulnerability here

**In scope:**

- **Build and CI compromise.** Anything that lets a pull request, a dependency, or a crafted diagram execute code in this repository's workflows, escalate the permissions those workflows hold, or exfiltrate a token.
- **Malicious content reaching the published site.** Anything that lets markdown in `MANUAL.md`, or a crafted contribution, produce executable script, an injected attribute, or a `javascript:` URL on <https://mlvpatel.github.io/open-weight-agent-stack/>.
- **Supply-chain compromise of the build.** A dependency, pinned Action, or the vendored browser bundle in `site/` carrying a known vulnerability that affects the build or the published page.
- **Secret exposure.** Any credential, token, or private data committed to the repository or reachable in its history.

**Out of scope:**

- **A factual error in the manual is a correction, not a vulnerability.** A wrong licence, a stale version floor, or a benchmark attributed to the wrong model is exactly the kind of defect this project wants reported, but it belongs in an issue or pull request with a primary source. See [CONTRIBUTING.md](CONTRIBUTING.md).
- **Vulnerabilities in the tools the manual describes.** If vLLM, Ollama, or a model runtime has a security issue, report it to that project. This manual only documents them.
- **Advice you disagree with.** Architecture recommendations are editorial judgement, argued in the text and open to challenge in an issue.
- **Missing response headers on GitHub Pages.** Pages cannot set custom response headers at all, so no Content-Security-Policy, `X-Frame-Options`, or reporting header can be delivered. `docs/VERIFICATION.md` records this limit. It is a platform constraint, not an oversight.

## Reporting

Use **[private vulnerability reporting](https://github.com/mlvpatel/open-weight-agent-stack/security/advisories/new)**, which is enabled on this repository. That keeps the report private until a fix is available and gives us a place to coordinate.

Please do not open a public issue for anything in the in-scope list above.

Include what you would want to receive: what you did, what happened, and why it matters. A proof of concept helps enormously, particularly for content injection, where the difference between "this could theoretically escape escaping" and "here is markdown that produces a script tag" is the whole report.

## What to expect

This repository is maintained by one person, so response times are honest rather than aspirational:

| Stage | Target |
|---|---|
| Acknowledgement | Within 7 days |
| Initial assessment | Within 14 days |
| Fix or documented decision not to fix | Depends on severity; you will be told which |

If a report is valid and you would like credit, say so and you will be named in the release notes and the advisory.

## What is already in place

So you know what has been done and can look for gaps in it rather than reporting what already exists:

- **Secret scanning with push protection**, so a credential cannot be pushed to this repository.
- **Dependabot alerts and security updates** for npm dependencies and GitHub Actions.
- **All Actions pinned to commit SHAs**, not movable tags, so an upstream tag repoint cannot silently change what runs.
- **Dependencies pinned by lockfile** with a committed CycloneDX SBOM.
- **A read-only default workflow token**, with write permissions granted per job only where needed.
- **Branch protection on `main`** requiring five status checks to pass. Note that administrator enforcement is deliberately off, because with a single maintainer, enabling it creates a lockout risk that is worse than the threat it mitigates.
- **Reproducible builds.** Diagram rendering is byte-identical across runs, and CI fails when a committed derived file differs from a fresh build, so an unexplained change to published output is visible. That now includes `site/mermaid.min.js`, the vendored browser bundle, which is checked byte-for-byte against the mermaid release pinned in the lockfile.
- **A Content-Security-Policy is served** as a meta element, since Pages cannot send headers. It denies everything by default, pins the single inline script by hash, and blocks external connections. `frame-ancestors`, `report-uri` and `sandbox` are ignored in meta form per the spec, so clickjacking protection and violation reporting remain unavailable.
- **The renderer is tested against injection.** `scripts/test_render_security.py` asserts that markdown cannot produce an event handler, an executable URL scheme, or any element outside a small allow-list. It exists because an earlier version of the renderer was vulnerable to exactly that.

## Diagram rendering runs sandboxed

Diagram rendering drives a headless Chromium over content taken from `MANUAL.md`, and pull requests from forks can change that content. The Chromium sandbox is therefore **enabled**: `scripts/puppeteer.json` passes no disabling flags, and CI permits unprivileged user namespaces so the sandbox can initialise on the runner.

An earlier version disabled the sandbox and justified it by claiming the renderer only ever saw repository-controlled sources. That justification was false, because the workflow also runs on pull requests. Enabling the sandbox was the correct fix rather than rewording the rationale.

## Updating the vendored browser bundle

When mermaid publishes a security fix, the published site needs the new bundle, not just the new lockfile entry. CI enforces that the two agree, so the sequence is:

```bash
npm install                                              # or merge the Dependabot pull request
cp node_modules/mermaid/dist/mermaid.min.js site/mermaid.min.js
npm run sbom
```

Skipping the copy turns the build red rather than silently shipping the old bundle.
