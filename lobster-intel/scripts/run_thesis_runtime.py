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

from lobster_runtime import ThesisRuntimeInput, run_thesis_runtime


def _load_json(path: str | None) -> dict | list | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--thesis-id", required=True)
    ap.add_argument("--official")
    ap.add_argument("--watchlist")
    ap.add_argument("--polymarket")
    ap.add_argument("--registry-file")
    ap.add_argument("--semantic-frame", default="generic_thesis_frame")
    ap.add_argument("--probability-direction", default="yes_is_peace")
    ap.add_argument("--state", default="ACTIVE_TRUCE")
    ap.add_argument("--now-utc")
    args = ap.parse_args()

    result = run_thesis_runtime(
        ThesisRuntimeInput(
            thesis_id=args.thesis_id,
            workspace_dir=args.workspace,
            official_statements=_load_json(args.official),
            watchlist=_load_json(args.watchlist),
            polymarket=_load_json(args.polymarket),
            target_registry=_load_json(args.registry_file) or [],
            semantic_frame=args.semantic_frame,
            probability_direction=args.probability_direction,
            state=args.state,
            now_utc=args.now_utc,
        )
    )
    print(
        json.dumps(
            {
                "thesis_id": result.thesis_id,
                "run_id": result.run_id,
                "compare_mode": result.runtime_snapshot.get("compare_mode"),
                "runtime_latest_path": result.paths["runtime_latest"],
                "delivery_receipt_path": result.paths["delivery_receipt"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
