from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from verify_runtime_ops_health import build_summary


REQUIRED_TOP_LEVEL_KEYS = (
    "market_target",
    "target_detail",
    "first_principles_probability",
    "alert_disposition",
)


def _first_reason(payload: dict[str, Any]) -> str | None:
    explain = payload.get("explain")
    if not isinstance(explain, dict):
        return None
    reasons = explain.get("reasons")
    if isinstance(reasons, list):
        for item in reasons:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return None


def _canonical_contract_fallback(value: Any) -> str:
    if value is None:
        return "unknown"
    canonical = str(value).strip()
    return canonical or "unknown"


def _build_basis_lines(*, latest_ngi: dict[str, Any], ops_health: dict[str, Any]) -> dict[str, str]:
    alert_disposition = latest_ngi.get("alert_disposition") or {}
    decision = _canonical_contract_fallback(alert_disposition.get("decision"))
    reason_code = _canonical_contract_fallback(alert_disposition.get("reason_code"))
    logistics = _first_reason(latest_ngi) or f"live alert disposition {decision} / {reason_code}"
    energy = (
        "P_AI "
        f"{ops_health['first_principles_probability'] * 100:.2f}% vs market yes "
        f"{ops_health['market_yes_probability'] * 100:.2f}%"
    )
    if ops_health["blockers"]:
        key_statement = f"ops-health blockers: {', '.join(str(item) for item in ops_health['blockers'])}"
    else:
        key_statement = "ops-health pass"
    return {
        "logistics": logistics,
        "energy": energy,
        "key_statement": key_statement,
    }


def _require_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"latest_ngi.{key} must be a JSON object")
    return value


def _is_positive_delivery(alert_disposition: dict[str, Any]) -> bool:
    if "should_send" in alert_disposition:
        should_send = _as_bool(alert_disposition.get("should_send"))
        if should_send is None:
            raise RuntimeError(
                "latest_ngi.alert_disposition.should_send must be a boolean-equivalent value"
            )
        return should_send
    decision = str(alert_disposition.get("decision") or "").strip().lower()
    return decision in {"would_send", "sent", "delivered"}


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
        return None
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def _read_non_empty_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise RuntimeError(
            f"latest_ngi.alert_disposition.delivery_proof.{key} must be a non-empty string"
        )
    if not value.strip():
        return None
    return value


def _require_non_empty_string(payload: dict[str, Any], key: str, *, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def _validate_delivery_proof_fields(proof: dict[str, Any]) -> None:
    boundary = proof.get("boundary")
    if boundary is not None and boundary != "":
        if not isinstance(boundary, str) or not boundary.strip():
            raise RuntimeError(
                "latest_ngi.alert_disposition.delivery_proof.boundary must be a non-empty string"
            )
    _read_non_empty_string(proof, "proof_id")
    _read_non_empty_string(proof, "sink_message_id")


def _canonicalize_delivery_proof(proof: dict[str, Any]) -> dict[str, Any]:
    canonical = dict(proof)
    for key in ("boundary", "proof_id", "sink_message_id"):
        value = canonical.get(key)
        if isinstance(value, str):
            canonical[key] = value.strip()
    return canonical


def _require_delivery_proof(alert_disposition: dict[str, Any]) -> dict[str, Any] | None:
    proof = alert_disposition.get("delivery_proof")
    if proof is not None and not isinstance(proof, dict):
        raise RuntimeError("latest_ngi.alert_disposition.delivery_proof must be a JSON object")
    if proof is not None:
        _validate_delivery_proof_fields(proof)
    if not _is_positive_delivery(alert_disposition):
        return _canonicalize_delivery_proof(proof) if proof is not None else None
    if _as_bool(alert_disposition.get("target_contract_match")) is not True:
        raise RuntimeError("positive latest_ngi.alert_disposition.target_contract_match must be true")
    if proof is None:
        raise RuntimeError("missing latest_ngi.alert_disposition.delivery_proof")
    boundary = proof.get("boundary")
    if boundary is None or boundary == "":
        raise RuntimeError("missing latest_ngi.alert_disposition.delivery_proof.boundary")
    if not isinstance(boundary, str) or not boundary.strip():
        raise RuntimeError(
            "latest_ngi.alert_disposition.delivery_proof.boundary must be a non-empty string"
        )
    proof_id = _read_non_empty_string(proof, "proof_id") or _read_non_empty_string(
        proof, "sink_message_id"
    )
    if proof_id is None:
        raise RuntimeError("missing latest_ngi.alert_disposition.delivery_proof.proof_id")
    return _canonicalize_delivery_proof(proof)


def _validate_non_positive_contract_match(alert_disposition: dict[str, Any]) -> None:
    if _is_positive_delivery(alert_disposition):
        return
    if (
        "target_contract_match" in alert_disposition
        and _as_bool(alert_disposition.get("target_contract_match")) is None
    ):
        raise RuntimeError(
            "latest_ngi.alert_disposition.target_contract_match must be a boolean-equivalent value"
        )


def build_live_progress_sync_payload(
    state_path: Path,
    db_path: Path,
    latest_ngi_path: Path,
    runtime_source_path: Path | None = None,
) -> dict[str, Any]:
    try:
        latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("latest_ngi payload must be valid JSON") from exc
    if not isinstance(latest_ngi, dict):
        raise RuntimeError("latest_ngi payload must be a JSON object")
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in latest_ngi:
            raise RuntimeError(f"missing latest_ngi.{key}")

    market_target = _require_mapping(latest_ngi, "market_target")
    target_detail = _require_mapping(latest_ngi, "target_detail")
    alert_disposition = _require_mapping(latest_ngi, "alert_disposition")
    decision = _require_non_empty_string(
        alert_disposition, "decision", context="latest_ngi.alert_disposition"
    )
    delivery_proof = _require_delivery_proof(alert_disposition)
    _validate_non_positive_contract_match(alert_disposition)
    reason_code = _require_non_empty_string(
        alert_disposition, "reason_code", context="latest_ngi.alert_disposition"
    )
    market_question = _require_non_empty_string(
        target_detail, "market_question", context="latest_ngi.target_detail"
    )
    contract_version = _require_non_empty_string(
        alert_disposition, "contract_version", context="latest_ngi.alert_disposition"
    )
    e2e_run_id = _require_non_empty_string(
        alert_disposition, "e2e_run_id", context="latest_ngi.alert_disposition"
    )
    ops_health = build_summary(state_path, db_path, latest_ngi_path, runtime_source_path)
    if ops_health["latest_ngi_stale"]:
        raise RuntimeError("latest_ngi.json is stale")
    basis = _build_basis_lines(latest_ngi=latest_ngi, ops_health=ops_health)
    should_send = (
        _as_bool(alert_disposition.get("should_send"))
        if "should_send" in alert_disposition
        else None
    )
    target_contract_match = (
        _as_bool(alert_disposition.get("target_contract_match"))
        if "target_contract_match" in alert_disposition
        else None
    )

    alert_payload = {
        "decision": decision,
        "should_send": should_send,
        "reason_code": reason_code,
        "target_contract_match": target_contract_match,
        "contract_version": contract_version,
        "e2e_run_id": e2e_run_id,
    }
    if delivery_proof is not None:
        alert_payload["delivery_proof"] = delivery_proof

    return {
        "sync_status": "blocking" if ops_health["status"] != "pass" else "ready",
        "sync_blocked": ops_health["status"] != "pass",
        "blocking_summary": {
            "runtime_target_id": ops_health["market_target_id"],
            "market_question": market_question,
            "reselection_required": ops_health["reselection_required"],
            "next_contract_action": ops_health["next_contract_action"],
            "rollover_candidate_blocker": ops_health["rollover_candidate_blocker"],
            "rollover_candidate": ops_health["rollover_candidate"],
        },
        "market_target": {
            "market_id": ops_health["market_target_id"],
            "market_name": ops_health["market_target_name"],
            "market_question": market_question,
            "probability_mode": ops_health["probability_mode"],
        },
        "alert_disposition": alert_payload,
        "probabilities": {
            "p_ai": ops_health["first_principles_probability"],
            "market_yes_probability": ops_health["market_yes_probability"],
        },
        "divergence": {
            "divergence_pp": ops_health["divergence_pp"],
            "direction": ops_health["direction"],
            "first_principles_minus_market_pp": ops_health["first_principles_minus_market_pp"],
            "threshold_pp": ops_health["divergence_threshold_pp"],
            "blocking": ops_health["divergence_blocking"],
        },
        "active_target": {
            "market_closed": ops_health["market_closed"],
            "market_accepting_orders": ops_health["market_accepting_orders"],
            "closed_target_blocking": ops_health["closed_target_blocking"],
            "reselection_required": ops_health["reselection_required"],
            "next_contract_action": ops_health["next_contract_action"],
            "rollover_candidate_blocker": ops_health["rollover_candidate_blocker"],
            "rollover_candidate": ops_health["rollover_candidate"],
        },
        "active_target_reselection": ops_health["active_target_reselection"],
        "freshness": {
            "dq_status": ops_health["dq_status"],
            "latest_snapshot_at_utc": ops_health["latest_snapshot_at_utc"],
            "freshness_hours": ops_health["freshness_hours"],
            "freshness_threshold_hours": ops_health["freshness_threshold_hours"],
            "stale_data": ops_health["stale_data"],
            "latest_ngi_timestamp_utc": ops_health["latest_ngi_timestamp_utc"],
            "latest_ngi_age_hours": ops_health["latest_ngi_age_hours"],
            "latest_ngi_threshold_hours": ops_health["latest_ngi_threshold_hours"],
            "latest_ngi_stale": ops_health["latest_ngi_stale"],
        },
        "contract_action": {
            "reselection_required": ops_health["reselection_required"],
            "next_contract_action": ops_health["next_contract_action"],
            "rollover_candidate": ops_health["rollover_candidate"],
            "rollover_candidate_blocker": ops_health["rollover_candidate_blocker"],
        },
        "blockers": list(ops_health["blockers"]),
        "basis_lines": basis,
    }


def main(argv: list[str]) -> int:
    if len(argv) not in {4, 5}:
        print(
            "usage: build_live_progress_sync_payload.py <state.yaml> <intelligence_store.sqlite> <latest_ngi.json> [runtime_source_polymarket.json]",
            file=sys.stderr,
        )
        return 2

    state_path = Path(argv[1])
    db_path = Path(argv[2])
    latest_ngi_path = Path(argv[3])
    runtime_source_path = Path(argv[4]) if len(argv) == 5 else None

    try:
        payload = build_live_progress_sync_payload(state_path, db_path, latest_ngi_path, runtime_source_path)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
