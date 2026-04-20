#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"
PY_BIN="$(which python3 || true)"

if [ "${1-}" = "--help" ] || [ "${1-}" = "-h" ]; then
  cat <<'EOF'
Usage:
  ./scripts/bootstrap_runtime.sh

Purpose:
  Create or reuse the local .venv, upgrade packaging tools, install lobster-intel editable,
  and install runtime dependencies needed by the current NGI Lobster setup.

Requirements:
  - python3 on PATH
  - Python >= 3.11
EOF
  exit 0
fi

if [ -z "$PY_BIN" ]; then
  echo "ERROR: python3 not found on PATH. Please install Python 3.11+ and retry." >&2
  exit 2
fi

PY_VERSION=$($PY_BIN -c 'import sys; print("%d.%d"%(sys.version_info.major, sys.version_info.minor))')
MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]; }; then
  echo "ERROR: python3 must be >= 3.11. Found $PY_VERSION" >&2
  exit 2
fi

# create venv if missing
if [ ! -d "$VENV" ]; then
  echo "Creating venv at $VENV"
  $PY_BIN -m venv "$VENV"
fi

PIP="$VENV/bin/pip"
PY="$VENV/bin/python"

# Upgrade pip
$PIP install --upgrade pip setuptools wheel

# Install lobster-intel editable for local runs
echo "Installing lobster-intel package into venv (editable)"
$PIP install -e "$ROOT/lobster-intel"

# Install runtime deps that lobster-intel may require
$PIP install requests

# Success
echo "OK: venv ready at $VENV. Use $VENV/bin/python to run demo_run_gooaye.sh"
