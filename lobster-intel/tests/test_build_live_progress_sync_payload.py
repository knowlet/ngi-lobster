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
    market_closed: bool = False,
    market_active: bool = True,
    market_accepting_orders: bool = True,
    next_contract_action: str | None = None,
    rollover_candidate: str | None = None,
    rollover_candidate_blocker: str | None = None,
):
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
                    "market_closed": market_closed,
                    "market_active": market_active,
                    "market_accepting_orders": market_accepting_orders,
                    "next_contract_action": next_contract_action,
                    "rollover_candidate": rollover_candidate,
                    "rollover_candidate_blocker": rollover_candidate_blocker,
                },
                "alert_disposition": {
                    "decision": "would_send",
                    "should_send": True,
                    "reason_code": "ngi_changed_major",
                    "target_contract_match": True,
                    "contract_version": "legacy-monitor-contract-v1",
                    "e2e_run_id": "legacy-monitor-20260501T002054.879803Z",
                },
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
    assert payload["contract_action"] == {
        "reselection_required": False,
        "next_contract_action": None,
        "rollover_candidate": None,
        "rollover_candidate_blocker": None,
    }
    assert payload["blockers"] == ["divergence_pp=34.51"]
    assert payload["basis_lines"]["logistics"] == "ADS-B 顯示區域軍機活動偏高（40 架）"
    assert payload["basis_lines"]["energy"] == "P_AI 10.99% vs market yes 45.50%"
    assert payload["basis_lines"]["key_statement"] == "ops-health blockers: divergence_pp=34.51"


def test_build_live_progress_sync_payload_includes_reselection_blockers_for_closed_market(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.56,
        market_closed=True,
        market_active=True,
        market_accepting_orders=False,
    )

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["sync_status"] == "blocking"
    assert payload["sync_blocked"] is True
    assert payload["contract_action"] == {
        "reselection_required": True,
        "next_contract_action": "reselect_active_target",
        "rollover_candidate": None,
        "rollover_candidate_blocker": "no_successor_market",
    }
    assert payload["blockers"] == [
        "market_untradable=closed:true,active:true,accepting_orders:false"
    ]
    assert (
        payload["basis_lines"]["key_statement"]
        == "ops-health blockers: market_untradable=closed:true,active:true,accepting_orders:false"
    )


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
