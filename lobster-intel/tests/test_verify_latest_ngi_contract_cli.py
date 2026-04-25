import json
import os
import subprocess
import sys
from pathlib import Path


def test_verify_latest_ngi_contract_cli_accepts_on_contract_payload(tmp_path: Path):
    repo = Path(__file__).resolve().parents[2]
    payload = {
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {
            "market_yes_probability": 0.42,
        },
        "first_principles_probability": 0.23,
        "alert_disposition": {
            "should_send": False,
            "decision": "suppressed",
            "reason_code": "legacy_target_mismatch",
            "runtime_target_id": "1517836",
            "runtime_target_name": "Trump announces end of military operations against Iran by June 30th",
            "alert_target_id": "1517836",
            "target_contract_match": True,
            "contract_version": "v1",
            "e2e_run_id": "bundle-20260425-01",
        },
        "alert_explain_contract": {
            "disposition": "suppressed",
            "reason_code": "legacy_target_mismatch",
        },
    }
    payload_path = tmp_path / "latest_ngi.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "lobster-intel/scripts/verify_latest_ngi_contract.py",
            str(payload_path),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["status"] == "ok"
    assert output["issues"] == []
    assert output["probable_sync_blocker"] is None


def test_verify_latest_ngi_contract_cli_uses_env_or_default_path_when_arg_omitted(tmp_path: Path):
    repo = Path(__file__).resolve().parents[2]
    payload = {
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {
            "market_yes_probability": 0.42,
        },
        "first_principles_probability": 0.23,
        "alert_disposition": {
            "should_send": False,
            "decision": "suppressed",
            "reason_code": "legacy_target_mismatch",
            "runtime_target_id": "1517836",
            "runtime_target_name": "Trump announces end of military operations against Iran by June 30th",
            "alert_target_id": "1517836",
            "target_contract_match": True,
            "contract_version": "v1",
            "e2e_run_id": "bundle-20260425-01",
        },
        "alert_explain_contract": {
            "disposition": "suppressed",
            "reason_code": "legacy_target_mismatch",
        },
    }
    payload_path = tmp_path / "latest_ngi.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    env = {**os.environ, "LOBSTER_LATEST_NGI_PATH": str(payload_path)}
    result = subprocess.run(
        [sys.executable, "lobster-intel/scripts/verify_latest_ngi_contract.py"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["status"] == "ok"
    assert output["path"] == str(payload_path)


def test_verify_latest_ngi_contract_cli_fails_off_contract_reason_code(tmp_path: Path):
    repo = Path(__file__).resolve().parents[2]
    payload = {
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {
            "market_yes_probability": 0.645,
        },
        "first_principles_probability": 0.87,
        "alert_disposition": {
            "should_send": False,
            "decision": "suppressed",
            "reason_code": "target_contract_market_slug_mismatch",
            "runtime_target_id": "1517836",
            "runtime_target_name": "Trump announces end of military operations against Iran by June 30th",
            "alert_target_id": "1517836",
            "target_contract_match": True,
            "contract_version": "v1",
            "e2e_run_id": "bundle-20260425-01",
        },
        "alert_explain_contract": {
            "disposition": "suppressed",
            "reason_code": "target_contract_market_slug_mismatch",
        },
    }
    payload_path = tmp_path / "latest_ngi.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "lobster-intel/scripts/verify_latest_ngi_contract.py",
            str(payload_path),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    output = json.loads(result.stdout)
    assert output["status"] == "contract_violation"
    assert "reason_code_off_contract:target_contract_market_slug_mismatch" in output["issues"]
    assert "explain_reason_code_off_contract:target_contract_market_slug_mismatch" in output["issues"]
    assert "probable_blocker:standalone_workspace_runtime_copy_stale" in output["issues"]
    assert output["probable_sync_blocker"]["kind"] == "standalone_workspace_runtime_copy_stale"
    assert output["probable_sync_blocker"]["stale_reason_code"] == "target_contract_market_slug_mismatch"
