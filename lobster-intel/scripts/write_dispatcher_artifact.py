#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from lobster_delivery import write_dispatcher_artifacts


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--thesis-id", required=True)
    parser.add_argument("--runtime-file", required=True)
    parser.add_argument("--sink")
    parser.add_argument("--delivery-status")
    parser.add_argument("--proof-boundary")
    parser.add_argument("--proof-id")
    args = parser.parse_args()

    delivery_receipt = None
    if args.sink or args.delivery_status or args.proof_boundary or args.proof_id:
        delivery_receipt = {
            "sink": args.sink,
            "delivery_status": args.delivery_status,
            "delivery_proof": {
                "boundary": args.proof_boundary,
                "proof_id": args.proof_id,
            },
        }

    result = write_dispatcher_artifacts(
        workspace_dir=args.workspace,
        thesis_id=args.thesis_id,
        runtime_payload=_load_json(args.runtime_file),
        delivery_receipt=delivery_receipt,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
