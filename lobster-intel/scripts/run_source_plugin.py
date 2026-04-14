#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in ["lobster-core", "lobster-plugins", "lobster-runtime", "lobster-ingest"]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_runtime import run_source_plugin


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("plugin_dir")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--config-json")
    ap.add_argument("--config-file")
    args = ap.parse_args()

    config = None
    if args.config_json:
        config = json.loads(args.config_json)
    elif args.config_file:
        config = json.loads(Path(args.config_file).read_text())

    result = run_source_plugin(args.plugin_dir, args.workspace, config=config)
    print(
        json.dumps(
            {
                "plugin": result.get("plugin"),
                "new_count": (result.get("evidence") or {}).get("new_count"),
                "runtime_artifact_path": result.get("runtime_artifact_path"),
                "state_path": (result.get("evidence") or {}).get("state_path"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
