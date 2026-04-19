#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export PYTHONPATH="$ROOT/lobster-intel/packages/lobster-core:$ROOT/lobster-intel/packages/lobster-plugins:$ROOT/lobster-intel/packages/lobster-runtime:$ROOT/lobster-intel/packages/lobster-delivery:$ROOT/lobster-intel/packages/lobster-ingest"

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

"$PY" "$ROOT/lobster-intel/scripts/process_gooaye_channel.py" >/dev/null

"$PY" - <<'PY'
import json
from pathlib import Path

runtime = json.loads(Path('lobster-intel/data/runtime/gooaye/latest.json').read_text())
print({
    'plugin': 'gooaye-tracker',
    'version': '0.1.0',
    'new_count': runtime.get('new_count'),
    'channel': runtime.get('channel'),
    'run_id': runtime.get('run_id'),
})
PY
