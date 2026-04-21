from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _install_real_runtime_spine_workspace(tmp_path: Path) -> tuple[str, str, str]:
    thesis_id = "gooaye"
    suppressed_run_id = "legacy-20260421T000000Z"
    positive_run_id = "positive-20260421T000500Z"
    runtime_root = tmp_path / "lobster-intel" / "data" / "runtime" / thesis_id
    delivery_root = tmp_path / "lobster-intel" / "data" / "delivery" / thesis_id

    _write_json(
        runtime_root / "runs" / f"{suppressed_run_id}.json",
        {
            "artifact_id": f"runtime:{thesis_id}:{suppressed_run_id}",
            "run_id": suppressed_run_id,
            "contract_version": "alert-contract-v1",
            "compare_mode": "suppressed",
            "active_target": {
                "market_id": "1517836",
                "market_question": "Trump announces end of military operations against Iran by June 30th?",
            },
            "P_AI": 0.1443,
            "market_implied_probability": None,
            "ngi_gap": None,
        },
    )
    _write_json(
        runtime_root / "compare" / f"{suppressed_run_id}.json",
        {
            "artifact_id": f"compare:{thesis_id}:{suppressed_run_id}",
            "run_id": suppressed_run_id,
            "compare_mode": "suppressed",
            "runtime_target_id": "1517836",
            "market_target_id": "legacy-430",
            "fallback_reason_codes": ["target_identity_mismatch"],
        },
    )
    _write_json(
        delivery_root / "alerts" / f"{suppressed_run_id}.json",
        {
            "artifact_id": f"alert:{thesis_id}:{suppressed_run_id}",
            "run_id": suppressed_run_id,
            "contract_version": "alert-contract-v1",
            "should_send": False,
            "reason_code": "legacy_target_mismatch",
            "compare_artifact_id": f"compare:{thesis_id}:{suppressed_run_id}",
        },
    )

    _write_json(
        runtime_root / "runs" / f"{positive_run_id}.json",
        {
            "artifact_id": f"runtime:{thesis_id}:{positive_run_id}",
            "run_id": positive_run_id,
            "contract_version": "alert-contract-v1",
            "compare_mode": "full_compare",
            "active_target": {
                "market_id": "1517836",
                "market_question": "Trump announces end of military operations against Iran by June 30th?",
            },
            "P_AI": 0.1443,
            "market_implied_probability": 0.83,
            "ngi_gap": 0.6857,
        },
    )
    _write_json(
        runtime_root / "compare" / f"{positive_run_id}.json",
        {
            "artifact_id": f"compare:{thesis_id}:{positive_run_id}",
            "run_id": positive_run_id,
            "compare_mode": "full_compare",
            "runtime_target_id": "1517836",
            "market_target_id": "1517836",
            "fallback_reason_codes": [],
        },
    )
    _write_json(
        delivery_root / "alerts" / f"{positive_run_id}.json",
        {
            "artifact_id": f"alert:{thesis_id}:{positive_run_id}",
            "run_id": positive_run_id,
            "contract_version": "alert-contract-v1",
            "should_send": True,
            "reason_code": "active_target_contract_ok",
            "compare_artifact_id": f"compare:{thesis_id}:{positive_run_id}",
        },
    )

    return thesis_id, suppressed_run_id, positive_run_id


def test_run_dispatcher_acceptance_cli_writes_artifacts_and_bundle(tmp_path: Path):
    thesis_id, suppressed_run_id, positive_run_id = _install_real_runtime_spine_workspace(tmp_path)
    script_path = ROOT / "lobster-intel" / "scripts" / "run_dispatcher_acceptance.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--workspace",
            str(tmp_path),
            "--thesis-id",
            thesis_id,
            "--bundle-id",
            "bundle-20260421-operator",
            "--suppressed-run-id",
            suppressed_run_id,
            "--positive-run-id",
            positive_run_id,
            "--sink",
            "openclaw_heartbeat",
            "--delivery-status",
            "delivered",
            "--proof-boundary",
            "openclaw_heartbeat",
            "--proof-id",
            f"heartbeat:{positive_run_id}",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["suppressed"]["decision"] == "suppressed"
    assert payload["positive"]["decision"] == "would_send"
    assert payload["bundle"]["bundle"]["e2e_run_id"] == "bundle-20260421-operator"
    assert (tmp_path / payload["suppressed"]["alert_artifact_path"]).exists()
    assert (tmp_path / payload["positive"]["receipt_artifact_path"]).exists()
    assert (tmp_path / payload["bundle"]["bundle_artifact_path"]).exists()
