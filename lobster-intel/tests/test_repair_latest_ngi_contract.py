from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "repair_latest_ngi_contract.py"
SPEC = importlib.util.spec_from_file_location("repair_latest_ngi_contract", MODULE_PATH)
repair_latest_ngi_contract = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(repair_latest_ngi_contract)


def test_repair_payload_backfills_legacy_live_contract_envelope():
    payload = {
        "timestamp_utc": "2026-04-25T12:55:30.291168+00:00",
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "alert_disposition": {
            "should_send": False,
            "decision": "suppressed",
            "reason_code": "no_novelty_within_24h",
        },
        "alert_explain_contract": {
            "disposition": "suppressed",
            "reason_code": "no_novelty_within_24h",
        },
    }

    repaired = repair_latest_ngi_contract.repair_payload(payload)

    disposition = repaired["alert_disposition"]
    explain = repaired["alert_explain_contract"]
    assert repaired["contract_version"] == "legacy-monitor-contract-v1"
    assert disposition["reason_code"] == "active_target_contract_ok"
    assert disposition["internal_runtime_reason_code"] == "no_novelty_within_24h"
    assert disposition["runtime_target_id"] == "1517836"
    assert disposition["alert_target_id"] == "1517836"
    assert disposition["target_contract_match"] is True
    assert disposition["contract_version"] == "legacy-monitor-contract-v1"
    assert disposition["e2e_run_id"] == "legacy-monitor-20260425T125530.291168Z"

    assert explain["reason_code"] == "active_target_contract_ok"
    assert explain["internal_runtime_reason_code"] == "no_novelty_within_24h"
    assert explain["alert_target_id"] == "1517836"
    assert explain["target_contract_match"] is True
    assert explain["e2e_run_id"] == disposition["e2e_run_id"]
