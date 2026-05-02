import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "lobster-intel" / "scripts" / "build_live_progress_sync_payload.py"


def write_db(db_path: Path, snapshot_at_utc: str):
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE market_snapshots (snapshot_at_utc TEXT)")
        conn.execute("INSERT INTO market_snapshots (snapshot_at_utc) VALUES (?)", (snapshot_at_utc,))
        conn.commit()
    finally:
        conn.close()


def write_latest_ngi(
    path: Path,
    *,
    timestamp_utc: str = "2099-01-01T00:00:00+00:00",
    first_principles_probability: float = 0.1099,
    market_yes_probability: float = 0.455,
    include_delivery_proof: bool = True,
):
    alert_disposition = {
        "decision": "would_send",
        "should_send": True,
        "reason_code": "ngi_changed_major",
        "target_contract_match": True,
        "contract_version": "legacy-monitor-contract-v1",
        "e2e_run_id": "legacy-monitor-20260501T002054.879803Z",
    }
    if include_delivery_proof:
        alert_disposition["delivery_proof"] = {
            "boundary": "openclaw_heartbeat",
            "proof_id": "heartbeat:legacy-monitor-20260501T002054.879803Z",
            "sink_message_id": "heartbeat:legacy-monitor-20260501T002054.879803Z",
        }
    path.write_text(
        json.dumps(
            {
                "timestamp_utc": timestamp_utc,
                "first_principles_probability": first_principles_probability,
                "market_target": {
                    "market_id": "1517836",
                    "market_name": "Trump announces end of military operations against Iran by June 30th",
                },
                "target_detail": {
                    "market_id": "1517836",
                    "market_question": "Trump announces end of military operations against Iran by June 30th?",
                    "market_yes_probability": market_yes_probability,
                    "probability_mode": "yes_is_peace",
                },
                "alert_disposition": alert_disposition,
                "explain": {
                    "reasons": [
                        "ADS-B 顯示區域軍機活動偏高（40 架）",
                        "Firehose 最近 1h 出現升級訊號（6956 件）",
                    ]
                },
            }
        ),
        encoding="utf-8",
    )


def run_cli(state_path: Path, db_path: Path, latest_ngi_path: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(state_path), str(db_path), str(latest_ngi_path)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )


def test_build_live_progress_sync_payload_keeps_target_divergence_and_blockers_together(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["sync_status"] == "blocking"
    assert payload["sync_blocked"] is True
    assert payload["market_target"] == {
        "market_id": "1517836",
        "market_name": "Trump announces end of military operations against Iran by June 30th",
        "market_question": "Trump announces end of military operations against Iran by June 30th?",
        "probability_mode": "yes_is_peace",
    }
    assert payload["divergence"] == {
        "divergence_pp": 34.51,
        "direction": "first_principles_below_market",
        "first_principles_minus_market_pp": -34.51,
        "threshold_pp": 15.0,
        "blocking": True,
    }
    assert payload["freshness"]["dq_status"] == "pass"
    assert payload["blockers"] == ["divergence_pp=34.51"]
    assert payload["basis_lines"]["logistics"] == "ADS-B 顯示區域軍機活動偏高（40 架）"
    assert payload["basis_lines"]["energy"] == "P_AI 10.99% vs market yes 45.50%"
    assert payload["basis_lines"]["key_statement"] == "ops-health blockers: divergence_pp=34.51"


def test_build_live_progress_sync_payload_requires_delivery_proof_for_positive_delivery(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, include_delivery_proof=False)

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "missing latest_ngi.alert_disposition.delivery_proof"


def test_build_live_progress_sync_payload_exports_machine_readable_delivery_proof(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0, result.stderr
    sync_payload = json.loads(result.stdout)
    assert sync_payload["alert_disposition"]["delivery_proof"] == {
        "boundary": "openclaw_heartbeat",
        "proof_id": "heartbeat:legacy-monitor-20260501T002054.879803Z",
        "sink_message_id": "heartbeat:legacy-monitor-20260501T002054.879803Z",
    }


def test_build_live_progress_sync_payload_fails_closed_when_alert_disposition_missing(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)
    payload = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    payload.pop("alert_disposition")
    latest_ngi_path.write_text(json.dumps(payload), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "missing latest_ngi.alert_disposition"
