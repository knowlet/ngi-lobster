#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOBSTER_DIR="$ROOT/lobster-intel"

export PYTHONPATH="$LOBSTER_DIR/packages/lobster-core:$LOBSTER_DIR/packages/lobster-plugins:$LOBSTER_DIR/packages/lobster-runtime:$LOBSTER_DIR/packages/lobster-delivery"

if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY=$(which python3 || true)
fi

if [ -z "$PY" ]; then
  echo "ERROR: No python runtime available. Run ./scripts/bootstrap_runtime.sh" >&2
  exit 2
fi

"$PY" "$LOBSTER_DIR/scripts/process_gooaye_channel.py"

