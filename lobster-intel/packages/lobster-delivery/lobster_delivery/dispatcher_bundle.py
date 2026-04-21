from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contract import build_e2e_contract_bundle_view


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _now_utc_iso(now_utc: str | None) -> str:
    if now_utc:
        return now_utc
    return datetime.now(UTC).isoformat()


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _load_json(path)


def _project_runtime_dispatcher_payload(
    *,
    workspace_dir: str | Path,
    thesis_id: str,
    run_id: str,
    bundle_id: str,
    alert_payload: dict[str, Any],
) -> dict[str, Any]:
    workspace_dir = Path(workspace_dir)
    runtime_root = workspace_dir / "lobster-intel" / "data" / "runtime" / thesis_id
    delivery_root = workspace_dir / "lobster-intel" / "data" / "delivery" / thesis_id

    runtime_payload = _load_optional_json(runtime_root / "runs" / f"{run_id}.json") or {}
    compare_payload = _load_optional_json(runtime_root / "compare" / f"{run_id}.json") or {}
    receipt_payload = _load_optional_json(delivery_root / "receipts" / f"{run_id}.json") or {}

    active_target = runtime_payload.get("active_target") or {}
    disposition = {
        "should_send": alert_payload.get("should_send"),
        "decision": "would_send" if alert_payload.get("should_send") else "suppressed",
        "reason_code": alert_payload.get("reason_code"),
        "runtime_target_id": compare_payload.get("runtime_target_id")
        or active_target.get("market_id")
        or active_target.get("market_slug"),
        "runtime_target_name": active_target.get("market_name")
        or active_target.get("market_question"),
        "alert_target_id": compare_payload.get("market_target_id") or compare_payload.get("runtime_target_id"),
        "contract_version": alert_payload.get("contract_version") or runtime_payload.get("contract_version"),
        "e2e_run_id": bundle_id,
    }
    if receipt_payload.get("delivery_proof") is not None:
        disposition["delivery_proof"] = receipt_payload.get("delivery_proof")

    return {
        **alert_payload,
        "alert_disposition": disposition,
        "market_target": active_target,
        "target_detail": {
            "market_yes_probability": runtime_payload.get("market_implied_probability"),
        },
        "first_principles_probability": runtime_payload.get("P_AI"),
    }


def load_dispatcher_payloads(
    workspace_dir: str | Path,
    thesis_id: str,
    run_ids: list[str],
    *,
    bundle_id: str,
) -> list[dict[str, Any]]:
    alerts_root = Path(workspace_dir) / "lobster-intel" / "data" / "delivery" / thesis_id / "alerts"
    payloads: list[dict[str, Any]] = []
    for run_id in run_ids:
        alert_payload = _load_json(alerts_root / f"{run_id}.json")
        disposition = alert_payload.get("alert_disposition")
        if isinstance(disposition, dict) and disposition.get("e2e_run_id"):
            payloads.append(alert_payload)
            continue
        if isinstance(disposition, dict):
            patched_payload = dict(alert_payload)
            patched_payload["alert_disposition"] = {**disposition, "e2e_run_id": bundle_id}
            payloads.append(patched_payload)
            continue
        payloads.append(
            _project_runtime_dispatcher_payload(
                workspace_dir=workspace_dir,
                thesis_id=thesis_id,
                run_id=run_id,
                bundle_id=bundle_id,
                alert_payload=alert_payload,
            )
        )
    return payloads


def write_dispatcher_e2e_bundle(
    *,
    workspace_dir: str | Path,
    thesis_id: str,
    run_ids: list[str],
    bundle_id: str,
    now_utc: str | None = None,
) -> dict[str, Any]:
    payloads = load_dispatcher_payloads(workspace_dir, thesis_id, run_ids, bundle_id=bundle_id)
    result = build_e2e_contract_bundle_view(payloads)
    if result.get("status") != "ok":
        raise ValueError(f"dispatcher bundle incomplete: {result}")

    resolved_bundle_id = str(result["bundle"].get("e2e_run_id") or "")
    if resolved_bundle_id != bundle_id:
        raise ValueError(f"shared e2e_run_id mismatch: expected {bundle_id}, got {resolved_bundle_id}")

    artifact_payload = {
        "schema": "lobster.delivery.dispatcher_e2e_bundle.v1",
        "recorded_at_utc": _now_utc_iso(now_utc),
        "thesis_id": thesis_id,
        "run_ids": list(run_ids),
        "contract_version": result["bundle"]["contract_version"],
        "e2e_run_id": resolved_bundle_id,
        "fixtures": result["bundle"]["fixtures"],
    }
    artifact_relpath = Path("lobster-intel") / "data" / "delivery" / thesis_id / "bundles" / f"{bundle_id}.json"
    artifact_path = Path(workspace_dir) / artifact_relpath
    _write_json(artifact_path, artifact_payload)

    return {
        "status": "ok",
        "bundle": result["bundle"],
        "bundle_artifact_path": artifact_relpath.as_posix(),
    }


def load_dispatcher_e2e_bundle(workspace_dir: str | Path, thesis_id: str, bundle_id: str) -> dict[str, Any]:
    artifact_path = Path(workspace_dir) / "lobster-intel" / "data" / "delivery" / thesis_id / "bundles" / f"{bundle_id}.json"
    return _load_json(artifact_path)
