from __future__ import annotations

from typing import Any


REQUIRED_BASE_FIELDS = (
    "should_send",
    "decision",
    "reason_code",
    "runtime_target_id",
    "runtime_target_name",
    "alert_target_id",
    "contract_version",
    "e2e_run_id",
    "p_ai",
    "market_yes_probability",
)

E2E_RUN_ID_ALIASES = (
    "e2e_run_id",
    "e2e_bundle_id",
)

REQUIRED_BUNDLE_DECISIONS = (
    "suppressed",
    "would_send",
)

DELIVERY_PROOF_ID_FIELDS = (
    "sink_message_id",
    "delivery_event_id",
    "external_receipt_id",
)

REQUIRED_COMPARE_FIELDS = (
    "runtime_target_id",
    "runtime_target_name",
    "market_question",
    "probability_mode",
    "p_ai",
    "market_implied_probability",
    "divergence_pp",
    "runtime_timestamp_utc",
    "logistics",
    "energy",
    "key_statement",
)


def _missing(value: Any) -> bool:
    return value is None or value == ""


def _first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if not _missing(value):
            return value
    return None


def _validate_delivery_proof(delivery_proof: Any) -> list[str]:
    if _missing(delivery_proof):
        return ["delivery_proof"]
    if not isinstance(delivery_proof, dict):
        return ["delivery_proof.boundary", "delivery_proof.proof_id"]

    missing_fields: list[str] = []
    if _missing(delivery_proof.get("boundary")):
        missing_fields.append("delivery_proof.boundary")

    proof_ids = [_first_present(delivery_proof, *DELIVERY_PROOF_ID_FIELDS)]
    if all(_missing(value) for value in proof_ids):
        missing_fields.append("delivery_proof.proof_id")

    return missing_fields


def _coerce_probability(value: Any) -> float | None:
    if _missing(value):
        return None
    return float(value)


def _resolve_market_implied_probability(target_detail: dict[str, Any]) -> float | None:
    market_yes_probability = _coerce_probability(target_detail.get("market_yes_probability"))
    if market_yes_probability is None:
        return None

    probability_mode = target_detail.get("probability_mode") or "yes_is_peace"
    if probability_mode == "yes_is_escalation":
        return market_yes_probability
    if probability_mode == "yes_is_peace":
        return 1.0 - market_yes_probability
    raise ValueError(f"unsupported probability_mode: {probability_mode}")


def build_alert_contract_view(runtime_data: dict[str, Any]) -> dict[str, Any]:
    alert_disposition = runtime_data.get("alert_disposition") or {}
    market_target = runtime_data.get("market_target") or {}
    target_detail = runtime_data.get("target_detail") or {}

    view = {
        "should_send": alert_disposition.get("should_send"),
        "decision": alert_disposition.get("decision"),
        "reason_code": alert_disposition.get("reason_code"),
        "runtime_target_id": alert_disposition.get("runtime_target_id")
        or market_target.get("market_id")
        or market_target.get("market_slug"),
        "runtime_target_name": alert_disposition.get("runtime_target_name")
        or market_target.get("market_name")
        or market_target.get("market_question"),
        "alert_target_id": alert_disposition.get("alert_target_id"),
        "contract_version": alert_disposition.get("contract_version"),
        "e2e_run_id": _first_present(alert_disposition, *E2E_RUN_ID_ALIASES),
        "p_ai": runtime_data.get("first_principles_probability"),
        "market_yes_probability": target_detail.get("market_yes_probability"),
    }

    missing_fields = [field for field in REQUIRED_BASE_FIELDS if _missing(view[field])]

    if view["decision"] == "would_send":
        missing_fields.extend(_validate_delivery_proof(alert_disposition.get("delivery_proof")))

    if missing_fields:
        return {
            "status": "contract_incomplete",
            "missing_fields": missing_fields,
            "view": view,
        }

    if alert_disposition.get("delivery_proof") is not None:
        view["delivery_proof"] = alert_disposition.get("delivery_proof")

    return {
        "status": "ok",
        "view": view,
    }


def build_active_target_compare_view(runtime_data: dict[str, Any]) -> dict[str, Any]:
    market_target = runtime_data.get("market_target") or {}
    target_detail = runtime_data.get("target_detail") or {}
    evidence_basis = ((runtime_data.get("alert_explain_contract") or {}).get("evidence_basis") or {})

    try:
        market_implied_probability = _resolve_market_implied_probability(target_detail)
    except ValueError as exc:
        return {
            "status": "contract_incomplete",
            "missing_fields": ["probability_mode"],
            "error": str(exc),
        }

    p_ai = _coerce_probability(runtime_data.get("first_principles_probability"))
    divergence_pp = None
    if p_ai is not None and market_implied_probability is not None:
        divergence_pp = round((p_ai - market_implied_probability) * 100, 2)

    view = {
        "runtime_target_id": market_target.get("market_id") or market_target.get("market_slug"),
        "runtime_target_name": market_target.get("market_name") or market_target.get("market_question"),
        "market_question": target_detail.get("market_question") or market_target.get("market_name"),
        "probability_mode": target_detail.get("probability_mode") or "yes_is_peace",
        "p_ai": p_ai,
        "market_yes_probability": _coerce_probability(target_detail.get("market_yes_probability")),
        "market_implied_probability": round(market_implied_probability, 6) if market_implied_probability is not None else None,
        "divergence_pp": divergence_pp,
        "runtime_timestamp_utc": runtime_data.get("timestamp_utc"),
        "logistics": evidence_basis.get("logistics"),
        "energy": evidence_basis.get("energy"),
        "key_statement": evidence_basis.get("key_statement"),
    }

    missing_fields = [field for field in REQUIRED_COMPARE_FIELDS if _missing(view[field])]
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


def build_e2e_contract_bundle_view(runtime_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    fixtures = [build_alert_contract_view(payload) for payload in runtime_payloads]
    issues: list[str] = []

    if len(fixtures) != len(REQUIRED_BUNDLE_DECISIONS):
        issues.append("bundle_size_mismatch")

    ok_views = [fixture["view"] for fixture in fixtures if fixture["status"] == "ok"]
    decisions = {view.get("decision") for view in ok_views}

    for decision in REQUIRED_BUNDLE_DECISIONS:
        if decision not in decisions:
            issues.append(f"missing_decision:{decision}")

    shared_values = {
        "contract_version": {view.get("contract_version") for view in ok_views},
        "e2e_run_id": {view.get("e2e_run_id") for view in ok_views},
    }
    for field, values in shared_values.items():
        present_values = {value for value in values if not _missing(value)}
        if len(present_values) > 1:
            issues.append(f"shared_field_mismatch:{field}")

    incomplete_indexes = [index for index, fixture in enumerate(fixtures) if fixture["status"] != "ok"]
    if incomplete_indexes:
        issues.append("incomplete_fixture")

    if issues:
        return {
            "status": "bundle_incomplete",
            "issues": issues,
            "fixtures": fixtures,
        }

    return {
        "status": "ok",
        "bundle": {
            "contract_version": ok_views[0]["contract_version"],
            "e2e_run_id": ok_views[0]["e2e_run_id"],
            "fixtures": ok_views,
        },
    }
