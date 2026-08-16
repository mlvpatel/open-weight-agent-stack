#!/usr/bin/env python3
"""Regression tests for deterministic CycloneDX SBOM generation.

Run: python3 scripts/test_sbom.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sbom  # noqa: E402


REPO = Path(__file__).resolve().parent.parent
SBOM = REPO / "sbom.cdx.json"


class SbomTests(unittest.TestCase):
    def test_normalization_removes_volatile_runtime_metadata(self) -> None:
        document = {
            "serialNumber": "urn:uuid:volatile",
            "metadata": {
                "timestamp": "2026-08-11T00:00:00Z",
                "tools": [{"vendor": "npm", "version": "999"}],
            },
            "components": [
                {"bom-ref": "z@1", "name": "z"},
                {"bom-ref": "a@1", "name": "a"},
            ],
        }

        normalized = sbom.normalize(document)

        self.assertNotIn("serialNumber", normalized)
        self.assertNotIn("timestamp", normalized["metadata"])
        self.assertNotIn("tools", normalized["metadata"])
        self.assertEqual([item["bom-ref"] for item in normalized["components"]], ["a@1", "z@1"])

    def test_two_independent_generations_are_byte_identical(self) -> None:
        first = sbom.generate_bytes(REPO)
        second = sbom.generate_bytes(REPO)

        self.assertEqual(first, second)
        self.assertNotIn(b'"serialNumber"', first)
        self.assertNotIn(b'"timestamp"', first)

    def test_committed_sbom_is_fresh_and_valid(self) -> None:
        errors = sbom.validation_errors(REPO, SBOM.read_bytes())

        self.assertEqual(errors, [], "\n".join(errors))

    def test_all_lockfile_packages_have_components_and_direct_dev_dependencies_are_present(self) -> None:
        document = json.loads(SBOM.read_text(encoding="utf-8"))
        component_refs = {component["bom-ref"] for component in document["components"]}
        lock_refs = sbom.lockfile_component_refs(REPO)
        package = json.loads((REPO / "package.json").read_text(encoding="utf-8"))

        self.assertEqual(component_refs, lock_refs)
        for name, version in package["devDependencies"].items():
            self.assertIn(f"{name}@{version}", component_refs)

    def test_dependency_graph_has_only_resolvable_component_references(self) -> None:
        document = json.loads(SBOM.read_text(encoding="utf-8"))
        refs = {component["bom-ref"] for component in document["components"]}
        root = document["metadata"]["component"]["bom-ref"]
        graph = {entry["ref"]: entry.get("dependsOn", []) for entry in document["dependencies"]}

        self.assertEqual(set(graph), refs | {root})
        self.assertTrue(all(dependency in refs | {root}
                            for dependencies in graph.values() for dependency in dependencies))

    def test_resolvable_peer_dependencies_are_graph_edges(self) -> None:
        graph = {entry["ref"]: entry.get("dependsOn", []) for entry in json.loads(SBOM.read_text(encoding="utf-8"))["dependencies"]}

        self.assertIn("puppeteer@25.5.0", graph["@mermaid-js/mermaid-cli@11.16.0"])

    def test_duplicate_lockfile_paths_union_dependency_and_peer_edges(self) -> None:
        packages = {
            "node_modules/first": {"version": "1.0.0", "dependencies": {"shared": "1"}},
            "node_modules/second": {"version": "1.0.0", "dependencies": {"shared": "1"}},
            "node_modules/first/node_modules/shared": {
                "version": "1.0.0", "dependencies": {"left": "1"},
            },
            "node_modules/second/node_modules/shared": {
                "version": "1.0.0", "peerDependencies": {"right": "1"},
            },
            "node_modules/first/node_modules/left": {"version": "1.0.0"},
            "node_modules/second/node_modules/right": {"version": "1.0.0"},
        }

        graph = {entry["ref"]: entry["dependsOn"]
                 for entry in sbom.dependency_graph_from_packages(packages, {"name": "root", "version": "1"})}

        self.assertEqual(graph["shared@1.0.0"], ["left@1.0.0", "right@1.0.0"])

    def test_conflicting_duplicate_supply_chain_metadata_fails_loudly(self) -> None:
        packages = {
            "node_modules/first/node_modules/shared": {
                "version": "1.0.0",
                "integrity": "sha512-first",
                "resolved": "https://registry.example/first.tgz",
                "license": "MIT",
                "dev": True,
            },
            "node_modules/second/node_modules/shared": {
                "version": "1.0.0",
                "integrity": "sha512-second",
                "resolved": "https://registry.example/second.tgz",
                "license": "Apache-2.0",
                "optional": True,
            },
        }

        with self.assertRaisesRegex(ValueError, "conflicting supply-chain metadata"):
            sbom.component_records(packages)

    def test_offline_schema_validator_accepts_committed_sbom_and_rejects_invalid_structure(self) -> None:
        valid = subprocess.run(
            ["node", "scripts/validate_sbom_schema.cjs", "--sbom", str(SBOM)],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertIn("CycloneDX 1.5 schema validation passed", valid.stdout)

        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.cdx.json"
            document = json.loads(SBOM.read_text(encoding="utf-8"))
            document["components"][0].pop("name")
            invalid.write_text(json.dumps(document), encoding="utf-8")
            result = subprocess.run(
                ["node", "scripts/validate_sbom_schema.cjs", "--sbom", str(invalid)],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CycloneDX schema validation failed", result.stderr)

    def test_tampered_or_stale_sbom_fails_validation(self) -> None:
        document = json.loads(SBOM.read_text(encoding="utf-8"))
        document["components"].pop()
        document["serialNumber"] = "urn:uuid:tampered"
        errors = sbom.validation_errors(REPO, json.dumps(document).encode())

        self.assertTrue(errors)
        self.assertTrue(any("volatile" in error or "lockfile" in error for error in errors))

    def test_unresolved_dependency_graph_reference_fails_validation(self) -> None:
        document = json.loads(SBOM.read_text(encoding="utf-8"))
        document["dependencies"][0]["dependsOn"].append("missing-package@0.0.0")

        errors = sbom.validation_errors(REPO, json.dumps(document).encode())

        self.assertTrue(any("unresolved reference" in error for error in errors))

    def test_check_command_rejects_a_tampered_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "tampered.cdx.json"
            target.write_bytes(SBOM.read_bytes().replace(b'"bomFormat": "CycloneDX"', b'"bomFormat": "Wrong"'))
            result = subprocess.run(
                [sys.executable, "scripts/sbom.py", "check", "--sbom", str(target)],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SBOM check failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
