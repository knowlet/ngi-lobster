import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "lobster-intel" / "scripts" / "verify_runtime_ops_health.py"


def write_db(db_path: Path, snapshot_at_utc: str):
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE market_snapshots (snapshot_at_utc TEXT)")
        conn.execute("INSERT INTO market_snapshots (snapshot_at_utc) VALUES (?)", (snapshot_at_utc,))
        conn.commit()
    finally:
        conn.close()


def write_latest_ngi(path: Path, *, timestamp_utc: str = "2099-01-01T00:00:00+00:00"):
    path.write_text(
        json.dumps(
            {
                "timestamp_utc": timestamp_utc,
                "first_principles_probability": 0.17,
                "market_target": {
                    "market_id": "1517836",
                    "market_name": "Trump announces end of military operations against Iran by June 30th",
                },
                "target_detail": {
                    "market_id": "1517836",
                    "market_question": "Trump announces end of military operations against Iran by June 30th?",
                    "market_yes_probability": 0.645,
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


def test_verify_runtime_ops_health_fails_on_dq_and_reports_divergence(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "fail"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["dq_status"] == "fail"
    assert payload["divergence_pp"] == 47.5
    assert payload["market_target_id"] == "1517836"
    assert payload["latest_ngi_timestamp_utc"] == "2099-01-01T00:00:00+00:00"
    assert payload["blockers"] == ["dq_status=fail"]


def test_verify_runtime_ops_health_fails_on_stale_data(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2026-04-20T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["dq_status"] == "pass"
    assert len(payload["blockers"]) == 1
    assert payload["blockers"][0].startswith("stale_data=")
    assert payload["freshness_hours"] > 4


def test_verify_runtime_ops_health_fails_on_stale_latest_ngi(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, timestamp_utc="2026-04-20T00:00:00+00:00")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["dq_status"] == "pass"
    assert len(payload["blockers"]) == 1
    assert payload["blockers"][0].startswith("stale_latest_ngi=")
    assert payload["latest_ngi_age_hours"] > 4


def test_verify_runtime_ops_health_reports_missing_probability_fields(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    latest_ngi_path.write_text(json.dumps({"timestamp_utc": "2099-01-01T00:00:00+00:00", "target_detail": {}}), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "missing latest_ngi.first_principles_probability"


def test_verify_runtime_ops_health_reports_missing_latest_ngi_timestamp(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    latest_ngi_path.write_text(
        json.dumps(
            {
                "first_principles_probability": 0.17,
                "target_detail": {"market_yes_probability": 0.645},
            }
        ),
        encoding="utf-8",
    )

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "missing latest_ngi timestamp field"
