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

from lobster_ingest import load_runtime_payload, ocr_image, process_visual_evidence_queue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--thesis-id", required=True)
    parser.add_argument("--runtime-file")
    args = parser.parse_args()

    runtime_payload = load_runtime_payload(
        workspace_dir=args.workspace,
        thesis_id=args.thesis_id,
        runtime_file=args.runtime_file,
    )
    result = process_visual_evidence_queue(
        workspace_dir=args.workspace,
        thesis_id=args.thesis_id,
        runtime_payload=runtime_payload,
        ocr_adapter=ocr_image,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
