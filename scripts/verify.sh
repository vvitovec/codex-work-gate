#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests
python3 -m py_compile codex_work_gate/*.py hooks/work_gate_hook.py
