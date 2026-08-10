#!/usr/bin/env python3
"""Detect upstream drift in the facts this manual publishes.

One mechanism, two instantiations: model metadata on Hugging Face, and the
build's own npm dependencies. Both are the same shape (poll, project, persist,
require repeated observation, then propose an edit), so they share an
implementation rather than existing as two bots.

Design decisions that matter:

* Nothing is proposed on a single observation. Upstream metadata flaps: a card
  gets edited and reverted, an API returns a partial record during a deploy. A
  change must be seen CONFIRMATIONS times in a row before it is reported, which
  is what stops the bot filing pull requests against noise.
* State lives in .github/upstream-state.json, committed, so the confirmation
  count survives across scheduled runs on ephemeral runners.
* The watcher only ever reports. It does not edit the manual. Writing the edit
  is the workflow's job, so a detection bug cannot silently rewrite content.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.manual import REPO  # noqa: E402

STATE_PATH = REPO / ".github" / "upstream-state.json"
CONFIRMATIONS = 2          # consecutive observations before reporting
TIMEOUT = 30

# Models whose licence, size, or existence the manual makes claims about.
WATCHED_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "moonshotai/Kimi-K3",
    "deepseek-ai/DeepSeek-V4-Pro",
    "deepseek-ai/DeepSeek-V4-Flash",
    "zai-org/GLM-5.2",
    "zai-org/GLM-4.5-Air",
    "Qwen/Qwen3.6-27B",
    "Qwen/Qwen3.5-9B",
    "Qwen/Qwen3-Coder-Next",
    "google/gemma-4-12B-it",
    "mistralai/Devstral-Small-2507",
    "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "microsoft/phi-4",
    "allenai/Olmo-3-1025-7B",
    "ibm-granite/granite-4.1-30b",
    "inclusionAI/Ling-3.0-flash",
    "tencent/Hy3",
    "MiniMaxAI/MiniMax-M2.7",
    "LiquidAI/LFM2.5-2.6B",
    "Kwaipilot/KAT-Coder-V2.5-Dev",
    "poolside/Laguna-S-2.1",
    "BAAI/bge-m3",
    "hexgrad/Kokoro-82M",
]


def fetch_json(url: str) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": "owas-freshness-watcher"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"__http_error__": e.code}
    except Exception:
        return None


def project_model(repo_id: str) -> dict | None:
    """Reduce a model card to only the fields the manual makes claims about.
    Everything else changes constantly and would produce noise."""
    data = fetch_json(f"https://huggingface.co/api/models/{repo_id}")
    if data is None:
        return None
    if "__http_error__" in data:
        return {"available": False, "http": data["__http_error__"]}
    card = data.get("cardData") or {}
    return {
        "available": True,
        "license": data.get("license") or card.get("license"),
        "license_name": card.get("license_name"),
        "gated": bool(data.get("gated")),
    }


def project_dependencies() -> dict:
    """The build's own pinned versions, from package.json."""
    pkg = json.loads((REPO / "package.json").read_text())
    return {name: ver for name, ver in sorted(pkg.get("devDependencies", {}).items())}


def latest_npm(name: str) -> str | None:
    data = fetch_json(f"https://registry.npmjs.org/{name}/latest")
    if not data or "__http_error__" in data:
        return None
    return data.get("version")


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"observed": {}, "pending": {}}


def diff(label: str, old: dict | None, new: dict | None) -> list[str]:
    if old is None or new is None:
        return []
    out = []
    for key in sorted(set(old) | set(new)):
        a, b = old.get(key), new.get(key)
        if a != b:
            out.append(f"{label}: {key} changed from {a!r} to {b!r}")
    return out


def main() -> int:
    state = load_state()
    observed_before: dict = state.get("observed", {})
    pending: dict = state.get("pending", {})

    observed_now: dict = {}
    findings: list[str] = []

    for repo_id in WATCHED_MODELS:
        current = project_model(repo_id)
        previous = observed_before.get(repo_id)

        if current is None:
            # Network failure is not drift. Carry the previous observation.
            observed_now[repo_id] = previous
            continue

        changes = diff(repo_id, previous, current)

        if not changes:
            # Stable, or flapped back to the old value. Either way, advance the
            # baseline and forget anything pending for this model.
            observed_now[repo_id] = current
            pending = {k: v for k, v in pending.items() if not k.startswith(f"{repo_id}: ")}
            continue

        # A change is present. The baseline must NOT advance while it is
        # unconfirmed, or the next run compares the new value against itself,
        # diff() returns nothing, and the counter freezes below CONFIRMATIONS
        # forever. Holding the old baseline is what makes the count accumulate.
        all_confirmed = True
        for c in changes:
            pending[c] = pending.get(c, 0) + 1
            if pending[c] >= CONFIRMATIONS:
                findings.append(f"- {c}\n  source: https://huggingface.co/{repo_id}")
            else:
                all_confirmed = False
        observed_now[repo_id] = current if all_confirmed else previous

    deps = project_dependencies()
    observed_now["__deps__"] = deps
    for name, pinned in deps.items():
        latest = latest_npm(name)
        if latest and latest != pinned.lstrip("^~"):
            key = f"dep:{name}:{latest}"
            pending[key] = pending.get(key, 0) + 1
            if pending[key] >= CONFIRMATIONS:
                findings.append(
                    f"- {name} is pinned at {pinned} but {latest} is published\n"
                    f"  source: https://www.npmjs.com/package/{name}"
                )

    # Anything that stopped being observed is no longer pending.
    still = {c for c in pending if any(c.startswith(p) for p in
             [f"{m}:" for m in WATCHED_MODELS] + ["dep:"])}
    pending = {k: v for k, v in pending.items() if k in still}

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(
        {"observed": observed_now, "pending": pending}, indent=2, sort_keys=True) + "\n")

    reachable = sum(1 for v in observed_now.values() if isinstance(v, dict) and v.get("available"))
    print(f"checked {len(WATCHED_MODELS)} models ({reachable} reachable) "
          f"and {len(deps)} pinned dependencies")

    if not findings:
        print("no confirmed drift")
        return 0

    report = "\n".join(findings)
    print(f"\n{len(findings)} confirmed change(s):\n{report}")
    Path("drift-report.md").write_text(
        "The upstream watcher observed these changes on two consecutive runs, "
        "so they are not transient.\n\n"
        f"{report}\n\n"
        "Each entry links the primary source. Verify against it before merging: "
        "a licence change is legal guidance by implication.\n"
    )
    return 2   # 2 means drift found, distinct from 1 for failure


if __name__ == "__main__":
    raise SystemExit(main())
