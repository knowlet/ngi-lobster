from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


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

from lobster_delivery import load_dispatcher_e2e_bundle, write_dispatcher_e2e_bundle


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _install_dispatcher_fixture(tmp_path: Path) -> tuple[str, str, str]:
    thesis_id = "gooaye"
    bundle_id = "bundle-20260421-01"
    suppressed_run_id = "legacy-20260421T000000Z"
    positive_run_id = "positive-20260421T000500Z"
    delivery_root = tmp_path / "lobster-intel" / "data" / "delivery" / thesis_id / "alerts"

    _write_json(
        delivery_root / f"{suppressed_run_id}.json",
        {
            "alert_disposition": {
                "should_send": False,
                "decision": "suppressed",
                "reason_code": "legacy_target_mismatch",
                "runtime_target_id": "1517836",
                "runtime_target_name": "Trump announces end of military operations against Iran by June 30th?",
                "alert_target_id": "legacy-430",
                "contract_version": "alert-contract-v1",
                "e2e_run_id": bundle_id,
            }
        },
    )
    _write_json(
        delivery_root / f"{positive_run_id}.json",
        {
            "alert_disposition": {
                "should_send": True,
                "decision": "would_send",
                "reason_code": "active_target_contract_ok",
                "runtime_target_id": "1517836",
                "runtime_target_name": "Trump announces end of military operations against Iran by June 30th?",
                "alert_target_id": "1517836",
                "contract_version": "alert-contract-v1",
                "e2e_run_id": bundle_id,
                "delivery_proof": {
                    "boundary": "dispatcher_sink",
                    "proof_id": "msg-123",
                    "sink_message_id": "msg-123",
                },
            }
        },
    )

    return thesis_id, suppressed_run_id, positive_run_id


def _install_real_dispatcher_runtime_fixture(tmp_path: Path) -> tuple[str, str, str]:
    thesis_id = "gooaye"
    bundle_id = "bundle-20260421-bridge"
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
    _write_json(
        delivery_root / "receipts" / f"{positive_run_id}.json",
        {
            "artifact_id": f"receipt:{thesis_id}:{positive_run_id}",
            "run_id": positive_run_id,
            "sink": "openclaw_heartbeat",
            "delivery_status": "delivered",
            "alert_artifact_id": f"alert:{thesis_id}:{positive_run_id}",
            "delivery_proof": {
                "boundary": "openclaw_heartbeat",
                "sink_message_id": "heartbeat:positive-20260421T000500Z",
            },
        },
    )

    return thesis_id, suppressed_run_id, positive_run_id


def test_write_dispatcher_e2e_bundle_writes_bundle_artifact(tmp_path: Path):
    thesis_id, suppressed_run_id, positive_run_id = _install_dispatcher_fixture(tmp_path)

    result = write_dispatcher_e2e_bundle(
        workspace_dir=tmp_path,
        thesis_id=thesis_id,
        run_ids=[suppressed_run_id, positive_run_id],
        bundle_id="bundle-20260421-01",
        now_utc="2026-04-21T00:10:00+00:00",
    )

    assert result["status"] == "ok"
    assert result["bundle"]["e2e_run_id"] == "bundle-20260421-01"
    assert result["bundle"]["fixtures"][1]["delivery_proof"]["proof_id"] == "msg-123"
    assert (tmp_path / result["bundle_artifact_path"]).exists()


def test_write_dispatcher_e2e_bundle_fails_closed_on_mismatched_bundle_id(tmp_path: Path):
    thesis_id, suppressed_run_id, positive_run_id = _install_dispatcher_fixture(tmp_path)

    with pytest.raises(ValueError, match="shared e2e_run_id"):
        write_dispatcher_e2e_bundle(
            workspace_dir=tmp_path,
            thesis_id=thesis_id,
            run_ids=[suppressed_run_id, positive_run_id],
            bundle_id="bundle-20260421-02",
            now_utc="2026-04-21T00:10:00+00:00",
        )


def test_write_dispatcher_e2e_bundle_fails_closed_on_stale_alert_run_id(tmp_path: Path):
    thesis_id, suppressed_run_id, positive_run_id = _install_dispatcher_fixture(tmp_path)
    stale_alert_path = (
        tmp_path
        / "lobster-intel"
        / "data"
        / "delivery"
        / thesis_id
        / "alerts"
        / f"{positive_run_id}.json"
    )
    stale_alert = json.loads(stale_alert_path.read_text(encoding="utf-8"))
    stale_alert["run_id"] = "positive-20260420T235959Z"
    _write_json(stale_alert_path, stale_alert)

    with pytest.raises(ValueError, match="alert artifact run_id mismatch"):
        write_dispatcher_e2e_bundle(
            workspace_dir=tmp_path,
            thesis_id=thesis_id,
            run_ids=[suppressed_run_id, positive_run_id],
            bundle_id="bundle-20260421-01",
            now_utc="2026-04-21T00:10:00+00:00",
        )


def test_write_dispatcher_e2e_bundle_fails_closed_on_stale_receipt_run_id(tmp_path: Path):
    thesis_id, suppressed_run_id, positive_run_id = _install_real_dispatcher_runtime_fixture(tmp_path)
    stale_receipt_path = (
        tmp_path
        / "lobster-intel"
        / "data"
        / "delivery"
        / thesis_id
        / "receipts"
        / f"{positive_run_id}.json"
    )
    stale_receipt = json.loads(stale_receipt_path.read_text(encoding="utf-8"))
    stale_receipt["run_id"] = "positive-20260420T235959Z"
    _write_json(stale_receipt_path, stale_receipt)

    with pytest.raises(ValueError, match="delivery receipt run_id mismatch"):
        write_dispatcher_e2e_bundle(
            workspace_dir=tmp_path,
            thesis_id=thesis_id,
            run_ids=[suppressed_run_id, positive_run_id],
            bundle_id="bundle-20260421-bridge",
            now_utc="2026-04-21T00:10:00+00:00",
        )


def test_write_dispatcher_e2e_bundle_fails_closed_on_stale_runtime_run_id(tmp_path: Path):
    thesis_id, suppressed_run_id, positive_run_id = _install_real_dispatcher_runtime_fixture(tmp_path)
    stale_runtime_path = (
        tmp_path
        / "lobster-intel"
        / "data"
        / "runtime"
        / thesis_id
        / "runs"
        / f"{positive_run_id}.json"
    )
    stale_runtime = json.loads(stale_runtime_path.read_text(encoding="utf-8"))
    stale_runtime["run_id"] = "positive-20260420T235959Z"
    _write_json(stale_runtime_path, stale_runtime)

    with pytest.raises(ValueError, match="runtime artifact run_id mismatch"):
        write_dispatcher_e2e_bundle(
            workspace_dir=tmp_path,
            thesis_id=thesis_id,
            run_ids=[suppressed_run_id, positive_run_id],
            bundle_id="bundle-20260421-bridge",
            now_utc="2026-04-21T00:10:00+00:00",
        )


def test_write_dispatcher_e2e_bundle_fails_closed_on_stale_compare_run_id(tmp_path: Path):
    thesis_id, suppressed_run_id, positive_run_id = _install_real_dispatcher_runtime_fixture(tmp_path)
    stale_compare_path = (
        tmp_path
        / "lobster-intel"
        / "data"
        / "runtime"
        / thesis_id
        / "compare"
        / f"{positive_run_id}.json"
    )
    stale_compare = json.loads(stale_compare_path.read_text(encoding="utf-8"))
    stale_compare["run_id"] = "positive-20260420T235959Z"
    _write_json(stale_compare_path, stale_compare)

    with pytest.raises(ValueError, match="runtime compare run_id mismatch"):
        write_dispatcher_e2e_bundle(
            workspace_dir=tmp_path,
            thesis_id=thesis_id,
            run_ids=[suppressed_run_id, positive_run_id],
            bundle_id="bundle-20260421-bridge",
            now_utc="2026-04-21T00:10:00+00:00",
        )


def test_load_dispatcher_e2e_bundle_reads_workspace_artifact(tmp_path: Path):
    thesis_id, suppressed_run_id, positive_run_id = _install_dispatcher_fixture(tmp_path)
    write_dispatcher_e2e_bundle(
        workspace_dir=tmp_path,
        thesis_id=thesis_id,
        run_ids=[suppressed_run_id, positive_run_id],
        bundle_id="bundle-20260421-01",
        now_utc="2026-04-21T00:10:00+00:00",
    )

    payload = load_dispatcher_e2e_bundle(tmp_path, thesis_id, "bundle-20260421-01")

    assert payload["schema"] == "lobster.delivery.dispatcher_e2e_bundle.v1"
    assert payload["e2e_run_id"] == "bundle-20260421-01"
    assert [fixture["decision"] for fixture in payload["fixtures"]] == ["suppressed", "would_send"]


def test_build_dispatcher_e2e_bundle_cli_writes_bundle_artifact(tmp_path: Path):
    thesis_id, suppressed_run_id, positive_run_id = _install_dispatcher_fixture(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "lobster-intel/scripts/build_dispatcher_e2e_bundle.py",
            "--workspace",
            str(tmp_path),
            "--thesis-id",
            thesis_id,
            "--bundle-id",
            "bundle-20260421-01",
            "--run-id",
            suppressed_run_id,
            "--run-id",
            positive_run_id,
        ],
        cwd=ROOT.parent,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["bundle"]["e2e_run_id"] == "bundle-20260421-01"


def test_write_dispatcher_e2e_bundle_accepts_real_runtime_artifacts(tmp_path: Path):
    thesis_id, suppressed_run_id, positive_run_id = _install_real_dispatcher_runtime_fixture(tmp_path)

    result = write_dispatcher_e2e_bundle(
        workspace_dir=tmp_path,
        thesis_id=thesis_id,
        run_ids=[suppressed_run_id, positive_run_id],
        bundle_id="bundle-20260421-bridge",
        now_utc="2026-04-21T00:10:00+00:00",
    )

    assert result["status"] == "ok"
    assert result["bundle"]["e2e_run_id"] == "bundle-20260421-bridge"
    assert result["bundle"]["fixtures"][0]["alert_target_id"] == "legacy-430"
    assert result["bundle"]["fixtures"][1]["delivery_proof"]["proof_id"] == "heartbeat:positive-20260421T000500Z"

    artifact_payload = load_dispatcher_e2e_bundle(tmp_path, thesis_id, "bundle-20260421-bridge")
    assert artifact_payload["run_ids"] == [suppressed_run_id, positive_run_id]
    assert artifact_payload["contract_version"] == "alert-contract-v1"
