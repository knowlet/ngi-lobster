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
)


def _missing(value: Any) -> bool:
    return value is None or value == ""


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
        "e2e_run_id": alert_disposition.get("e2e_run_id"),
        "p_ai": runtime_data.get("first_principles_probability"),
        "market_yes_probability": target_detail.get("market_yes_probability"),
    }

    missing_fields = [field for field in REQUIRED_BASE_FIELDS if _missing(view[field])]

    if view["decision"] == "would_send" and _missing(alert_disposition.get("delivery_proof")):
        missing_fields.append("delivery_proof")

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
