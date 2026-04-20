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

from lobster_ingest import extract_linked_content, load_runtime_payload, process_linked_content_queue


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--thesis-id", required=True)
    ap.add_argument("--runtime-file")
    ap.add_argument("--linked-url")
    ap.add_argument("--now-utc")
    args = ap.parse_args()

    runtime_payload = load_runtime_payload(args.workspace, args.thesis_id, runtime_file=args.runtime_file)
    if args.linked_url:
        runtime_payload = dict(runtime_payload)
        runtime_payload["linked_content_queue"] = [
            {
                "post_id": "manual",
                "url": args.linked_url,
                "linked_url": args.linked_url,
                "site_name": None,
                "title": None,
            }
        ]

    result = process_linked_content_queue(
        workspace_dir=args.workspace,
        thesis_id=args.thesis_id,
        runtime_payload=runtime_payload,
        extractor=extract_linked_content,
        now_utc=args.now_utc,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
