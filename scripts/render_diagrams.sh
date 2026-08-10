#!/usr/bin/env bash
# Render diagrams/src/*.mmd to diagrams/svg/*.svg using the single shared theme.
# Dependencies resolve from package-lock.json, so two runs produce identical bytes.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -d node_modules ] || npm ci --no-audit --no-fund

THEME_INIT="%%{init: $(node -e 'process.stdout.write(JSON.stringify(require("./assets/mermaid-theme.json")))')}%%"

mkdir -p diagrams/svg
for f in diagrams/src/*.mmd; do
  name="$(basename "${f%.mmd}")"
  tmp="$(mktemp)"
  printf '%s\n' "$THEME_INIT" > "$tmp"
  cat "$f" >> "$tmp"
  npx --no-install mmdc -p scripts/puppeteer.json -i "$tmp" -o "diagrams/svg/${name}.svg"
  rm -f "$tmp"
  echo "rendered ${name}"
done
