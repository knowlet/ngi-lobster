import json
import subprocess
from pathlib import Path


def test_verify_alert_contract_bundle_cli_accepts_canonical_example_bundle():
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            str(repo / ".venv" / "bin" / "python"),
            "lobster-intel/scripts/verify_alert_contract_bundle.py",
            "lobster-intel/examples/e2e_alert_contract_bundle.json",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["bundle"]["e2e_run_id"] == "bundle-20260417-01"
    assert [fixture["decision"] for fixture in payload["bundle"]["fixtures"]] == [
        "suppressed",
        "would_send",
    ]


def test_verify_alert_contract_bundle_cli_accepts_dispatcher_bundle_artifact(tmp_path: Path):
    repo = Path(__file__).resolve().parents[2]
    example_payloads = json.loads((repo / "lobster-intel" / "examples" / "e2e_alert_contract_bundle.json").read_text())
    fixtures = []
    for payload in example_payloads:
        disposition = dict(payload["alert_disposition"])
        fixture = {
            "should_send": disposition["should_send"],
            "decision": disposition["decision"],
            "reason_code": disposition["reason_code"],
            "runtime_target_id": disposition["runtime_target_id"],
            "runtime_target_name": disposition["runtime_target_name"],
            "alert_target_id": disposition["alert_target_id"],
            "contract_version": disposition["contract_version"],
            "e2e_run_id": disposition["e2e_run_id"],
        }
        if disposition.get("delivery_proof") is not None:
            fixture["delivery_proof"] = disposition["delivery_proof"]
        fixtures.append(fixture)
    dispatcher_bundle = {
        "schema": "lobster.delivery.dispatcher_e2e_bundle.v1",
        "recorded_at_utc": "2026-04-21T12:00:00Z",
        "thesis_id": "gooaye",
        "run_ids": [
            "legacy-20260421T000000Z",
            "positive-20260421T000500Z",
        ],
        "contract_version": "v1",
        "e2e_run_id": "bundle-20260417-01",
        "fixtures": fixtures,
    }
    bundle_path = tmp_path / "dispatcher_bundle.json"
    bundle_path.write_text(json.dumps(dispatcher_bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    result = subprocess.run(
        [
            str(repo / ".venv" / "bin" / "python"),
            "lobster-intel/scripts/verify_alert_contract_bundle.py",
            str(bundle_path),
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["bundle"]["e2e_run_id"] == "bundle-20260417-01"
