#!/usr/bin/env node
"use strict";

/** Validate a CycloneDX 1.5 SBOM using the vendored official schemas. */
const fs = require("fs");
const path = require("path");
const Ajv = require("ajv");

const REPO = path.resolve(__dirname, "..");
const SCHEMA_DIR = path.join(REPO, "schemas", "cyclonedx-1.5");
const MAIN_SCHEMA = "http://cyclonedx.org/schema/bom-1.5.schema.json";
const SCHEMA_FILES = ["spdx.schema.json", "jsf-0.82.schema.json", "bom-1.5.schema.json"];

function parseArgs(argv) {
  const index = argv.indexOf("--sbom");
  if (index === -1 || !argv[index + 1] || index + 2 !== argv.length) {
    throw new Error("usage: node scripts/validate_sbom_schema.cjs --sbom <path>");
  }
  return path.resolve(argv[index + 1]);
}

function loadJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function main() {
  const sbomPath = parseArgs(process.argv.slice(2));
  const ajv = new Ajv({ strict: false, validateFormats: false });
  for (const file of SCHEMA_FILES) {
    ajv.addSchema(loadJson(path.join(SCHEMA_DIR, file)));
  }
  const validate = ajv.getSchema(MAIN_SCHEMA);
  if (!validate) {
    throw new Error(`missing vendored schema ${MAIN_SCHEMA}`);
  }
  if (!validate(loadJson(sbomPath))) {
    console.error("CycloneDX schema validation failed:");
    for (const error of validate.errors || []) {
      console.error(`  - ${error.instancePath || "/"} ${error.message}`);
    }
    return 1;
  }
  console.log("CycloneDX 1.5 schema validation passed");
  return 0;
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(`CycloneDX schema validation failed: ${error.message}`);
  process.exitCode = 1;
}
