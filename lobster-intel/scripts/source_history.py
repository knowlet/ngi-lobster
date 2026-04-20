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

from lobster_runtime import rebuild_source_index, replay_source_run


def main() -> None:
    ap = argparse.ArgumentParser()
    subparsers = ap.add_subparsers(dest="command", required=True)

    replay_ap = subparsers.add_parser("replay")
    replay_ap.add_argument("--workspace", default=".")
    replay_ap.add_argument("--plugin-id", required=True)
    replay_ap.add_argument("--run-id", required=True)

    rebuild_ap = subparsers.add_parser("rebuild-index")
    rebuild_ap.add_argument("--workspace", default=".")
    rebuild_ap.add_argument("--plugin-id", required=True)

    args = ap.parse_args()

    if args.command == "replay":
        payload = replay_source_run(args.workspace, args.plugin_id, args.run_id)
    else:
        payload = rebuild_source_index(args.workspace, args.plugin_id)

    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
