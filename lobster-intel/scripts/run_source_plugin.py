#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in ["lobster-core", "lobster-delivery", "lobster-plugins", "lobster-runtime", "lobster-ingest"]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_runtime import normalize_source_plugin_config, run_source_plugin


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("plugin_dir")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--config-json")
    ap.add_argument("--config-file")
    ap.add_argument("--state-path")
    args = ap.parse_args()

    config = None
    if args.config_json:
        config = json.loads(args.config_json)
    elif args.config_file:
        config = json.loads(Path(args.config_file).read_text())

    normalized_config = normalize_source_plugin_config(args.plugin_dir, config)
    if args.state_path:
        normalized_config = normalized_config or {}
        normalized_config["state_path"] = args.state_path

    result = run_source_plugin(args.plugin_dir, args.workspace, config=normalized_config)
    print(
        json.dumps(
            {
                "plugin": result.get("plugin"),
                "new_count": (result.get("evidence") or {}).get("new_count"),
                "run_id": result.get("run_id"),
                "runtime_artifact_path": result.get("runtime_artifact_path"),
                "latest_runtime_artifact_path": result.get("latest_runtime_artifact_path"),
                "state_path": (result.get("evidence") or {}).get("state_path"),
                "normalized_config": result.get("normalized_config"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
