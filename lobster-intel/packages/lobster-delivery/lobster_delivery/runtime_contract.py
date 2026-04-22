from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DELIVERY_PROOF_ID_FIELDS = (
    "proof_id",
    "sink_message_id",
    "delivery_event_id",
    "external_receipt_id",
)

REQUIRED_RUNTIME_FIELDS = (
    "runtime.artifact_id",
    "runtime.compare_mode",
    "runtime.active_target",
    "runtime.P_AI",
    "runtime.market_implied_probability",
    "runtime.ngi_gap",
    "compare.artifact_id",
    "compare.compare_mode",
    "alert.artifact_id",
    "alert.should_send",
    "alert.reason_code",
    "receipt.artifact_id",
    "receipt.alert_artifact_id",
    "receipt.sink",
    "receipt.delivery_status",
    "receipt.delivery_proof",
)


def _missing(value: Any) -> bool:
    return value is None or value == ""


def _first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if not _missing(value):
            return value
    return None


def _normalize_delivery_proof(delivery_proof: Any) -> Any:
    if not isinstance(delivery_proof, dict):
        return delivery_proof

    normalized = dict(delivery_proof)
    proof_id = _first_present(normalized, *DELIVERY_PROOF_ID_FIELDS)
    if not _missing(proof_id):
        normalized["proof_id"] = proof_id
    return normalized


def _read_nested(view: dict[str, Any], dotted_path: str) -> Any:
    value: Any = view
    for part in dotted_path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_runtime_contract_view(
    *,
    runtime_snapshot: dict[str, Any],
    compare_artifact: dict[str, Any],
    alert_artifact: dict[str, Any],
    delivery_receipt: dict[str, Any],
) -> dict[str, Any]:
    view = {
        "runtime": {
            "artifact_id": runtime_snapshot.get("artifact_id"),
            "compare_mode": runtime_snapshot.get("compare_mode"),
            "active_target": runtime_snapshot.get("active_target"),
            "P_AI": runtime_snapshot.get("P_AI"),
            "market_implied_probability": runtime_snapshot.get("market_implied_probability"),
            "ngi_gap": runtime_snapshot.get("ngi_gap"),
        },
        "compare": {
            "artifact_id": compare_artifact.get("artifact_id"),
            "compare_mode": compare_artifact.get("compare_mode"),
            "runtime_target_id": compare_artifact.get("runtime_target_id"),
            "market_target_id": compare_artifact.get("market_target_id"),
            "fallback_reason_codes": compare_artifact.get("fallback_reason_codes"),
        },
        "alert": {
            "artifact_id": alert_artifact.get("artifact_id"),
            "should_send": alert_artifact.get("should_send"),
            "reason_code": alert_artifact.get("reason_code"),
            "compare_artifact_id": alert_artifact.get("compare_artifact_id"),
        },
        "receipt": {
            "artifact_id": delivery_receipt.get("artifact_id"),
            "sink": delivery_receipt.get("sink"),
            "delivery_status": delivery_receipt.get("delivery_status"),
            "alert_artifact_id": delivery_receipt.get("alert_artifact_id"),
            "delivery_proof": _normalize_delivery_proof(delivery_receipt.get("delivery_proof")),
        },
    }

    missing_fields = [field for field in REQUIRED_RUNTIME_FIELDS if _missing(_read_nested(view, field))]
    proof = view["receipt"]["delivery_proof"]
    if not _missing(proof) and _missing((proof or {}).get("boundary")):
        missing_fields.append("receipt.delivery_proof.boundary")
    if not _missing(proof) and _missing((proof or {}).get("proof_id")):
        missing_fields.append("receipt.delivery_proof.proof_id")
    if (
        not _missing(view["receipt"]["alert_artifact_id"])
        and not _missing(view["alert"]["artifact_id"])
        and view["receipt"]["alert_artifact_id"] != view["alert"]["artifact_id"]
    ):
        missing_fields.append("receipt.alert_artifact_id_mismatch")

    if missing_fields:
        return {
            "status": "contract_incomplete",
            "missing_fields": missing_fields,
            "view": view,
        }

    return {
        "status": "ok",
        "view": view,
    }


def load_runtime_contract_bundle(workspace_dir: str | Path, thesis_id: str, run_id: str) -> dict[str, Any]:
    workspace_dir = Path(workspace_dir)
    runtime_root = workspace_dir / "lobster-intel" / "data" / "runtime" / thesis_id
    delivery_root = workspace_dir / "lobster-intel" / "data" / "delivery" / thesis_id
    return build_runtime_contract_view(
        runtime_snapshot=_load_json(runtime_root / "runs" / f"{run_id}.json"),
        compare_artifact=_load_json(runtime_root / "compare" / f"{run_id}.json"),
        alert_artifact=_load_json(delivery_root / "alerts" / f"{run_id}.json"),
        delivery_receipt=_load_json(delivery_root / "receipts" / f"{run_id}.json"),
    )
