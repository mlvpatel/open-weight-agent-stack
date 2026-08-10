# Vendored CycloneDX 1.5 schemas

These files are the unmodified official JSON schemas used by the offline SBOM
gate. They were downloaded from the CycloneDX schema endpoint on 2026-08-11:

- `https://cyclonedx.org/schema/bom-1.5.schema.json`
- `https://cyclonedx.org/schema/spdx.schema.json`
- `https://cyclonedx.org/schema/jsf-0.82.schema.json`

SHA-256 digests:

```text
a00fcba23a44b72179ac1f288be4c3529b59f6e1b3719709a40685f177516b46  bom-1.5.schema.json
c87aa7bb5eb503d40b52ec6bf00de8045df15da7a13cea48d290cf6d36a8d2ea  spdx.schema.json
2faf5eb3651f2ae5f46091a131770d8d847bbd121139d19c85fc7051bfa58c46  jsf-0.82.schema.json
```

The validator is `scripts/validate_sbom_schema.cjs`; it reads only these
vendored files and never fetches schemas during tests or CI.
