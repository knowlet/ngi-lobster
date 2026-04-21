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

from lobster_ingest import backfill_visual_evidence_runs
from lobster_ingest import visual_evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--thesis-id", required=True)
    args = parser.parse_args()

    result = backfill_visual_evidence_runs(
        workspace_dir=args.workspace,
        thesis_id=args.thesis_id,
        ocr_adapter=visual_evidence.ocr_image,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
