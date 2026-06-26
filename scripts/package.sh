#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
rm -rf dist
mkdir -p dist
zip -qr dist/codex-work-gate-extension.zip extension
tar -czf dist/codex-work-gate-source.tgz \
  codex_work_gate hooks native-host scripts docs tests extension codex-work-gate README.md
echo "Wrote dist/codex-work-gate-extension.zip and dist/codex-work-gate-source.tgz"
