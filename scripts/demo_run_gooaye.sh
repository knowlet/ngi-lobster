#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export PYTHONPATH="$ROOT/lobster-intel/packages/lobster-core:$ROOT/lobster-intel/packages/lobster-plugins:$ROOT/lobster-intel/packages/lobster-runtime:$ROOT/lobster-intel/packages/lobster-delivery"

# Prefer venv python if present
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY=$(which python3 || true)
fi

if [ -z "$PY" ]; then
  echo "ERROR: No python3 found and no .venv available. Run scripts/bootstrap_runtime.sh" >&2
  exit 2
fi

"$PY" - <<'PY'
from lobster_runtime.run_once import run_plugin_once
from pathlib import Path

# Ensure we run with repository-root workspace
root = Path('.')
result = run_plugin_once(
    'lobster-intel/plugins/gooaye-tracker',
    str(root)
)

evidence = result.get('evidence', {}) or {}
print({
    'plugin': result.get('plugin'),
    'version': result.get('version'),
    'new_count': evidence.get('new_count'),
    'channel': evidence.get('channel'),
})
PY

