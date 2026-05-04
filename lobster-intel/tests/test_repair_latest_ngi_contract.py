from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
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


def test_repair_payload_marks_mismatched_target_ids_false():
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
            "alert_target_id": "wrong-target",
        },
        "alert_explain_contract": {
            "disposition": "suppressed",
            "reason_code": "no_novelty_within_24h",
        },
    }

    repaired = repair_latest_ngi_contract.repair_payload(payload)

    disposition = repaired["alert_disposition"]
    explain = repaired["alert_explain_contract"]
    assert disposition["alert_target_id"] == "wrong-target"
    assert disposition["target_contract_match"] is False
    assert explain["target_contract_match"] is False


def test_repair_payload_preserves_string_false_target_contract_match():
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
            "alert_target_id": "wrong-target",
            "target_contract_match": "false",
        },
        "alert_explain_contract": {
            "disposition": "suppressed",
            "reason_code": "no_novelty_within_24h",
        },
    }

    repaired = repair_latest_ngi_contract.repair_payload(payload)

    disposition = repaired["alert_disposition"]
    explain = repaired["alert_explain_contract"]
    assert disposition["reason_code"] == "active_target_contract_ok"
    assert disposition["internal_runtime_reason_code"] == "no_novelty_within_24h"
    assert disposition["target_contract_match"] is False
    assert explain["target_contract_match"] is False


def test_repair_latest_ngi_contract_cli_uses_env_default_path(tmp_path: Path):
    payload_path = tmp_path / "latest_ngi.json"
    payload_path.write_text(
        json.dumps(
            {
                "timestamp_utc": "2026-04-25T12:55:30.291168+00:00",
                "market_target": {"market_id": "1517836", "market_name": "Target"},
                "alert_disposition": {"should_send": False, "decision": "suppressed", "reason_code": "no_novelty_within_24h"},
                "alert_explain_contract": {"disposition": "suppressed", "reason_code": "no_novelty_within_24h"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    env = {**os.environ, "LOBSTER_LATEST_NGI_PATH": str(payload_path)}
    subprocess.run(
        [sys.executable, str(MODULE_PATH)],
        cwd=MODULE_PATH.parents[2],
        env=env,
        check=True,
    )

    repaired = json.loads(payload_path.read_text(encoding="utf-8"))
    assert repaired["alert_disposition"]["reason_code"] == "active_target_contract_ok"
    assert repaired["alert_disposition"]["alert_target_id"] == "1517836"


def test_resolve_paths_uses_default_path_when_argv_omitted(monkeypatch):
    monkeypatch.delenv("LOBSTER_LATEST_NGI_PATH", raising=False)

    input_path, output_path = repair_latest_ngi_contract.resolve_paths(["repair_latest_ngi_contract.py"])

    assert input_path == repair_latest_ngi_contract.DEFAULT_LATEST_NGI_PATH
    assert output_path == repair_latest_ngi_contract.DEFAULT_LATEST_NGI_PATH
