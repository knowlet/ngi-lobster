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


def _load_optional_json(path: str | Path) -> dict | None:
    resolved = Path(path)
    if not resolved.exists():
        return None
    return _load_json(resolved)


def _validate_persisted_receipt(
    receipt: dict,
    *,
    thesis_id: str,
    run_id: str,
    contract_version: str | None,
) -> dict:
    persisted_run_id = str(receipt.get("run_id") or "").strip()
    persisted_thesis_id = str(receipt.get("thesis_id") or "").strip()
    persisted_contract_version = str(receipt.get("contract_version") or "").strip()
    mismatches: list[str] = []
    if persisted_run_id and persisted_run_id != run_id:
        mismatches.append(f"run_id={persisted_run_id!r}")
    if persisted_thesis_id and persisted_thesis_id != thesis_id:
        mismatches.append(f"thesis_id={persisted_thesis_id!r}")
    if contract_version and persisted_contract_version and persisted_contract_version != contract_version:
        raise ValueError(
            "persisted receipt contract_version does not match requested positive run: "
            f"expected {contract_version!r}, got {persisted_contract_version!r}"
        )
    if mismatches:
        mismatch_summary = ", ".join(mismatches)
        raise ValueError(
            "persisted receipt metadata does not match requested positive run: "
            f"expected thesis_id={thesis_id!r}, run_id={run_id!r}; got {mismatch_summary}"
        )
    return receipt


def _resolve_delivery_receipt(
    args: argparse.Namespace,
    *,
    positive_runtime: dict,
    receipts_root: Path,
) -> dict | None:
    receipt = _load_optional_json(receipts_root / f"{args.positive_run_id}.json") or {}
    if receipt:
        receipt = _validate_persisted_receipt(
            receipt,
            thesis_id=args.thesis_id,
            run_id=args.positive_run_id,
            contract_version=str(positive_runtime.get("contract_version") or "").strip() or None,
        )
    if args.sink:
        receipt["sink"] = args.sink
    if args.delivery_status:
        receipt["delivery_status"] = args.delivery_status

    delivery_proof = dict(receipt.get("delivery_proof") or {})
    if args.proof_boundary:
        delivery_proof["boundary"] = args.proof_boundary
    if args.proof_id:
        delivery_proof["proof_id"] = args.proof_id
    if delivery_proof:
        receipt["delivery_proof"] = delivery_proof

    return receipt or None


def _with_bundle_id(runtime_payload: dict, bundle_id: str) -> dict:
    enriched = dict(runtime_payload)
    disposition = dict(enriched.get("alert_disposition") or {})
    if not disposition:
        enriched["alert_disposition"] = {"e2e_run_id": bundle_id}
        return enriched
    if not disposition.get("e2e_run_id"):
        disposition["e2e_run_id"] = bundle_id
    enriched["alert_disposition"] = disposition
    return enriched


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Materialize one dispatcher acceptance bundle from a suppressed and positive runtime run."
    )
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--thesis-id", required=True)
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument("--suppressed-run-id", required=True)
    parser.add_argument("--positive-run-id", required=True)
    parser.add_argument("--sink")
    parser.add_argument("--delivery-status")
    parser.add_argument("--proof-boundary")
    parser.add_argument("--proof-id")
    parser.add_argument("--now-utc")
    args = parser.parse_args(argv[1:])

    runtime_root = Path(args.workspace) / "lobster-intel" / "data" / "runtime" / args.thesis_id / "runs"
    receipts_root = Path(args.workspace) / "lobster-intel" / "data" / "delivery" / args.thesis_id / "receipts"
    try:
        suppressed_runtime = _load_json(runtime_root / f"{args.suppressed_run_id}.json")
        positive_runtime = _load_json(runtime_root / f"{args.positive_run_id}.json")
        delivery_receipt = _resolve_delivery_receipt(
            args,
            positive_runtime=positive_runtime,
            receipts_root=receipts_root,
        )

        suppressed = write_dispatcher_artifacts(
            workspace_dir=args.workspace,
            thesis_id=args.thesis_id,
            runtime_payload=_with_bundle_id(suppressed_runtime, args.bundle_id),
            now_utc=args.now_utc,
        )
        positive = write_dispatcher_artifacts(
            workspace_dir=args.workspace,
            thesis_id=args.thesis_id,
            runtime_payload=_with_bundle_id(positive_runtime, args.bundle_id),
            delivery_receipt=delivery_receipt,
            now_utc=args.now_utc,
        )
        bundle = write_dispatcher_e2e_bundle(
            workspace_dir=args.workspace,
            thesis_id=args.thesis_id,
            run_ids=[args.suppressed_run_id, args.positive_run_id],
            bundle_id=args.bundle_id,
            now_utc=args.now_utc,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

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
