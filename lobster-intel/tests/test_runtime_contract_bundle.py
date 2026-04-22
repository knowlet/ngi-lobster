from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in [
    "lobster-core",
    "lobster-delivery",
    "lobster-ingest",
    "lobster-plugins",
    "lobster-runtime",
]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_delivery import build_runtime_contract_view, load_runtime_contract_bundle


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _install_runtime_contract_fixture(tmp_path: Path) -> str:
    thesis_id = "gooaye"
    run_id = "20260419T123000Z"
    runtime_root = tmp_path / "lobster-intel" / "data" / "runtime" / thesis_id
    delivery_root = tmp_path / "lobster-intel" / "data" / "delivery" / thesis_id

    _write_json(
        runtime_root / "runs" / f"{run_id}.json",
        {
            "artifact_id": f"runtime:{thesis_id}:{run_id}",
            "run_id": run_id,
            "compare_mode": "full_compare",
            "active_target": {
                "market_id": "1517836",
                "market_question": "Trump announces end of military operations against Iran by June 30th?",
            },
            "P_AI": 0.25,
            "market_implied_probability": 0.72,
            "ngi_gap": -0.47,
        },
    )
    _write_json(
        runtime_root / "compare" / f"{run_id}.json",
        {
            "artifact_id": f"compare:{thesis_id}:{run_id}",
            "run_id": run_id,
            "compare_mode": "full_compare",
            "runtime_target_id": "1517836",
            "market_target_id": "1517836",
            "fallback_reason_codes": [],
        },
    )
    _write_json(
        delivery_root / "alerts" / f"{run_id}.json",
        {
            "artifact_id": f"alert:{thesis_id}:{run_id}",
            "run_id": run_id,
            "should_send": True,
            "reason_code": "active_target_contract_ok",
            "compare_artifact_id": f"compare:{thesis_id}:{run_id}",
        },
    )
    _write_json(
        delivery_root / "receipts" / f"{run_id}.json",
        {
            "artifact_id": f"receipt:{thesis_id}:{run_id}",
            "run_id": run_id,
            "sink": "openclaw_heartbeat",
            "delivery_status": "delivered",
            "alert_artifact_id": f"alert:{thesis_id}:{run_id}",
            "delivery_proof": {
                "boundary": "openclaw_heartbeat",
                "proof_id": f"heartbeat:{run_id}",
                "sink_message_id": f"heartbeat:{run_id}",
            },
        },
    )
    return run_id


def test_build_runtime_contract_view_accepts_real_thesis_runtime_artifacts(tmp_path: Path):
    run_id = _install_runtime_contract_fixture(tmp_path)

    contract_view = build_runtime_contract_view(
        runtime_snapshot=json.loads(
            (tmp_path / "lobster-intel" / "data" / "runtime" / "gooaye" / "runs" / f"{run_id}.json").read_text(
                encoding="utf-8"
            )
        ),
        compare_artifact=json.loads(
            (tmp_path / "lobster-intel" / "data" / "runtime" / "gooaye" / "compare" / f"{run_id}.json").read_text(
                encoding="utf-8"
            )
        ),
        alert_artifact=json.loads(
            (tmp_path / "lobster-intel" / "data" / "delivery" / "gooaye" / "alerts" / f"{run_id}.json").read_text(
                encoding="utf-8"
            )
        ),
        delivery_receipt=json.loads(
            (tmp_path / "lobster-intel" / "data" / "delivery" / "gooaye" / "receipts" / f"{run_id}.json").read_text(
                encoding="utf-8"
            )
        ),
    )

    assert contract_view["status"] == "ok"
    assert contract_view["view"]["runtime"]["compare_mode"] == "full_compare"
    assert contract_view["view"]["receipt"]["delivery_proof"]["boundary"] == "openclaw_heartbeat"


def test_build_runtime_contract_view_fails_closed_without_delivery_proof():
    result = build_runtime_contract_view(
        runtime_snapshot={
            "artifact_id": "runtime:1",
            "compare_mode": "full_compare",
            "active_target": {"market_id": "1517836"},
            "P_AI": 0.25,
            "market_implied_probability": 0.72,
            "ngi_gap": -0.47,
        },
        compare_artifact={
            "artifact_id": "compare:1",
            "compare_mode": "full_compare",
            "fallback_reason_codes": [],
        },
        alert_artifact={
            "artifact_id": "alert:1",
            "should_send": True,
            "reason_code": "first_run_gap_detected",
        },
        delivery_receipt={
            "artifact_id": "receipt:1",
            "sink": "openclaw_heartbeat",
            "delivery_status": "delivered",
        },
    )

    assert result["status"] == "contract_incomplete"
    assert "receipt.delivery_proof" in result["missing_fields"]


def test_build_runtime_contract_view_fails_closed_without_receipt_alert_artifact_id():
    result = build_runtime_contract_view(
        runtime_snapshot={
            "artifact_id": "runtime:1",
            "compare_mode": "full_compare",
            "active_target": {"market_id": "1517836"},
            "P_AI": 0.25,
            "market_implied_probability": 0.72,
            "ngi_gap": -0.47,
        },
        compare_artifact={
            "artifact_id": "compare:1",
            "compare_mode": "full_compare",
            "fallback_reason_codes": [],
        },
        alert_artifact={
            "artifact_id": "alert:1",
            "should_send": True,
            "reason_code": "active_target_contract_ok",
        },
        delivery_receipt={
            "artifact_id": "receipt:1",
            "sink": "openclaw_heartbeat",
            "delivery_status": "delivered",
            "delivery_proof": {
                "boundary": "openclaw_heartbeat",
                "proof_id": "heartbeat:1",
            },
        },
    )

    assert result["status"] == "contract_incomplete"
    assert "receipt.alert_artifact_id" in result["missing_fields"]


def test_build_runtime_contract_view_fails_closed_on_mismatched_receipt_alert_artifact_id():
    result = build_runtime_contract_view(
        runtime_snapshot={
            "artifact_id": "runtime:1",
            "compare_mode": "full_compare",
            "active_target": {"market_id": "1517836"},
            "P_AI": 0.25,
            "market_implied_probability": 0.72,
            "ngi_gap": -0.47,
        },
        compare_artifact={
            "artifact_id": "compare:1",
            "compare_mode": "full_compare",
            "fallback_reason_codes": [],
        },
        alert_artifact={
            "artifact_id": "alert:1",
            "should_send": True,
            "reason_code": "active_target_contract_ok",
        },
        delivery_receipt={
            "artifact_id": "receipt:1",
            "sink": "openclaw_heartbeat",
            "delivery_status": "delivered",
            "alert_artifact_id": "alert:other",
            "delivery_proof": {
                "boundary": "openclaw_heartbeat",
                "proof_id": "heartbeat:1",
            },
        },
    )

    assert result["status"] == "contract_incomplete"
    assert "receipt.alert_artifact_id_mismatch" in result["missing_fields"]


def test_load_runtime_contract_bundle_reads_workspace_artifacts(tmp_path: Path):
    run_id = _install_runtime_contract_fixture(tmp_path)

    contract_view = load_runtime_contract_bundle(tmp_path, "gooaye", run_id)

    assert contract_view["status"] == "ok"
    assert contract_view["view"]["alert"]["should_send"] is True
    assert contract_view["view"]["receipt"]["delivery_proof"]["proof_id"] == f"heartbeat:{run_id}"


def test_verify_runtime_contract_bundle_cli_accepts_real_runtime_run(tmp_path: Path):
    run_id = _install_runtime_contract_fixture(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "lobster-intel/scripts/verify_runtime_contract_bundle.py",
            "--workspace",
            str(tmp_path),
            "--thesis-id",
            "gooaye",
            "--run-id",
            run_id,
        ],
        cwd=ROOT.parent,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["view"]["runtime"]["artifact_id"] == f"runtime:gooaye:{run_id}"
