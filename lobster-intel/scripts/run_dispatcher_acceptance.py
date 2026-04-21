#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for package_dir in (
    ROOT / "packages" / "lobster-core",
    ROOT / "packages" / "lobster-delivery",
    ROOT / "packages" / "lobster-ingest",
    ROOT / "packages" / "lobster-plugins",
    ROOT / "packages" / "lobster-runtime",
):
    sys.path.insert(0, str(package_dir))

from lobster_delivery import write_dispatcher_artifacts, write_dispatcher_e2e_bundle


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Materialize real dispatcher artifacts and one shared E2E bundle from runtime runs."
    )
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--thesis-id", required=True)
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument("--suppressed-run-id", required=True)
    parser.add_argument("--positive-run-id", required=True)
    parser.add_argument("--sink", required=True)
    parser.add_argument("--delivery-status", required=True)
    parser.add_argument("--proof-boundary", required=True)
    parser.add_argument("--proof-id", required=True)
    parser.add_argument("--now-utc")
    args = parser.parse_args(argv[1:])

    runtime_root = Path(args.workspace) / "lobster-intel" / "data" / "runtime" / args.thesis_id / "runs"
    suppressed_runtime = _load_json(runtime_root / f"{args.suppressed_run_id}.json")
    positive_runtime = _load_json(runtime_root / f"{args.positive_run_id}.json")

    suppressed = write_dispatcher_artifacts(
        workspace_dir=args.workspace,
        thesis_id=args.thesis_id,
        runtime_payload=suppressed_runtime,
        e2e_run_id=args.bundle_id,
        now_utc=args.now_utc,
    )
    positive = write_dispatcher_artifacts(
        workspace_dir=args.workspace,
        thesis_id=args.thesis_id,
        runtime_payload=positive_runtime,
        e2e_run_id=args.bundle_id,
        delivery_receipt={
            "sink": args.sink,
            "delivery_status": args.delivery_status,
            "delivery_proof": {
                "boundary": args.proof_boundary,
                "proof_id": args.proof_id,
            },
        },
        now_utc=args.now_utc,
    )
    bundle = write_dispatcher_e2e_bundle(
        workspace_dir=args.workspace,
        thesis_id=args.thesis_id,
        run_ids=[args.suppressed_run_id, args.positive_run_id],
        bundle_id=args.bundle_id,
        now_utc=args.now_utc,
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "thesis_id": args.thesis_id,
                "bundle_id": args.bundle_id,
                "suppressed": suppressed,
                "positive": positive,
                "bundle": bundle,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
