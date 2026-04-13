#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export PYTHONPATH="$ROOT/lobster-intel/packages/lobster-core:$ROOT/lobster-intel/packages/lobster-plugins:$ROOT/lobster-intel/packages/lobster-runtime:$ROOT/lobster-intel/packages/lobster-delivery"

python3 - <<'PY'
from lobster_runtime.run_once import run_plugin_once

result = run_plugin_once(
    'lobster-intel/plugins/gooaye-tracker',
    '.'
)

evidence = result.get('evidence', {})
print({
    'plugin': result.get('plugin'),
    'version': result.get('version'),
    'new_count': evidence.get('new_count'),
    'channel': evidence.get('channel'),
})
PY

