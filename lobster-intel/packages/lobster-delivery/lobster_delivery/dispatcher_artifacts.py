from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DELIVERY_PROOF_ID_FIELDS = (
    "proof_id",
    "sink_message_id",
    "delivery_event_id",
    "external_receipt_id",
)


def _missing(value: Any) -> bool:
    return value is None or value == ""


def _first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if not _missing(value):
            return value
    return None


def _now_utc(value: str | None = None) -> str:
    if value:
        return value
    return datetime.now(timezone.utc).isoformat()


def _delivery_root(workspace_dir: str | Path, thesis_id: str) -> Path:
    return Path(workspace_dir) / "lobster-intel" / "data" / "delivery" / thesis_id


def _runtime_root(workspace_dir: str | Path, thesis_id: str) -> Path:
    return Path(workspace_dir) / "lobster-intel" / "data" / "runtime" / thesis_id


def _relative_path(path: Path, workspace_dir: str | Path) -> str:
    return str(path.relative_to(Path(workspace_dir)))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_delivery_proof(delivery_proof: dict[str, Any] | None) -> dict[str, Any] | None:
    if delivery_proof is None:
        return None

    normalized = dict(delivery_proof)
    proof_id = _first_present(normalized, *DELIVERY_PROOF_ID_FIELDS)
    if not _missing(proof_id):
        normalized["proof_id"] = proof_id
    return normalized


def _project_runtime_disposition(
    *,
    workspace_dir: str | Path,
    thesis_id: str,
    runtime_payload: dict[str, Any],
) -> dict[str, Any]:
    run_id = str(runtime_payload.get("run_id") or "").strip()
    runtime_root = _runtime_root(workspace_dir, thesis_id)
    delivery_root = _delivery_root(workspace_dir, thesis_id)

    compare_payload = _load_json(runtime_root / "compare" / f"{run_id}.json")
    alert_payload = _load_json(delivery_root / "alerts" / f"{run_id}.json")
    active_target = runtime_payload.get("active_target") or {}
    should_send = bool(alert_payload.get("should_send"))

    return {
        "should_send": should_send,
        "decision": "would_send" if should_send else "suppressed",
        "reason_code": alert_payload.get("reason_code"),
        "runtime_target_id": compare_payload.get("runtime_target_id")
        or active_target.get("market_id")
        or active_target.get("market_slug"),
        "runtime_target_name": active_target.get("market_name")
        or active_target.get("market_question"),
        "alert_target_id": compare_payload.get("market_target_id") or compare_payload.get("runtime_target_id"),
        "contract_version": alert_payload.get("contract_version") or runtime_payload.get("contract_version"),
    }


def _validate_delivery_receipt(delivery_receipt: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(delivery_receipt, dict):
        raise ValueError("delivery_receipt is required for would_send dispatcher artifacts")

    normalized = dict(delivery_receipt)
    normalized["delivery_proof"] = _normalize_delivery_proof(normalized.get("delivery_proof"))

    missing_fields = [
        field
        for field in ("sink", "delivery_status", "delivery_proof")
        if _missing(normalized.get(field))
    ]
    delivery_proof = normalized.get("delivery_proof")
    if not isinstance(delivery_proof, dict):
        missing_fields.extend(["delivery_proof.boundary", "delivery_proof.proof_id"])
    else:
        if _missing(delivery_proof.get("boundary")):
            missing_fields.append("delivery_proof.boundary")
        if _missing(delivery_proof.get("proof_id")):
            missing_fields.append("delivery_proof.proof_id")

    if missing_fields:
        raise ValueError(f"incomplete delivery_receipt: {', '.join(missing_fields)}")

    return normalized


def write_dispatcher_artifacts(
    *,
    workspace_dir: str | Path,
    thesis_id: str,
    runtime_payload: dict[str, Any],
    delivery_receipt: dict[str, Any] | None = None,
    e2e_run_id: str | None = None,
    now_utc: str | None = None,
) -> dict[str, Any]:
    run_id = str(runtime_payload.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("runtime_payload.run_id is required")

    disposition = dict(runtime_payload.get("alert_disposition") or {})
    if not disposition:
        disposition = _project_runtime_disposition(
            workspace_dir=workspace_dir,
            thesis_id=thesis_id,
            runtime_payload=runtime_payload,
        )
    decision = str(disposition.get("decision") or "").strip()
    if not decision:
        raise ValueError("runtime_payload.alert_disposition.decision is required")
    if e2e_run_id and _missing(disposition.get("e2e_run_id")) and _missing(disposition.get("e2e_bundle_id")):
        disposition["e2e_run_id"] = e2e_run_id

    recorded_at_utc = _now_utc(now_utc)
    delivery_root = _delivery_root(workspace_dir, thesis_id)
    alerts_root = delivery_root / "alerts"
    receipts_root = delivery_root / "receipts"
    alerts_root.mkdir(parents=True, exist_ok=True)
    receipts_root.mkdir(parents=True, exist_ok=True)

    alert_artifact_id = f"alert:{thesis_id}:{run_id}"
    compare_artifact_id = f"compare:{thesis_id}:{run_id}"
    normalized_receipt = None
    if decision == "would_send":
        normalized_receipt = _validate_delivery_receipt(delivery_receipt)
        disposition["delivery_proof"] = normalized_receipt["delivery_proof"]
    normalized_runtime_payload = dict(runtime_payload)
    normalized_runtime_payload.setdefault("market_target", normalized_runtime_payload.get("active_target"))
    normalized_runtime_payload.setdefault(
        "target_detail",
        {
            "market_yes_probability": normalized_runtime_payload.get("market_implied_probability"),
        },
    )
    if "first_principles_probability" not in normalized_runtime_payload and normalized_runtime_payload.get("P_AI") is not None:
        normalized_runtime_payload["first_principles_probability"] = normalized_runtime_payload.get("P_AI")
    normalized_runtime_payload["alert_disposition"] = disposition
    alert_payload = {
        "schema": "lobster.delivery.dispatcher_alert.v1",
        "artifact_id": alert_artifact_id,
        "recorded_at_utc": recorded_at_utc,
        "thesis_id": thesis_id,
        "run_id": run_id,
        "should_send": disposition.get("should_send"),
        "decision": decision,
        "reason_code": disposition.get("reason_code"),
        "compare_artifact_id": compare_artifact_id,
        **normalized_runtime_payload,
    }
    alert_path = alerts_root / f"{run_id}.json"
    alert_path.write_text(json.dumps(alert_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    receipt_path: Path | None = None
    if decision == "would_send":
        receipt_payload = {
            "schema": "lobster.delivery.dispatcher_receipt.v1",
            "artifact_id": f"receipt:{thesis_id}:{run_id}",
            "recorded_at_utc": recorded_at_utc,
            "thesis_id": thesis_id,
            "run_id": run_id,
            "alert_artifact_id": alert_artifact_id,
            "e2e_run_id": disposition.get("e2e_run_id"),
            "sink": normalized_receipt["sink"],
            "delivery_status": normalized_receipt["delivery_status"],
            "delivery_proof": normalized_receipt["delivery_proof"],
        }
        receipt_path = receipts_root / f"{run_id}.json"
        receipt_path.write_text(json.dumps(receipt_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "ok",
        "decision": decision,
        "alert_artifact_path": _relative_path(alert_path, workspace_dir),
        "receipt_artifact_path": None if receipt_path is None else _relative_path(receipt_path, workspace_dir),
    }
