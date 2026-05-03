import json
import os
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


def write_latest_ngi(
    path: Path,
    *,
    timestamp_utc: str = "2099-01-01T00:00:00+00:00",
    first_principles_probability: float = 0.17,
    market_yes_probability: float = 0.645,
    probability_mode: str = "yes_is_peace",
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
                    "probability_mode": probability_mode,
                    "market_closed": market_closed,
                    "market_active": market_active,
                    "market_accepting_orders": market_accepting_orders,
                    "next_contract_action": next_contract_action,
                    "rollover_candidate": rollover_candidate,
                    "rollover_candidate_blocker": rollover_candidate_blocker,
                },
            }
        ),
        encoding="utf-8",
    )


def run_cli(state_path: Path, db_path: Path, latest_ngi_path: Path, *, env: dict[str, str] | None = None):
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(state_path), str(db_path), str(latest_ngi_path)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        env=effective_env,
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
    assert payload["stale_data"] is False
    assert payload["latest_ngi_stale"] is False
    assert payload["market_untradable"] is False
    assert payload["reselection_required"] is False
    assert payload["next_contract_action"] is None
    assert payload["rollover_candidate"] is None
    assert payload["rollover_candidate_blocker"] is None
    assert payload["divergence_pp"] == 47.5
    assert payload["divergence_threshold_pp"] == 15.0
    assert payload["divergence_blocking"] is True
    assert payload["first_principles_minus_market_pp"] == -47.5
    assert payload["direction"] == "first_principles_below_market"
    assert payload["probability_mode"] == "yes_is_peace"
    assert payload["market_target_id"] == "1517836"
    assert payload["blockers"] == ["dq_status=fail", "divergence_pp=47.50"]


def test_verify_runtime_ops_health_fails_on_stale_data(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2026-04-20T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        timestamp_utc="2099-01-01T00:00:00+00:00",
        first_principles_probability=0.60,
        market_yes_probability=0.62,
    )

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["dq_status"] == "pass"
    assert payload["stale_data"] is True
    assert payload["latest_ngi_stale"] is False
    assert payload["divergence_blocking"] is False
    assert len(payload["blockers"]) == 1
    assert payload["blockers"][0].startswith("stale_data=")
    assert payload["freshness_hours"] > 4


def test_verify_runtime_ops_health_fails_on_latest_ngi_staleness(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        timestamp_utc="2026-04-20T00:00:00+00:00",
        first_principles_probability=0.60,
        market_yes_probability=0.62,
    )

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["dq_status"] == "pass"
    assert payload["stale_data"] is False
    assert payload["latest_ngi_stale"] is True
    assert payload["divergence_blocking"] is False
    assert payload["latest_ngi_age_hours"] > 4
    assert payload["blockers"] == [f"latest_ngi_stale={payload['latest_ngi_age_hours']:.2f}h"]


def test_verify_runtime_ops_health_fails_when_latest_ngi_is_stale_and_divergence_is_blocking(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        timestamp_utc="2026-04-20T00:00:00+00:00",
        first_principles_probability=0.12,
        market_yes_probability=0.54,
    )

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["dq_status"] == "pass"
    assert payload["stale_data"] is False
    assert payload["latest_ngi_stale"] is True
    assert payload["latest_ngi_age_hours"] > 4
    assert payload["divergence_pp"] == 42.0
    assert payload["divergence_blocking"] is True
    assert payload["first_principles_minus_market_pp"] == -42.0
    assert payload["direction"] == "first_principles_below_market"
    assert payload["blockers"] == [
        f"latest_ngi_stale={payload['latest_ngi_age_hours']:.2f}h",
        "divergence_pp=42.00",
    ]


def test_verify_runtime_ops_health_fails_on_divergence_threshold(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["dq_status"] == "pass"
    assert payload["stale_data"] is False
    assert payload["latest_ngi_stale"] is False
    assert payload["divergence_blocking"] is True
    assert payload["blockers"] == ["divergence_pp=47.50"]


def test_verify_runtime_ops_health_uses_state_config_fallback_for_live_reselection_cut(tmp_path: Path):
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
    state_config_path = tmp_path / "state_config.json"
    state_config_path.write_text(
        json.dumps(
            {
                "current_state": "ACTIVE_TRUCE",
                "states": {
                    "ACTIVE_TRUCE": {
                        "fallback_target": {
                            "market_id": "1517835",
                            "market_slug": "fallback-market",
                            "market_name": "Fallback target",
                            "probability_mode": "yes_is_peace",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    result = run_cli(
        state_path,
        db_path,
        latest_ngi_path,
        env={"LOBSTER_STATE_CONFIG_PATH": str(state_config_path)},
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["divergence_blocking"] is False
    assert payload["market_closed"] is True
    assert payload["market_active"] is True
    assert payload["market_accepting_orders"] is False
    assert payload["market_untradable"] is True
    assert payload["reselection_required"] is True
    assert payload["next_contract_action"] == "reselect_active_target"
    assert payload["rollover_candidate"] == {
        "market_id": "1517835",
        "market_slug": "fallback-market",
        "market_name": "Fallback target",
        "probability_mode": "yes_is_peace",
        "source": "state_config_fallback",
        "state": "ACTIVE_TRUCE",
    }
    assert payload["rollover_candidate_blocker"] == "configured_successor_pending_validation"
    assert payload["blockers"] == [
        "market_untradable=closed:true,active:true,accepting_orders:false"
    ]


def test_verify_runtime_ops_health_fails_on_untradable_market(tmp_path: Path):
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

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["divergence_blocking"] is False
    assert payload["market_closed"] is True
    assert payload["market_active"] is True
    assert payload["market_accepting_orders"] is False
    assert payload["market_untradable"] is True
    assert payload["reselection_required"] is True
    assert payload["next_contract_action"] == "reselect_active_target"
    assert payload["rollover_candidate"] is None
    assert payload["rollover_candidate_blocker"] == "no_successor_market"
    assert payload["blockers"] == [
        "market_untradable=closed:true,active:true,accepting_orders:false"
    ]


def test_verify_runtime_ops_health_passes_when_dq_freshness_and_divergence_are_in_contract(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, first_principles_probability=0.52, market_yes_probability=0.645)

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["stale_data"] is False
    assert payload["latest_ngi_stale"] is False
    assert payload["market_untradable"] is False
    assert payload["reselection_required"] is False
    assert payload["next_contract_action"] is None
    assert payload["rollover_candidate"] is None
    assert payload["rollover_candidate_blocker"] is None
    assert payload["divergence_blocking"] is False
    assert payload["blockers"] == []
    assert payload["divergence_pp"] == 12.5
    assert payload["first_principles_minus_market_pp"] == -12.5
    assert payload["direction"] == "first_principles_below_market"


def test_verify_runtime_ops_health_reports_first_principles_above_market_direction(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, first_principles_probability=0.72, market_yes_probability=0.61)

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["first_principles_minus_market_pp"] == 11.0
    assert payload["direction"] == "first_principles_above_market"


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
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    latest_ngi_path.write_text(
        json.dumps(
            {
                "first_principles_probability": 0.52,
                "target_detail": {"market_yes_probability": 0.645},
            }
        ),
        encoding="utf-8",
    )

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == (
        "missing latest_ngi timestamp (expected one of: timestamp_utc, generated_at_utc, created_at_utc, updated_at_utc, snapshot_at_utc)"
    )
