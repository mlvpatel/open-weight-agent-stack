#!/usr/bin/env python3
"""Generate and verify the repository's deterministic CycloneDX SBOM.

The lockfile is the dependency source of truth.  Unlike ``npm sbom``, this
generator does not include an invocation timestamp, a random UUID, or the
locally installed npm version.  It records every unique package identity in
``package-lock.json`` (including platform-specific optional packages) so the
committed SBOM is portable between developer machines and CI operating systems.

Run ``python3 scripts/sbom.py generate`` to update ``sbom.cdx.json`` and
``python3 scripts/sbom.py check`` to verify it is current.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote


REPO = Path(__file__).resolve().parent.parent
LOCKFILE = "package-lock.json"
OUTPUT = "sbom.cdx.json"
VOLATILE_METADATA_KEYS = frozenset({"timestamp", "tools"})
SUPPLY_CHAIN_METADATA_KEYS = ("integrity", "resolved", "license", "dev", "optional")


def package_name(package_path: str) -> str:
    """Extract an npm package name from a lockfile ``packages`` path."""
    suffix = package_path.rsplit("node_modules/", 1)[-1]
    parts = suffix.split("/")
    return "/".join(parts[:2]) if parts[0].startswith("@") else parts[0]


def component_ref(name: str, package: dict[str, Any]) -> str:
    return f"{name}@{package['version']}"


def load_lockfile(repo: Path) -> dict[str, Any]:
    data = json.loads((repo / LOCKFILE).read_text())
    if data.get("lockfileVersion") != 3 or not isinstance(data.get("packages"), dict):
        raise ValueError("package-lock.json must use lockfileVersion 3 with a packages map")
    return data


def lockfile_packages(repo: Path) -> dict[str, tuple[str, dict[str, Any]]]:
    """Return one canonical lockfile record for every unique name@version.

    Nested copies with the same package identity deliberately collapse into one
    SBOM component.  This matches CycloneDX component identity while preserving
    distinct versions as separate records.
    """
    return component_records(load_lockfile(repo)["packages"])


def component_records(packages: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    """Return one component record per unique identity in a packages map."""
    records: dict[str, tuple[str, dict[str, Any]]] = {}
    source_paths: dict[str, str] = {}
    for package_path in sorted(path for path in packages if path):
        package = packages[package_path]
        if not isinstance(package, dict) or "version" not in package:
            raise ValueError(f"lockfile package {package_path!r} has no version")
        name = package_name(package_path)
        ref = component_ref(name, package)
        existing = records.get(ref)
        if existing is not None:
            prior = existing[1]
            differences = [key for key in SUPPLY_CHAIN_METADATA_KEYS
                           if prior.get(key) != package.get(key)]
            if differences:
                raise ValueError(
                    f"conflicting supply-chain metadata for {ref}: {source_paths[ref]!r} and "
                    f"{package_path!r} differ in {', '.join(differences)}"
                )
        else:
            records[ref] = (name, package)
            source_paths[ref] = package_path
    if not records:
        raise ValueError("package-lock.json contains no dependency packages")
    return records


def lockfile_component_refs(repo: Path) -> set[str]:
    """Component agreement rule: one component for every unique lock identity.

    Platform-specific optional packages remain in the SBOM because they are
    locked supply-chain inputs even when the current host does not install them.
    """
    return set(lockfile_packages(repo))


def parent_package_path(package_path: str) -> str:
    """Return the lockfile path of the enclosing npm package, if any."""
    parts = package_path.split("/")
    remove = 3 if len(parts) >= 3 and parts[-2].startswith("@") else 2
    return "/".join(parts[:-remove])


def resolve_dependency_path(packages: dict[str, Any], package_path: str, name: str) -> str | None:
    """Resolve an npm dependency by walking the lockfile's node_modules tree."""
    candidate_parent = package_path
    while candidate_parent:
        candidate = f"{candidate_parent}/node_modules/{name}"
        if candidate in packages:
            return candidate
        candidate_parent = parent_package_path(candidate_parent)
    root_candidate = f"node_modules/{name}"
    return root_candidate if root_candidate in packages else None


def dependency_graph(repo: Path) -> list[dict[str, Any]]:
    """Build a resolvable CycloneDX dependency graph from lockfile locations."""
    lock = load_lockfile(repo)
    packages: dict[str, Any] = lock["packages"]
    root_package = json.loads((repo / "package.json").read_text())
    return dependency_graph_from_packages(packages, root_package)


def dependency_graph_from_packages(packages: dict[str, Any], root_package: dict[str, Any]) -> list[dict[str, Any]]:
    """Build dependency edges from every lockfile path and union duplicate refs.

    A name@version can be present below more than one ``node_modules`` path.
    CycloneDX stores that identity once, so its edges are the union of regular,
    optional, and resolvable peer edges from each installed location. Missing
    optional peers stay absent because no lockfile path can resolve them.
    """
    records = component_records(packages)
    graph: dict[str, set[str]] = {ref: set() for ref in records}
    for package_path in sorted(path for path in packages if path):
        package = packages[package_path]
        ref = component_ref(package_name(package_path), package)
        declared = dict(package.get("dependencies", {}))
        declared.update(package.get("optionalDependencies", {}))
        declared.update(package.get("peerDependencies", {}))
        for dependency_name in declared:
            resolved = resolve_dependency_path(packages, package_path, dependency_name)
            if resolved is None:
                continue
            dependency = packages[resolved]
            graph[ref].add(component_ref(package_name(resolved), dependency))
    root_ref = f"{root_package['name']}@{root_package['version']}"
    root_dependencies: set[str] = set()
    declared_root = dict(root_package.get("dependencies", {}))
    declared_root.update(root_package.get("devDependencies", {}))
    for dependency_name in declared_root:
        resolved = resolve_dependency_path(packages, "", dependency_name)
        if resolved is None:
            raise ValueError(f"package.json dependency {dependency_name!r} is absent from package-lock.json")
        root_dependencies.add(component_ref(package_name(resolved), packages[resolved]))
    graph[root_ref] = root_dependencies
    return [{"ref": ref, "dependsOn": sorted(dependencies)}
            for ref, dependencies in sorted(graph.items())]


def integrity_hash(integrity: Any) -> list[dict[str, str]]:
    """Convert npm's SRI hash to CycloneDX's hexadecimal hash representation."""
    if not isinstance(integrity, str) or "-" not in integrity:
        return []
    algorithm, encoded = integrity.split("-", 1)
    names = {"sha256": "SHA-256", "sha384": "SHA-384", "sha512": "SHA-512"}
    if algorithm.lower() not in names:
        return []
    try:
        content = base64.b64decode(encoded, validate=True).hex()
    except ValueError:
        return []
    return [{"alg": names[algorithm.lower()], "content": content}]


def component_from_lock(name: str, package: dict[str, Any]) -> dict[str, Any]:
    """Make a CycloneDX component only from immutable lockfile metadata."""
    component: dict[str, Any] = {
        "bom-ref": component_ref(name, package),
        "type": "library",
        "name": name,
        "version": package["version"],
        "scope": "optional" if package.get("optional") else "required",
        "purl": f"pkg:npm/{quote(name, safe='/')}@{quote(str(package['version']), safe='')}",
        "properties": [{
            "name": "cdx:npm:package:development",
            "value": "true" if package.get("dev", False) else "false",
        }],
    }
    hashes = integrity_hash(package.get("integrity"))
    if hashes:
        component["hashes"] = hashes
    if isinstance(package.get("resolved"), str):
        component["externalReferences"] = [{"type": "distribution", "url": package["resolved"]}]
    if isinstance(package.get("license"), str) and package["license"].strip():
        component["licenses"] = [{"license": {"name": package["license"].strip()}}]
    return component


def root_component(repo: Path) -> dict[str, Any]:
    package = json.loads((repo / "package.json").read_text())
    required = ("name", "version")
    if any(key not in package for key in required):
        raise ValueError("package.json must declare name and version")
    component: dict[str, Any] = {
        "bom-ref": f"{package['name']}@{package['version']}",
        "type": "library",
        "name": package["name"],
        "version": package["version"],
        "scope": "required",
        "purl": f"pkg:npm/{quote(package['name'], safe='/')}@{quote(package['version'], safe='')}",
        "properties": [{"name": "cdx:npm:package:private", "value": str(bool(package.get("private"))).lower()}],
    }
    if isinstance(package.get("description"), str):
        component["description"] = package["description"]
    if isinstance(package.get("license"), str):
        component["licenses"] = [{"license": {"name": package["license"]}}]
    return component


def canonicalize(value: Any) -> Any:
    """Recursively make equivalent JSON data serialize with identical bytes."""
    if isinstance(value, dict):
        return {key: canonicalize(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        normalized = [canonicalize(item) for item in value]
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    return value


def normalize(document: dict[str, Any]) -> dict[str, Any]:
    """Remove runtime metadata and canonicalize a CycloneDX document."""
    normalized = json.loads(json.dumps(document))
    normalized.pop("serialNumber", None)
    metadata = normalized.get("metadata")
    if isinstance(metadata, dict):
        for key in VOLATILE_METADATA_KEYS:
            metadata.pop(key, None)
    return canonicalize(normalized)


def document(repo: Path) -> dict[str, Any]:
    lock_digest = hashlib.sha256((repo / LOCKFILE).read_bytes()).hexdigest()
    components = [component_from_lock(name, package)
                  for _ref, (name, package) in lockfile_packages(repo).items()]
    return normalize({
        "$schema": "http://cyclonedx.org/schema/bom-1.5.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "lifecycles": [{"phase": "build"}],
            "component": root_component(repo),
            "properties": [{
                "name": "cdx:lockfile:sha256",
                "value": lock_digest,
            }],
        },
        "components": components,
        "dependencies": dependency_graph(repo),
    })


def generate_bytes(repo: Path) -> bytes:
    return (json.dumps(document(repo), indent=2, sort_keys=True) + "\n").encode()


def validation_errors(repo: Path, candidate: bytes) -> list[str]:
    """Return concrete SBOM contract failures without using the network."""
    errors: list[str] = []
    try:
        data = json.loads(candidate)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return [f"SBOM is not valid JSON: {error}"]
    if not isinstance(data, dict):
        return ["SBOM root must be an object"]
    if data.get("bomFormat") != "CycloneDX" or data.get("specVersion") != "1.5":
        errors.append("SBOM must be a CycloneDX 1.5 document")
    if "serialNumber" in data:
        errors.append("SBOM contains volatile serialNumber metadata")
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        errors.append("SBOM metadata is missing")
    else:
        for key in VOLATILE_METADATA_KEYS:
            if key in metadata:
                errors.append(f"SBOM contains volatile metadata.{key}")
    components = data.get("components")
    if not isinstance(components, list):
        errors.append("SBOM components is missing")
        return errors
    refs = {component.get("bom-ref") for component in components if isinstance(component, dict)}
    expected_refs = lockfile_component_refs(repo)
    if refs != expected_refs:
        errors.append(
            "SBOM lockfile/component agreement failed: "
            f"expected {len(expected_refs)} unique lockfile components, found {len(refs)}"
        )
    package = json.loads((repo / "package.json").read_text())
    for name, version in package.get("devDependencies", {}).items():
        if f"{name}@{version}" not in refs:
            errors.append(f"SBOM omits direct devDependency {name}@{version}")
    dependencies = data.get("dependencies")
    root_ref = f"{package['name']}@{package['version']}"
    if not isinstance(dependencies, list):
        errors.append("SBOM dependencies graph is missing")
    else:
        graph_refs = {item.get("ref") for item in dependencies if isinstance(item, dict)}
        expected_graph_refs = refs | {root_ref}
        if graph_refs != expected_graph_refs:
            errors.append("SBOM dependencies graph must contain the root and every component ref")
        for item in dependencies:
            if not isinstance(item, dict):
                errors.append("SBOM dependencies graph contains a non-object entry")
                continue
            for dependency_ref in item.get("dependsOn", []):
                if dependency_ref not in expected_graph_refs:
                    errors.append(
                        f"SBOM dependencies graph has unresolved reference {dependency_ref!r} from {item.get('ref')!r}"
                    )
    expected = generate_bytes(repo)
    if candidate != expected:
        errors.append("SBOM differs from deterministic package-lock generation; run npm run sbom")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "check"))
    parser.add_argument("--sbom", type=Path, default=REPO / OUTPUT,
                        help="SBOM file to write or check (default: sbom.cdx.json)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = args.sbom if args.sbom.is_absolute() else REPO / args.sbom
    if args.command == "generate":
        target.write_bytes(generate_bytes(REPO))
        print(f"generated {target.relative_to(REPO) if target.is_relative_to(REPO) else target}: "
              f"{len(lockfile_component_refs(REPO))} components")
        return 0
    if not target.is_file():
        print(f"SBOM check failed:\n  - missing {target}", file=sys.stderr)
        return 1
    errors = validation_errors(REPO, target.read_bytes())
    if errors:
        print("SBOM check failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"SBOM check passed: {len(lockfile_component_refs(REPO))} lockfile components")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
