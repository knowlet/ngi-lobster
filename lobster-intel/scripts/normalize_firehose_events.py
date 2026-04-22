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

from lobster_ingest import normalize_firehose_events


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--input-file", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--now-utc")
    args = ap.parse_args()

    payload = normalize_firehose_events(
        workspace_dir=args.workspace,
        input_file=args.input_file,
        run_id=args.run_id,
        now_utc=args.now_utc,
    )
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
