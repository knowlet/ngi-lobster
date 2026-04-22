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
    "receipt.sink",
    "receipt.delivery_status",
    "receipt.delivery_proof",
)

REQUIRED_TARGET_AUDIT_FIELDS = (
    "latest_run_id",
    "latest_target.market_id",
    "audited_run_id",
    "audited_target.market_id",
    "compare.runtime_target_id",
    "alert.reason_code",
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


def _target_view(payload: dict[str, Any] | None) -> dict[str, Any]:
    target = payload or {}
    return {
        "market_id": target.get("market_id"),
        "market_slug": target.get("market_slug"),
        "market_question": target.get("market_question") or target.get("market_name"),
    }


def _target_identity(target: dict[str, Any]) -> Any:
    return (
        target.get("market_id"),
        target.get("market_slug"),
        target.get("market_question"),
    )
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


def build_runtime_target_audit_view(
    *,
    latest_runtime_snapshot: dict[str, Any],
    runtime_snapshot: dict[str, Any],
    compare_artifact: dict[str, Any],
    alert_artifact: dict[str, Any],
) -> dict[str, Any]:
    latest_target = _target_view(latest_runtime_snapshot.get("active_target"))
    audited_target = _target_view(runtime_snapshot.get("active_target"))
    compare_view = {
        "artifact_id": compare_artifact.get("artifact_id"),
        "runtime_target_id": compare_artifact.get("runtime_target_id"),
        "market_target_id": compare_artifact.get("market_target_id"),
    }
    alert_view = {
        "artifact_id": alert_artifact.get("artifact_id"),
        "should_send": alert_artifact.get("should_send"),
        "reason_code": alert_artifact.get("reason_code"),
    }

    view = {
        "latest_run_id": latest_runtime_snapshot.get("run_id"),
        "latest_target": latest_target,
        "audited_run_id": runtime_snapshot.get("run_id"),
        "audited_target": audited_target,
        "compare": compare_view,
        "alert": alert_view,
        "same_target_as_latest": False,
    }

    missing_fields = [field for field in REQUIRED_TARGET_AUDIT_FIELDS if _missing(_read_nested(view, field))]
    if missing_fields:
        return {
            "status": "audit_incomplete",
            "missing_fields": missing_fields,
            "view": view,
        }

    issues: list[str] = []
    latest_identity = _target_identity(latest_target)
    audited_identity = _target_identity(audited_target)
    if latest_identity != audited_identity:
        issues.append("runtime.active_target_mismatch_latest")
    if compare_view["runtime_target_id"] != latest_target["market_id"]:
        issues.append("compare.runtime_target_id_mismatch_latest")
    if bool(alert_view["should_send"]) and compare_view["market_target_id"] != latest_target["market_id"]:
        issues.append("compare.market_target_id_mismatch_latest")

    view["same_target_as_latest"] = not issues
    if issues:
        return {
            "status": "audit_failed",
            "issues": issues,
            "view": view,
        }

    return {
        "status": "ok",
        "view": view,
    }


def load_runtime_target_audit(workspace_dir: str | Path, thesis_id: str, run_id: str) -> dict[str, Any]:
    workspace_dir = Path(workspace_dir)
    runtime_root = workspace_dir / "lobster-intel" / "data" / "runtime" / thesis_id
    delivery_root = workspace_dir / "lobster-intel" / "data" / "delivery" / thesis_id
    return build_runtime_target_audit_view(
        latest_runtime_snapshot=_load_json(runtime_root / "latest.json"),
        runtime_snapshot=_load_json(runtime_root / "runs" / f"{run_id}.json"),
        compare_artifact=_load_json(runtime_root / "compare" / f"{run_id}.json"),
        alert_artifact=_load_json(delivery_root / "alerts" / f"{run_id}.json"),
    )
