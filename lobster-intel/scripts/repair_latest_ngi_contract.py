#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_CONTRACT_VERSION = "legacy-monitor-contract-v1"
SUPPRESSED_REASON_MAP = {
    "no_novelty_within_24h": "active_target_contract_ok",
    "cooldown_elapsed_but_no_new_thesis": "active_target_contract_ok",
}


def _resolve_run_id(timestamp_utc: Any) -> str | None:
    timestamp = str(timestamp_utc or "").strip()
    if not timestamp:
        return None
    return (
        "legacy-monitor-"
        + timestamp.replace(":", "").replace("-", "").replace("+00:00", "Z").replace("+0000", "Z")
    )


def _resolve_target(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    target = payload.get("market_target") or {}
    runtime_target_id = target.get("market_id") or target.get("market_slug")
    runtime_target_name = target.get("market_name") or target.get("market_question")
    return (
        str(runtime_target_id).strip() or None if runtime_target_id is not None else None,
        str(runtime_target_name).strip() or None if runtime_target_name is not None else None,
    )


def _resolve_target_contract_match(
    existing_match: Any,
    alert_target_id: Any,
    runtime_target_id: str | None,
) -> bool | None:
    if existing_match is not None:
        return bool(existing_match)

    normalized_alert_target_id = str(alert_target_id).strip() or None if alert_target_id is not None else None
    if runtime_target_id and normalized_alert_target_id:
        return normalized_alert_target_id == runtime_target_id
    if runtime_target_id:
        return True
    return None


def repair_payload(payload: dict[str, Any]) -> dict[str, Any]:
    repaired = deepcopy(payload)
    disposition = dict(repaired.get("alert_disposition") or {})
    explain = dict(repaired.get("alert_explain_contract") or {})

    runtime_target_id, runtime_target_name = _resolve_target(repaired)
    contract_version = str(repaired.get("contract_version") or disposition.get("contract_version") or DEFAULT_CONTRACT_VERSION)
    e2e_run_id = disposition.get("e2e_run_id") or explain.get("e2e_run_id") or _resolve_run_id(repaired.get("timestamp_utc"))
    internal_reason = str(disposition.get("reason_code") or explain.get("reason_code") or "").strip() or None
    public_reason = SUPPRESSED_REASON_MAP.get(internal_reason, internal_reason)
    alert_target_id = disposition.get("alert_target_id") or runtime_target_id
    target_contract_match = _resolve_target_contract_match(
        disposition.get("target_contract_match"),
        alert_target_id,
        runtime_target_id,
    )

    disposition.update(
        {
            "runtime_target_id": runtime_target_id,
            "runtime_target_name": runtime_target_name,
            "alert_target_id": alert_target_id,
            "target_contract_match": target_contract_match,
            "contract_version": contract_version,
            "e2e_run_id": e2e_run_id,
            "reason_code": public_reason,
        }
    )
    if internal_reason and internal_reason != public_reason:
        disposition["internal_runtime_reason_code"] = internal_reason

    explain.update(
        {
            "disposition": explain.get("disposition") or disposition.get("decision"),
            "reason_code": public_reason,
            "runtime_target_id": explain.get("runtime_target_id") or runtime_target_id,
            "runtime_target_name": explain.get("runtime_target_name") or runtime_target_name,
            "alert_target_id": explain.get("alert_target_id") or disposition.get("alert_target_id"),
            "target_contract_match": explain.get("target_contract_match", disposition.get("target_contract_match")),
            "contract_version": explain.get("contract_version") or contract_version,
            "e2e_run_id": explain.get("e2e_run_id") or e2e_run_id,
        }
    )
    if internal_reason:
        explain["internal_runtime_reason_code"] = explain.get("internal_runtime_reason_code") or internal_reason

    repaired["contract_version"] = repaired.get("contract_version") or contract_version
    repaired["alert_disposition"] = disposition
    repaired["alert_explain_contract"] = explain
    return repaired


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print("usage: repair_latest_ngi_contract.py <input.json> [output.json]", file=sys.stderr)
        return 2

    input_path = Path(argv[1])
    output_path = Path(argv[2]) if len(argv) == 3 else input_path
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    repaired = repair_payload(payload)
    output_path.write_text(json.dumps(repaired, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"input": str(input_path), "output": str(output_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
