from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


stub_runtime = types.ModuleType("lobster_runtime")
stub_runtime.TARGET_CONTRACT_MISMATCH_REASON = "legacy_target_mismatch"
stub_runtime.TARGET_CONTRACT_OK_REASON = "active_target_contract_ok"
stub_runtime.build_explanation = lambda data: data
stub_runtime.build_signature = lambda data, expl: {"data": data, "expl": expl}
stub_runtime.should_send_alert = lambda data, expl, prior_state: None
sys.modules.setdefault("lobster_runtime", stub_runtime)

MODULE_PATH = Path(__file__).resolve().parents[2] / "legacy" / "intelligence-model" / "run_ngi_monitor.py"
SPEC = importlib.util.spec_from_file_location("run_ngi_monitor", MODULE_PATH)
run_ngi_monitor = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(run_ngi_monitor)


def test_legacy_monitor_uses_repo_local_lobster_packages_by_default():
    expected = (Path(__file__).resolve().parents[2] / "lobster-intel" / "packages").resolve()
    assert run_ngi_monitor.LOBSTER_PACKAGES == expected
    assert str(expected / "lobster-core") in sys.path
    assert str(expected / "lobster-runtime") in sys.path
    assert str(expected / "lobster-delivery") in sys.path


def test_build_alert_contract_payload_maps_suppressed_novelty_reason_to_public_contract_code():
    payload = run_ngi_monitor._build_alert_contract_payload(
        {
            "timestamp_utc": "2026-04-25T22:32:45.343547+00:00",
            "market_target": {
                "market_id": "1517836",
                "market_name": "Trump announces end of military operations against Iran by June 30th",
            },
        },
        "suppressed",
        "no_novelty_within_24h",
    )

    disposition = payload["alert_disposition"]
    explain = payload["alert_explain_contract"]

    assert disposition["should_send"] is False
    assert disposition["decision"] == "suppressed"
    assert disposition["reason_code"] == "active_target_contract_ok"
    assert disposition["runtime_target_id"] == "1517836"
    assert disposition["alert_target_id"] == "1517836"
    assert disposition["target_contract_match"] is True
    assert disposition["contract_version"] == "legacy-monitor-contract-v1"
    assert disposition["e2e_run_id"] == "legacy-monitor-20260425T223245.343547Z"

    assert explain["reason_code"] == "active_target_contract_ok"
    assert explain["alert_target_id"] == "1517836"
    assert explain["e2e_run_id"] == disposition["e2e_run_id"]
    assert explain["internal_runtime_reason_code"] == "no_novelty_within_24h"


def test_build_alert_contract_payload_restores_live_contract_aliases():
    payload = run_ngi_monitor._build_alert_contract_payload(
        {
            "timestamp_utc": "2026-04-25T22:32:45.343547+00:00",
            "market_target": {
                "market_id": "1517836",
                "market_name": "Trump announces end of military operations against Iran by June 30th",
            },
            "first_principles_probability": 0.182944,
        },
        "suppressed",
        "no_novelty_within_24h",
        {"summary": "contract ok"},
    )

    assert payload["P_AI"] == 0.182944
    assert payload["explain"] == {"summary": "contract ok"}



def test_build_alert_contract_payload_keeps_legacy_mismatch_public_reason_code():
    payload = run_ngi_monitor._build_alert_contract_payload(
        {
            "timestamp_utc": "2026-04-25T22:32:45.343547+00:00",
            "market_target": {
                "market_id": "1517836",
                "market_name": "Trump announces end of military operations against Iran by June 30th",
            },
        },
        "suppressed",
        "legacy_target_mismatch",
    )

    disposition = payload["alert_disposition"]
    explain = payload["alert_explain_contract"]

    assert disposition["reason_code"] == "legacy_target_mismatch"
    assert explain["reason_code"] == "legacy_target_mismatch"
    assert explain["internal_runtime_reason_code"] == "legacy_target_mismatch"
