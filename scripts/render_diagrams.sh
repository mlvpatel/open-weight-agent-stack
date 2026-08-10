#!/usr/bin/env bash
# Render diagrams/src/*.mmd to diagrams/svg/*.svg with the house theme.
# Needs node; uses mermaid-cli via npx.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p diagrams/svg
for f in diagrams/src/*.mmd; do
  tmp="$(mktemp).mmd"
  cat scripts/theme-init.txt "$f" > "$tmp"
  npx -y @mermaid-js/mermaid-cli -p scripts/puppeteer.json -i "$tmp" -o "diagrams/svg/$(basename "${f%.mmd}").svg"
  rm "$tmp"
  echo "rendered $(basename "$f")"
done
