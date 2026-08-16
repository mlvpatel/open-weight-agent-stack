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
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.manual import REPO  # noqa: E402

STATE_PATH = REPO / ".github" / "upstream-state.json"
SOURCES_PATH = REPO / ".github" / "freshness-sources.json"
CHANGE_CONFIRMATIONS = 2   # plus the stable baseline = three observations
TIMEOUT = 30
MODEL_URL = re.compile(
    r"https://huggingface\.co/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?=[/?#)]|$)"
)


def load_model_coverage(path: Path = SOURCES_PATH) -> dict[str, Any]:
    """Read the auditable source-to-model coverage contract."""
    return json.loads(path.read_text(encoding="utf-8"))


def declared_model_cards(coverage: dict[str, Any] | None = None) -> set[str]:
    """Extract exact checkpoint IDs from the contract's source pages."""
    coverage = coverage or load_model_coverage()
    declared: set[str] = set()
    for name, source in coverage["source_sets"].items():
        text = (REPO / source["path"]).read_text(encoding="utf-8")
        start, end = source.get("start_heading"), source.get("end_heading")
        if start:
            if start not in text:
                raise ValueError(f"{name}: missing start heading {start}")
            text = text.split(start, 1)[1]
        if end:
            if end not in text:
                raise ValueError(f"{name}: missing end heading {end}")
            text = text.split(end, 1)[0]
        declared.update(MODEL_URL.findall(text))
    return declared


def coverage_contract_errors(coverage: dict[str, Any] | None = None) -> list[str]:
    """Return unclassified or stale model-card sources as actionable errors."""
    coverage = coverage or load_model_coverage()
    automated = list(coverage.get("automated_models", []))
    manual_only = coverage.get("manual_only", {})
    errors: list[str] = []
    if coverage.get("schema_version") != 1:
        errors.append("freshness source manifest must use schema_version 1")
    if automated != sorted(set(automated)):
        errors.append("automated_models must be unique and alphabetically sorted")
    if not isinstance(manual_only, dict):
        errors.append("manual_only must be a mapping")
        manual_only = {}
    unreasoned = [model for model, reason in manual_only.items()
                  if not isinstance(reason, str) or not reason.strip()]
    if unreasoned:
        errors.append("manual-only models need a reason: " + ", ".join(sorted(unreasoned)))
    classified = set(automated) | set(manual_only)
    overlap = set(automated) & set(manual_only)
    if overlap:
        errors.append("models cannot be both automated and manual-only: " + ", ".join(sorted(overlap)))
    declared = declared_model_cards(coverage)
    missing, stale = declared - classified, classified - declared
    if missing:
        errors.append("declared model cards lack coverage: " + ", ".join(sorted(missing)))
    if stale:
        errors.append("manifest models are no longer declared: " + ", ".join(sorted(stale)))
    return errors


def watched_models() -> tuple[str, ...]:
    coverage = load_model_coverage()
    errors = coverage_contract_errors(coverage)
    if errors:
        raise ValueError("freshness coverage contract failed: " + "; ".join(errors))
    return tuple(coverage["automated_models"])


# Kept overrideable so tests do not need live network access.
WATCHED_MODELS = watched_models()


def fetch_json(url: str) -> dict[str, Any]:
    """Return a coarse transport status; only 404/410 prove absence."""
    req = urllib.request.Request(url, headers={"User-Agent": "owas-freshness-watcher"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.load(r)
        if isinstance(data, dict):
            return {"status": "ok", "data": data}
        return {"status": "indeterminate", "reason": "invalid-payload"}
    except urllib.error.HTTPError as error:
        if error.code in {404, 410}:
            return {"status": "missing", "reason": f"http-{error.code}"}
        return {"status": "indeterminate", "reason": f"http-{error.code}"}
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"status": "indeterminate", "reason": "network"}
    except (json.JSONDecodeError, ValueError):
        return {"status": "indeterminate", "reason": "invalid-json"}
    except Exception:
        # Never store exception text: it can contain URLs, tokens, or bodies.
        return {"status": "indeterminate", "reason": "transport-error"}


def project_model(repo_id: str) -> dict[str, Any]:
    """Reduce a model card to only the fields the manual makes claims about.
    Everything else changes constantly and would produce noise."""
    response = fetch_json(f"https://huggingface.co/api/models/{repo_id}")
    if response["status"] == "missing":
        return {"status": "missing", "metadata": {"available": False}}
    if response["status"] != "ok":
        return {"status": "indeterminate", "reason": response.get("reason", "transport-error")}
    data = response["data"]
    card = data.get("cardData") or {}
    if not isinstance(card, dict):
        return {"status": "indeterminate", "reason": "invalid-card-data"}
    return {
        "status": "available",
        "metadata": {
            "available": True,
            "license": data.get("license") or card.get("license"),
            "license_name": card.get("license_name"),
            "gated": bool(data.get("gated")),
            "parameters": (
                data.get("safetensors", {}).get("total")
                if isinstance(data.get("safetensors"), dict) else None
            ),
        },
    }


def project_dependencies() -> dict:
    """The build's own pinned versions, from package.json."""
    pkg = json.loads((REPO / "package.json").read_text(encoding="utf-8"))
    return {name: ver for name, ver in sorted(pkg.get("devDependencies", {}).items())}


def latest_npm(name: str) -> str | None:
    response = fetch_json(f"https://registry.npmjs.org/{name}/latest")
    if response["status"] != "ok":
        return None
    data = response["data"]
    return data.get("version")


def load_state() -> dict[str, Any]:
    """Accept legacy state and always return the stable v2 shape."""
    if not STATE_PATH.exists():
        return {"schema_version": 2, "observed": {}, "pending": {}}
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    observed, pending = state.get("observed", {}), state.get("pending", {})
    return {
        "schema_version": 2,
        "observed": observed if isinstance(observed, dict) else {},
        "pending": pending if isinstance(pending, dict) else {},
    }


def diff(label: str, old: dict | None, new: dict | None) -> list[str]:
    if old is None or new is None:
        return []
    out = []
    for key in sorted(set(old) | set(new)):
        if key not in old:
            continue
        a, b = old.get(key), new.get(key)
        if a != b:
            out.append(f"{label}: {key} changed from {a!r} to {b!r}")
    return out


def pending_for_model(pending: dict[str, int], repo_id: str) -> dict[str, int]:
    return {key: value for key, value in pending.items()
            if not key.startswith(f"{repo_id}: ")}


def pending_for_dependency(
    pending: dict[str, int], name: str, keep: str | None = None
) -> dict[str, int]:
    """Forget a dependency's alternate candidate versions, if any."""
    prefix = f"dep:{name}:"
    return {
        key: value for key, value in pending.items()
        if not key.startswith(prefix) or key == keep
    }


def observe_model(
    repo_id: str, previous: dict | None, pending: dict[str, int], current: dict[str, Any]
) -> tuple[dict | None, dict[str, int], list[str], str | None]:
    """Apply one result without allowing indeterminate data to alter state."""
    if current.get("status") == "indeterminate":
        return previous, pending, [], (
            f"{repo_id}: indeterminate ({current.get('reason', 'unknown')}); "
            "keeping last known state"
        )
    metadata = current.get("metadata")
    if current.get("status") not in {"available", "missing"} or not isinstance(metadata, dict):
        return previous, pending, [], (
            f"{repo_id}: indeterminate (invalid-observation); keeping last known state"
        )
    if previous is None:
        return metadata, pending_for_model(pending, repo_id), [], None
    changes = diff(repo_id, previous, metadata)
    if not changes:
        return metadata, pending_for_model(pending, repo_id), [], None
    # A different candidate must start a new consecutive-observation run. Keep
    # only counters for this exact metadata delta; indeterminate observations
    # return above and therefore preserve the current candidate's counters.
    next_pending = {
        key: value for key, value in pending.items()
        if not key.startswith(f"{repo_id}: ") or key in changes
    }
    for change in changes:
        next_pending[change] = next_pending.get(change, 0) + 1
    confirmed = all(next_pending[change] >= CHANGE_CONFIRMATIONS for change in changes)
    if confirmed:
        return metadata, pending_for_model(next_pending, repo_id), changes, None
    return previous, next_pending, [], None


def normalise_state(
    observed: dict[str, Any], pending: dict[str, Any], models: tuple[str, ...]
) -> tuple[dict[str, Any], dict[str, int]]:
    """Migrate state by removing retired IDs and malformed counters."""
    prefixes = tuple(f"{model}: " for model in models)
    observed_now = {
        key: value for key, value in observed.items()
        if key in models or key == "__deps__"
    }
    pending_now = {
        key: value for key, value in pending.items()
        if isinstance(value, int) and value >= 0
        and (key.startswith(prefixes) or key.startswith("dep:"))
    }
    if "__deps__" in observed_now and not isinstance(observed_now["__deps__"], dict):
        observed_now.pop("__deps__")
    return observed_now, pending_now


def main() -> int:
    contract_errors = coverage_contract_errors()
    if contract_errors:
        print("freshness coverage contract failed: " + "; ".join(contract_errors), file=sys.stderr)
        return 1

    state = load_state()
    observed_now, pending = normalise_state(
        state["observed"], state["pending"], tuple(WATCHED_MODELS)
    )
    findings: list[str] = []
    warnings: list[str] = []

    for repo_id in WATCHED_MODELS:
        next_observed, pending, changes, warning = observe_model(
            repo_id, observed_now.get(repo_id), pending, project_model(repo_id)
        )
        if next_observed is None:
            observed_now.pop(repo_id, None)
        else:
            observed_now[repo_id] = next_observed
        if warning:
            warnings.append(warning)
        findings.extend(
            f"- {change}\n  source: https://huggingface.co/{repo_id}"
            for change in changes
        )

    deps = project_dependencies()
    observed_now["__deps__"] = deps
    for name, pinned in deps.items():
        latest = latest_npm(name)
        if latest and latest != pinned.lstrip("^~"):
            key = f"dep:{name}:{latest}"
            pending = pending_for_dependency(pending, name, keep=key)
            pending[key] = pending.get(key, 0) + 1
            if pending[key] >= CHANGE_CONFIRMATIONS:
                findings.append(
                    f"- {name} is pinned at {pinned} but {latest} is published\n"
                    f"  source: https://www.npmjs.com/package/{name}"
                )
                pending = pending_for_dependency(pending, name)
        elif latest:
            # A return to the pinned version is a flap, not proof of an older
            # candidate; discard any counter for this dependency.
            pending = pending_for_dependency(pending, name)

    # Retired IDs (including the old Devstral card) cannot retain counters.
    observed_now, pending = normalise_state(observed_now, pending, tuple(WATCHED_MODELS))

    from datetime import datetime, timezone
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(
        {
            "schema_version": 2,
            "last_run": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "observed": observed_now,
            "pending": pending,
        },
        indent=2, sort_keys=True) + "\n", encoding="utf-8")

    reachable = sum(1 for repo_id in WATCHED_MODELS
                    if isinstance(observed_now.get(repo_id), dict)
                    and observed_now[repo_id].get("available"))
    print(f"checked {len(WATCHED_MODELS)} models ({reachable} last-known available) "
          f"and {len(deps)} pinned dependencies")
    for warning in warnings:
        print(f"warning: {warning}")

    if not findings:
        print("no confirmed drift")
        return 0

    report = "\n".join(findings)
    print(f"\n{len(findings)} confirmed change(s):\n{report}")
    Path("drift-report.md").write_text(
        "The upstream watcher observed these changes after a stable baseline and "
        "two consecutive differing observations. Temporary API failures are excluded.\n\n"
        f"{report}\n\n"
        "Each entry links the primary source. Verify against it before merging: "
        "a licence change is legal guidance by implication.\n",
        encoding="utf-8",
    )
    return 2   # 2 means drift found, distinct from 1 for failure


if __name__ == "__main__":
    raise SystemExit(main())
