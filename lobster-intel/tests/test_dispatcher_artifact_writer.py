import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in ["lobster-delivery"]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_delivery import (
    load_dispatcher_e2e_bundle,
    load_runtime_contract_bundle,
    write_dispatcher_artifacts,
    write_dispatcher_e2e_bundle,
)


def _suppressed_runtime_payload(bundle_id: str = "bundle-20260421-01") -> dict:
    return {
        "run_id": "legacy-20260421T000000Z",
        "market_target": {
            "market_id": "1517836",
            "market_name": "Will regional escalation happen before May?",
        },
        "target_detail": {
            "market_yes_probability": 0.83,
            "market_question": "Will regional escalation happen before May?",
        },
        "first_principles_probability": 0.1443,
        "alert_disposition": {
            "should_send": False,
            "decision": "suppressed",
            "reason_code": "legacy_target_mismatch",
            "runtime_target_id": "1517836",
            "runtime_target_name": "Will regional escalation happen before May?",
            "alert_target_id": "legacy-430",
            "contract_version": "alert-contract-v1",
            "e2e_run_id": bundle_id,
        },
    }


def _delivered_runtime_payload(bundle_id: str = "bundle-20260421-01") -> dict:
    payload = _suppressed_runtime_payload(bundle_id)
    payload["run_id"] = "positive-20260421T000500Z"
    payload["alert_disposition"] = {
        "should_send": True,
        "decision": "would_send",
        "reason_code": "active_target_contract_ok",
        "runtime_target_id": "1517836",
        "runtime_target_name": "Will regional escalation happen before May?",
        "alert_target_id": "1517836",
        "contract_version": "alert-contract-v1",
        "e2e_run_id": bundle_id,
    }
    return payload


def _install_real_runtime_spine_workspace(workspace: Path) -> tuple[str, str, str]:
    thesis_id = "gooaye"
    suppressed_run_id = "legacy-20260421T000000Z"
    positive_run_id = "positive-20260421T000500Z"
    runtime_root = workspace / "lobster-intel" / "data" / "runtime" / thesis_id
    delivery_root = workspace / "lobster-intel" / "data" / "delivery" / thesis_id

    (runtime_root / "runs").mkdir(parents=True, exist_ok=True)
    (runtime_root / "compare").mkdir(parents=True, exist_ok=True)
    (delivery_root / "alerts").mkdir(parents=True, exist_ok=True)

    suppressed_runtime = {
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
    }
    delivered_runtime = {
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
    }
    (runtime_root / "runs" / f"{suppressed_run_id}.json").write_text(
        json.dumps(suppressed_runtime, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (runtime_root / "runs" / f"{positive_run_id}.json").write_text(
        json.dumps(delivered_runtime, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (runtime_root / "compare" / f"{suppressed_run_id}.json").write_text(
        json.dumps(
            {
                "artifact_id": f"compare:{thesis_id}:{suppressed_run_id}",
                "run_id": suppressed_run_id,
                "compare_mode": "suppressed",
                "runtime_target_id": "1517836",
                "market_target_id": "legacy-430",
                "fallback_reason_codes": ["target_identity_mismatch"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (runtime_root / "compare" / f"{positive_run_id}.json").write_text(
        json.dumps(
            {
                "artifact_id": f"compare:{thesis_id}:{positive_run_id}",
                "run_id": positive_run_id,
                "compare_mode": "full_compare",
                "runtime_target_id": "1517836",
                "market_target_id": "1517836",
                "fallback_reason_codes": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (delivery_root / "alerts" / f"{suppressed_run_id}.json").write_text(
        json.dumps(
            {
                "artifact_id": f"alert:{thesis_id}:{suppressed_run_id}",
                "run_id": suppressed_run_id,
                "contract_version": "alert-contract-v1",
                "should_send": False,
                "reason_code": "legacy_target_mismatch",
                "compare_artifact_id": f"compare:{thesis_id}:{suppressed_run_id}",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (delivery_root / "alerts" / f"{positive_run_id}.json").write_text(
        json.dumps(
            {
                "artifact_id": f"alert:{thesis_id}:{positive_run_id}",
                "run_id": positive_run_id,
                "contract_version": "alert-contract-v1",
                "should_send": True,
                "reason_code": "active_target_contract_ok",
                "compare_artifact_id": f"compare:{thesis_id}:{positive_run_id}",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return thesis_id, suppressed_run_id, positive_run_id


class DispatcherArtifactWriterTests(unittest.TestCase):
    def test_write_dispatcher_artifacts_writes_suppressed_alert_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            result = write_dispatcher_artifacts(
                workspace_dir=workspace,
                thesis_id="gooaye",
                runtime_payload=_suppressed_runtime_payload(),
                now_utc="2026-04-21T00:00:00+00:00",
            )

            alert_path = workspace / result["alert_artifact_path"]
            alert_payload = json.loads(alert_path.read_text(encoding="utf-8"))
            alert_exists = alert_path.exists()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["decision"], "suppressed")
        self.assertEqual(result["receipt_artifact_path"], None)
        self.assertTrue(alert_exists)
        self.assertEqual(alert_payload["alert_disposition"]["reason_code"], "legacy_target_mismatch")

    def test_write_dispatcher_artifacts_writes_receipt_for_positive_control(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            result = write_dispatcher_artifacts(
                workspace_dir=workspace,
                thesis_id="gooaye",
                runtime_payload=_delivered_runtime_payload(),
                delivery_receipt={
                    "sink": "openclaw_heartbeat",
                    "delivery_status": "delivered",
                    "delivery_proof": {
                        "boundary": "openclaw_heartbeat",
                        "sink_message_id": "msg-123",
                    },
                },
                now_utc="2026-04-21T00:00:00+00:00",
            )

            receipt_path = workspace / result["receipt_artifact_path"]
            receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt_exists = receipt_path.exists()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["decision"], "would_send")
        self.assertTrue(receipt_exists)
        self.assertEqual(receipt_payload["delivery_proof"]["proof_id"], "msg-123")
        self.assertEqual(receipt_payload["alert_artifact_id"], "alert:gooaye:positive-20260421T000500Z")

    def test_written_dispatcher_artifacts_are_bundle_and_runtime_contract_compatible(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            suppressed = write_dispatcher_artifacts(
                workspace_dir=workspace,
                thesis_id="gooaye",
                runtime_payload=_suppressed_runtime_payload(),
                now_utc="2026-04-21T00:00:00+00:00",
            )
            delivered = write_dispatcher_artifacts(
                workspace_dir=workspace,
                thesis_id="gooaye",
                runtime_payload=_delivered_runtime_payload(),
                delivery_receipt={
                    "sink": "openclaw_heartbeat",
                    "delivery_status": "delivered",
                    "delivery_proof": {
                        "boundary": "openclaw_heartbeat",
                        "sink_message_id": "msg-123",
                    },
                },
                now_utc="2026-04-21T00:01:00+00:00",
            )

            runtime_root = workspace / "lobster-intel" / "data" / "runtime" / "gooaye"
            runtime_root.mkdir(parents=True, exist_ok=True)
            (runtime_root / "runs").mkdir(parents=True, exist_ok=True)
            (runtime_root / "compare").mkdir(parents=True, exist_ok=True)

            run_id = "positive-20260421T000500Z"
            runtime_payload = {
                **_delivered_runtime_payload(),
                "artifact_id": f"runtime:gooaye:{run_id}",
                "compare_mode": "active_target_contract",
                "active_target": {
                    "market_id": "1517836",
                    "market_name": "Will regional escalation happen before May?",
                },
                "P_AI": 0.1443,
                "market_implied_probability": 0.83,
                "ngi_gap": 0.6857,
            }
            (runtime_root / "runs" / f"{run_id}.json").write_text(
                json.dumps(runtime_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (runtime_root / "compare" / f"{run_id}.json").write_text(
                json.dumps(
                    {
                        "artifact_id": f"compare:gooaye:{run_id}",
                        "compare_mode": "active_target_contract",
                        "runtime_target_id": "1517836",
                        "market_target_id": "1517836",
                        "fallback_reason_codes": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            bundle_result = write_dispatcher_e2e_bundle(
                workspace_dir=workspace,
                thesis_id="gooaye",
                run_ids=["legacy-20260421T000000Z", "positive-20260421T000500Z"],
                bundle_id="bundle-20260421-01",
            )
            bundle_payload = load_dispatcher_e2e_bundle(workspace, "gooaye", "bundle-20260421-01")
            contract_payload = load_runtime_contract_bundle(workspace, "gooaye", run_id)

        self.assertEqual(suppressed["decision"], "suppressed")
        self.assertEqual(delivered["decision"], "would_send")
        self.assertEqual(bundle_result["status"], "ok")
        self.assertEqual(bundle_payload["e2e_run_id"], "bundle-20260421-01")
        self.assertEqual(contract_payload["status"], "ok")
        self.assertEqual(contract_payload["view"]["receipt"]["delivery_proof"]["proof_id"], "msg-123")

    def test_write_dispatcher_artifact_cli_reads_runtime_file(self):
        repo = Path(__file__).resolve().parents[2]
        script_path = repo / "lobster-intel" / "scripts" / "write_dispatcher_artifact.py"
        self.assertTrue(script_path.exists(), f"missing CLI script: {script_path}")

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            runtime_file = workspace / "runtime.json"
            runtime_file.write_text(
                json.dumps(_delivered_runtime_payload(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            old_argv = sys.argv
            try:
                sys.argv = [
                    str(script_path),
                    "--workspace",
                    str(workspace),
                    "--thesis-id",
                    "gooaye",
                    "--runtime-file",
                    str(runtime_file),
                    "--sink",
                    "openclaw_heartbeat",
                    "--delivery-status",
                    "delivered",
                    "--proof-boundary",
                    "openclaw_heartbeat",
                    "--proof-id",
                    "msg-123",
                ]
                with patch("sys.stdout", stdout):
                    namespace: dict[str, object] = {
                        "__name__": "__main__",
                        "__file__": str(script_path),
                    }
                    exec(script_path.read_text(encoding="utf-8"), namespace)
            finally:
                sys.argv = old_argv

            payload = json.loads(stdout.getvalue())
            alert_exists = (workspace / payload["alert_artifact_path"]).exists()
            receipt_exists = (workspace / payload["receipt_artifact_path"]).exists()

        self.assertEqual(payload["status"], "ok")
        self.assertTrue(alert_exists)
        self.assertTrue(receipt_exists)

    def test_real_runtime_spine_artifacts_flow_into_dispatcher_bundle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            thesis_id, suppressed_run_id, positive_run_id = _install_real_runtime_spine_workspace(workspace)

            suppressed = write_dispatcher_artifacts(
                workspace_dir=workspace,
                thesis_id=thesis_id,
                runtime_payload=json.loads(
                    (workspace / "lobster-intel" / "data" / "runtime" / thesis_id / "runs" / f"{suppressed_run_id}.json").read_text(
                        encoding="utf-8"
                    )
                ),
                now_utc="2026-04-21T00:00:00+00:00",
            )
            delivered = write_dispatcher_artifacts(
                workspace_dir=workspace,
                thesis_id=thesis_id,
                runtime_payload=json.loads(
                    (workspace / "lobster-intel" / "data" / "runtime" / thesis_id / "runs" / f"{positive_run_id}.json").read_text(
                        encoding="utf-8"
                    )
                ),
                delivery_receipt={
                    "sink": "openclaw_heartbeat",
                    "delivery_status": "delivered",
                    "delivery_proof": {
                        "boundary": "openclaw_heartbeat",
                        "sink_message_id": "heartbeat:positive-20260421T000500Z",
                    },
                },
                now_utc="2026-04-21T00:01:00+00:00",
            )
            bundle = write_dispatcher_e2e_bundle(
                workspace_dir=workspace,
                thesis_id=thesis_id,
                run_ids=[suppressed_run_id, positive_run_id],
                bundle_id="bundle-20260421-runtime-path",
                now_utc="2026-04-21T00:02:00+00:00",
            )

        self.assertEqual(suppressed["decision"], "suppressed")
        self.assertEqual(delivered["decision"], "would_send")
        self.assertEqual(bundle["status"], "ok")
        self.assertEqual(bundle["bundle"]["e2e_run_id"], "bundle-20260421-runtime-path")
        self.assertEqual(bundle["bundle"]["fixtures"][0]["reason_code"], "legacy_target_mismatch")
        self.assertEqual(
            bundle["bundle"]["fixtures"][1]["delivery_proof"]["proof_id"],
            "heartbeat:positive-20260421T000500Z",
        )


if __name__ == "__main__":
    unittest.main()
