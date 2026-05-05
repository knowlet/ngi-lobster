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
    market_closed: bool | None = None,
    market_accepting_orders: bool | None = None,
):
    target_detail = {
        "market_id": "1517836",
        "market_question": "Trump announces end of military operations against Iran by June 30th?",
        "market_yes_probability": market_yes_probability,
        "probability_mode": probability_mode,
    }
    if market_closed is not None:
        target_detail["market_closed"] = market_closed
    if market_accepting_orders is not None:
        target_detail["market_accepting_orders"] = market_accepting_orders

    path.write_text(
        json.dumps(
            {
                "timestamp_utc": timestamp_utc,
                "first_principles_probability": first_principles_probability,
                "market_target": {
                    "market_id": "1517836",
                    "market_name": "Trump announces end of military operations against Iran by June 30th",
                },
                "target_detail": target_detail,
            }
        ),
        encoding="utf-8",
    )


def write_runtime_source(path: Path, *, items: list[dict[str, object]]):
    path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "plugin": "polymarket-tracker",
                "version": "0.1.0",
                "ran_at_utc": "2099-01-01T00:00:00+00:00",
                "evidence": {"items": items},
            }
        ),
        encoding="utf-8",
    )


def run_cli(
    state_path: Path,
    db_path: Path,
    latest_ngi_path: Path,
    runtime_source_path: Path | None = None,
    *,
    env: dict[str, str] | None = None,
):
    argv = [sys.executable, str(SCRIPT), str(state_path), str(db_path), str(latest_ngi_path)]
    if runtime_source_path is not None:
        argv.append(str(runtime_source_path))
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
    return subprocess.run(
        argv,
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
    assert payload["divergence_pp"] == 47.5
    assert payload["divergence_threshold_pp"] == 15.0
    assert payload["divergence_blocking"] is True
    assert payload["first_principles_minus_market_pp"] == -47.5
    assert payload["direction"] == "first_principles_below_market"
    assert payload["probability_mode"] == "yes_is_peace"
    assert payload["market_target_id"] == "1517836"
    assert payload["rollover_candidate"] is None
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


def test_verify_runtime_ops_health_exports_reselection_acceptance_when_stale_target_is_closed(
    tmp_path: Path,
):
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
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    write_runtime_source(
        runtime_source_path,
        items=[
            {
                "external_id": "1517836",
                "title": "Closed target",
                "url": "closed-target",
                "collected_at_utc": "2099-01-01T00:00:00+00:00",
                "metadata": {
                    "market_id": "1517836",
                    "slug": "closed-target",
                    "yes_probability": 1.0,
                    "active": True,
                    "closed": True,
                    "accepting_orders": False,
                    "source_config": {"label": "Closed target"},
                },
            },
            {
                "external_id": "rollover-1518000",
                "title": "Open successor market",
                "url": "open-successor",
                "collected_at_utc": "2099-01-01T00:05:00+00:00",
                "metadata": {
                    "market_id": "rollover-1518000",
                    "slug": "open-successor",
                    "yes_probability": 0.42,
                    "active": True,
                    "closed": False,
                    "accepting_orders": True,
                    "source_config": {"label": "Open successor market"},
                },
            },
        ],
    )

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["latest_ngi_stale"] is True
    assert payload["closed_target_blocking"] is True
    assert payload["divergence_blocking"] is True
    assert payload["active_target_reselection"] == {
        "runtime_target_id": "1517836",
        "market_question": "Trump announces end of military operations against Iran by June 30th?",
        "reselection_required": True,
        "next_contract_action": "reselect_active_target",
        "rollover_candidate_blocker": None,
        "rollover_candidate": {
            "market_id": "rollover-1518000",
            "market_slug": "open-successor",
            "market_name": "Open successor market",
            "market_question": "Open successor market",
            "market_yes_probability": 0.42,
            "market_closed": False,
            "market_active": True,
            "market_accepting_orders": True,
            "collected_at_utc": "2099-01-01T00:05:00+00:00",
            "published_at_utc": None,
        },
        "rollover_candidate_diagnostics": {
            "current_market_id": "1517836",
            "successor_count": 1,
            "open_successor_count": 1,
            "accepting_orders_count": 1,
            "explicit_open_accepting_count": 1,
            "sample_successors": [
                {
                    "market_id": "rollover-1518000",
                    "market_slug": "open-successor",
                    "market_question": "Open successor market",
                    "market_yes_probability": 0.42,
                    "market_closed": False,
                    "market_accepting_orders": True,
                }
            ],
        },
    }


def test_verify_runtime_ops_health_requires_reselection_market_question(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["target_detail"].pop("market_question")
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == (
        "active_target_reselection.market_question must be a non-empty string"
    )


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


def test_verify_runtime_ops_health_fails_closed_when_market_is_closed(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    write_runtime_source(
        runtime_source_path,
        items=[
            {
                "external_id": "1517836",
                "title": "Closed market",
                "url": "closed-market",
                "collected_at_utc": "2099-01-01T00:00:00+00:00",
                "metadata": {
                    "market_id": "1517836",
                    "slug": "closed-market",
                    "yes_probability": 1.0,
                    "active": True,
                    "closed": True,
                    "accepting_orders": False,
                    "source_config": {"label": "Closed market"},
                },
            },
            {
                "external_id": "rollover-1518000",
                "title": "Open successor market",
                "url": "open-successor",
                "collected_at_utc": "2099-01-01T00:05:00+00:00",
                "metadata": {
                    "market_id": "rollover-1518000",
                    "slug": "open-successor",
                    "yes_probability": 0.42,
                    "active": True,
                    "closed": False,
                    "accepting_orders": True,
                    "source_config": {"label": "Open successor market"},
                },
            },
        ],
    )

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["closed_target_blocking"] is True
    assert payload["reselection_required"] is True
    assert payload["next_contract_action"] == "reselect_active_target"
    assert payload["market_closed"] is True
    assert payload["market_accepting_orders"] is False
    assert payload["divergence_blocking"] is False
    assert payload["rollover_candidate"] == {
        "market_id": "rollover-1518000",
        "market_slug": "open-successor",
        "market_name": "Open successor market",
        "market_question": "Open successor market",
        "market_yes_probability": 0.42,
        "market_closed": False,
        "market_active": True,
        "market_accepting_orders": True,
        "collected_at_utc": "2099-01-01T00:05:00+00:00",
        "published_at_utc": None,
    }
    assert payload["blockers"] == ["market_closed=true", "market_accepting_orders=false"]


def test_verify_runtime_ops_health_uses_state_config_fallback_for_live_reselection_cut(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
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
    assert payload["closed_target_blocking"] is True
    assert payload["reselection_required"] is True
    assert payload["next_contract_action"] == "reselect_active_target"
    assert payload["rollover_candidate"] == {
        "market_id": "1517835",
        "market_slug": "fallback-market",
        "market_name": "Fallback target",
        "market_question": "Fallback target",
        "probability_mode": "yes_is_peace",
        "source": "state_config_fallback",
        "state": "ACTIVE_TRUCE",
    }
    assert payload["rollover_candidate_blocker"] == "configured_successor_pending_validation"
    assert payload["active_target_reselection"]["rollover_candidate"] == payload["rollover_candidate"]


def test_verify_runtime_ops_health_uses_state_config_fallback_when_runtime_source_has_no_successor(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    write_runtime_source(
        runtime_source_path,
        items=[
            {
                "external_id": "1517836",
                "title": "Closed target",
                "url": "closed-target",
                "collected_at_utc": "2099-01-01T00:00:00+00:00",
                "metadata": {
                    "market_id": "1517836",
                    "slug": "closed-target",
                    "yes_probability": 1.0,
                    "active": True,
                    "closed": True,
                    "accepting_orders": False,
                    "source_config": {"label": "Closed target"},
                },
            }
        ],
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
        runtime_source_path,
        env={"LOBSTER_STATE_CONFIG_PATH": str(state_config_path)},
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["rollover_candidate"] == {
        "market_id": "1517835",
        "market_slug": "fallback-market",
        "market_name": "Fallback target",
        "market_question": "Fallback target",
        "probability_mode": "yes_is_peace",
        "source": "state_config_fallback",
        "state": "ACTIVE_TRUCE",
    }
    assert payload["rollover_candidate_blocker"] == "configured_successor_pending_validation"
    assert payload["active_target_reselection"]["rollover_candidate"] == payload["rollover_candidate"]


def test_verify_runtime_ops_health_strips_state_config_fallback_probability_mode(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
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
                            "probability_mode": " yes_is_peace ",
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
    assert payload["rollover_candidate"]["probability_mode"] == "yes_is_peace"
    assert (
        payload["active_target_reselection"]["rollover_candidate"]["probability_mode"]
        == "yes_is_peace"
    )


def test_verify_runtime_ops_health_strips_state_config_fallback_identity_fields(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
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
                            "market_id": " 1517835 ",
                            "market_slug": " fallback-market ",
                            "market_name": " Fallback target ",
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
    assert payload["rollover_candidate"]["market_id"] == "1517835"
    assert payload["rollover_candidate"]["market_slug"] == "fallback-market"
    assert payload["rollover_candidate"]["market_name"] == "Fallback target"
    assert payload["active_target_reselection"]["rollover_candidate"] == payload["rollover_candidate"]


def test_verify_runtime_ops_health_strips_state_config_fallback_market_question(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
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
                            "market_question": " Fallback target question? ",
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
    assert payload["rollover_candidate"]["market_question"] == "Fallback target question?"
    assert payload["active_target_reselection"]["rollover_candidate"] == payload["rollover_candidate"]


def test_verify_runtime_ops_health_strips_state_config_current_state(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    state_config_path = tmp_path / "state_config.json"
    state_config_path.write_text(
        json.dumps(
            {
                "current_state": " ACTIVE_TRUCE ",
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
    assert payload["rollover_candidate"]["state"] == "ACTIVE_TRUCE"
    assert payload["active_target_reselection"]["rollover_candidate"] == payload["rollover_candidate"]


def test_verify_runtime_ops_health_strips_state_config_fallback_source_metadata(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
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
                            "type": " polymarket ",
                            "topic_slug": " us_iran_escalation ",
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
    assert payload["rollover_candidate"]["target_type"] == "polymarket"
    assert payload["rollover_candidate"]["topic_slug"] == "us_iran_escalation"
    assert payload["active_target_reselection"]["rollover_candidate"] == payload["rollover_candidate"]


def test_verify_runtime_ops_health_rejects_malformed_state_config_fallback_identity(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
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
                            "market_id": ["1517835"],
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
    assert result.stdout == ""
    assert result.stderr.strip() == "state_config.fallback_target.market_id must be a non-empty string"


def test_verify_runtime_ops_health_rejects_malformed_state_config_states(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    state_config_path = tmp_path / "state_config.json"
    state_config_path.write_text(
        json.dumps({"current_state": "ACTIVE_TRUCE", "states": ["ACTIVE_TRUCE"]}),
        encoding="utf-8",
    )

    result = run_cli(
        state_path,
        db_path,
        latest_ngi_path,
        env={"LOBSTER_STATE_CONFIG_PATH": str(state_config_path)},
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "state_config.states must be a JSON object"


def test_verify_runtime_ops_health_rejects_empty_state_config_current_state(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    state_config_path = tmp_path / "state_config.json"
    state_config_path.write_text(
        json.dumps(
            {
                "current_state": "",
                "states": {
                    "ACTIVE_TRUCE": {
                        "fallback_target": {
                            "market_id": "1517835",
                            "market_slug": "fallback-market",
                            "market_name": "Fallback target",
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
    assert result.stdout == ""
    assert result.stderr.strip() == "state_config.current_state must be a non-empty string"


def test_verify_runtime_ops_health_rejects_missing_state_config_current_state(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    state_config_path = tmp_path / "state_config.json"
    state_config_path.write_text(
        json.dumps(
            {
                "states": {
                    "ACTIVE_TRUCE": {
                        "fallback_target": {
                            "market_id": "1517835",
                            "market_slug": "fallback-market",
                            "market_name": "Fallback target",
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
    assert result.stdout == ""
    assert result.stderr.strip() == "state_config.current_state must be a non-empty string"


def test_verify_runtime_ops_health_rejects_malformed_state_config_json(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    state_config_path = tmp_path / "state_config.json"
    state_config_path.write_text("{", encoding="utf-8")

    result = run_cli(
        state_path,
        db_path,
        latest_ngi_path,
        env={"LOBSTER_STATE_CONFIG_PATH": str(state_config_path)},
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "state_config payload must be valid JSON"


def test_verify_runtime_ops_health_rejects_falsy_malformed_state_config_states(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    state_config_path = tmp_path / "state_config.json"
    state_config_path.write_text(
        json.dumps({"current_state": "ACTIVE_TRUCE", "states": []}),
        encoding="utf-8",
    )

    result = run_cli(
        state_path,
        db_path,
        latest_ngi_path,
        env={"LOBSTER_STATE_CONFIG_PATH": str(state_config_path)},
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "state_config.states must be a JSON object"


def test_verify_runtime_ops_health_rejects_malformed_state_config_current_state_bundle(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    state_config_path = tmp_path / "state_config.json"
    state_config_path.write_text(
        json.dumps({"current_state": "ACTIVE_TRUCE", "states": {"ACTIVE_TRUCE": []}}),
        encoding="utf-8",
    )

    result = run_cli(
        state_path,
        db_path,
        latest_ngi_path,
        env={"LOBSTER_STATE_CONFIG_PATH": str(state_config_path)},
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "state_config.states.ACTIVE_TRUCE must be a JSON object"


def test_verify_runtime_ops_health_rejects_missing_state_config_current_state_bundle(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    state_config_path = tmp_path / "state_config.json"
    state_config_path.write_text(
        json.dumps({"current_state": "ACTIVE_TRUCE", "states": {}}),
        encoding="utf-8",
    )

    result = run_cli(
        state_path,
        db_path,
        latest_ngi_path,
        env={"LOBSTER_STATE_CONFIG_PATH": str(state_config_path)},
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "state_config.states.ACTIVE_TRUCE must be a JSON object"


def test_verify_runtime_ops_health_rejects_malformed_state_config_fallback_target(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    state_config_path = tmp_path / "state_config.json"
    state_config_path.write_text(
        json.dumps(
            {
                "current_state": "ACTIVE_TRUCE",
                "states": {
                    "ACTIVE_TRUCE": {
                        "fallback_target": ["1517835"],
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
    assert result.stdout == ""
    assert result.stderr.strip() == "state_config.fallback_target must be a JSON object"


def test_verify_runtime_ops_health_ignores_ambiguous_runtime_boolean_for_rollover_rank(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    write_runtime_source(
        runtime_source_path,
        items=[
            {
                "external_id": "ambiguous-1518001",
                "title": "Ambiguous successor market",
                "url": "ambiguous-successor",
                "collected_at_utc": "2099-01-01T00:10:00+00:00",
                "metadata": {
                    "market_id": "ambiguous-1518001",
                    "slug": "ambiguous-successor",
                    "yes_probability": 0.39,
                    "active": True,
                    "closed": False,
                    "accepting_orders": "unknown",
                    "source_config": {"label": "Ambiguous successor market"},
                },
            },
            {
                "external_id": "rollover-1518000",
                "title": "Open successor market",
                "url": "open-successor",
                "collected_at_utc": "2099-01-01T00:05:00+00:00",
                "metadata": {
                    "market_id": "rollover-1518000",
                    "slug": "open-successor",
                    "yes_probability": 0.42,
                    "active": True,
                    "closed": False,
                    "accepting_orders": True,
                    "source_config": {"label": "Open successor market"},
                },
            },
        ],
    )

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["rollover_candidate"]["market_id"] == "rollover-1518000"
    assert payload["rollover_candidate"]["market_accepting_orders"] is True


def test_verify_runtime_ops_health_rejects_ambiguous_rollover_candidate(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    write_runtime_source(
        runtime_source_path,
        items=[
            {
                "external_id": "ambiguous-1518001",
                "title": "Ambiguous successor market",
                "url": "ambiguous-successor",
                "collected_at_utc": "2099-01-01T00:10:00+00:00",
                "metadata": {
                    "market_id": "ambiguous-1518001",
                    "slug": "ambiguous-successor",
                    "yes_probability": 0.39,
                    "active": True,
                    "closed": False,
                    "accepting_orders": "unknown",
                    "source_config": {"label": "Ambiguous successor market"},
                },
            }
        ],
    )

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["closed_target_blocking"] is True
    assert payload["rollover_candidate"] is None
    assert payload["rollover_candidate_blocker"] == "no_explicit_open_accepting_successor"
    assert payload["rollover_candidate_diagnostics"] == {
        "current_market_id": "1517836",
        "successor_count": 1,
        "open_successor_count": 1,
        "accepting_orders_count": 0,
        "explicit_open_accepting_count": 0,
        "sample_successors": [
            {
                "market_id": "ambiguous-1518001",
                "market_slug": "ambiguous-successor",
                "market_question": "Ambiguous successor market",
                "market_yes_probability": 0.39,
                "market_closed": False,
                "market_accepting_orders": None,
            }
        ],
    }
    assert payload["active_target_reselection"]["rollover_candidate_diagnostics"] == payload[
        "rollover_candidate_diagnostics"
    ]


def test_verify_runtime_ops_health_rejects_malformed_rollover_candidate_identity(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    write_runtime_source(
        runtime_source_path,
        items=[
            {
                "external_id": "rollover-1518000",
                "title": "Open successor market",
                "url": "open-successor",
                "collected_at_utc": "2099-01-01T00:05:00+00:00",
                "metadata": {
                    "market_id": ["rollover-1518000"],
                    "slug": "open-successor",
                    "yes_probability": 0.42,
                    "active": True,
                    "closed": False,
                    "accepting_orders": True,
                    "source_config": {"label": "Open successor market"},
                },
            }
        ],
    )

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert (
        result.stderr.strip()
        == "runtime_source evidence.items[0].metadata.market_id must be a non-empty string"
    )


def test_verify_runtime_ops_health_requires_selected_rollover_candidate_question(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    write_runtime_source(
        runtime_source_path,
        items=[
            {
                "external_id": "rollover-1518000",
                "url": "open-successor",
                "collected_at_utc": "2099-01-01T00:05:00+00:00",
                "metadata": {
                    "market_id": "rollover-1518000",
                    "slug": "open-successor",
                    "yes_probability": 0.42,
                    "active": True,
                    "closed": False,
                    "accepting_orders": True,
                    "source_config": {"label": "Open successor market"},
                },
            }
        ],
    )

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "rollover_candidate.market_question must be a non-empty string"


def test_verify_runtime_ops_health_rejects_malformed_runtime_source_run_timestamp(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    write_runtime_source(
        runtime_source_path,
        items=[
            {
                "external_id": "rollover-1518000",
                "title": "Open successor market",
                "url": "open-successor",
                "collected_at_utc": "2099-01-01T00:05:00+00:00",
                "metadata": {
                    "market_id": "rollover-1518000",
                    "slug": "open-successor",
                    "yes_probability": 0.42,
                    "active": True,
                    "closed": False,
                    "accepting_orders": True,
                    "source_config": {"label": "Open successor market"},
                },
            }
        ],
    )
    runtime_source = json.loads(runtime_source_path.read_text(encoding="utf-8"))
    runtime_source["ran_at_utc"] = "not-a-timestamp"
    runtime_source_path.write_text(json.dumps(runtime_source), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "runtime_source.ran_at_utc must be an ISO-8601 timestamp"


def test_verify_runtime_ops_health_fails_when_runtime_source_path_is_missing(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )

    result = run_cli(state_path, db_path, latest_ngi_path, tmp_path / "missing-runtime-source.json")

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "missing runtime_source payload"


def test_verify_runtime_ops_health_fails_when_runtime_source_is_not_an_object(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    runtime_source_path.write_text(json.dumps([]), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "runtime_source payload must be a JSON object"


def test_verify_runtime_ops_health_fails_when_runtime_source_items_is_not_a_list(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    runtime_source_path.write_text(
        json.dumps({"schema_version": "v1", "evidence": {"items": {"market_id": "rollover-1518000"}}}),
        encoding="utf-8",
    )

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "runtime_source evidence.items must be a list"


def test_verify_runtime_ops_health_fails_when_runtime_source_item_is_not_an_object(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    runtime_source_path.write_text(
        json.dumps({"schema_version": "v1", "evidence": {"items": ["rollover-1518000"]}}),
        encoding="utf-8",
    )

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "runtime_source evidence.items[0] must be a JSON object"


def test_verify_runtime_ops_health_fails_when_runtime_source_item_metadata_is_not_an_object(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    runtime_source_path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "evidence": {
                    "items": [
                        {
                            "external_id": "rollover-1518000",
                            "title": "Open successor market",
                            "metadata": "not-a-json-object",
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "runtime_source evidence.items[0].metadata must be a JSON object"


def test_verify_runtime_ops_health_fails_when_runtime_source_item_source_config_is_not_an_object(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    runtime_source_path = tmp_path / "polymarket-runtime.json"
    runtime_source_path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "evidence": {
                    "items": [
                        {
                            "external_id": "rollover-1518000",
                            "title": "Open successor market",
                            "metadata": {
                                "market_id": "rollover-1518000",
                                "closed": False,
                                "accepting_orders": True,
                                "source_config": "not-a-json-object",
                            },
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == (
        "runtime_source evidence.items[0].metadata.source_config must be a JSON object"
    )


def test_verify_runtime_ops_health_fails_closed_on_ambiguous_active_target_status(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
    )
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["target_detail"]["market_closed"] = "unknown"
    latest_ngi["target_detail"]["market_accepting_orders"] = "unknown"
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["market_closed"] is None
    assert payload["market_accepting_orders"] is None
    assert payload["closed_target_blocking"] is True
    assert payload["reselection_required"] is True
    assert payload["next_contract_action"] == "reselect_active_target"
    assert payload["blockers"] == ["market_closed=unknown", "market_accepting_orders=unknown"]


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
    assert payload["closed_target_blocking"] is False
    assert payload["reselection_required"] is False
    assert payload["next_contract_action"] == "keep_active_target"
    assert payload["rollover_candidate"] is None
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


def test_verify_runtime_ops_health_fails_when_probability_fields_are_malformed(
    tmp_path: Path,
):
    for context, key, replacement in (
        ("latest_ngi", "first_principles_probability", True),
        ("latest_ngi", "first_principles_probability", float("nan")),
        ("target_detail", "market_yes_probability", "0.62"),
        ("target_detail", "market_yes_probability", 1.2),
        ("target_detail", "market_yes_probability", float("inf")),
    ):
        case_dir = tmp_path / f"{context}-{key}-{str(replacement).lower()}"
        case_dir.mkdir()
        state_path = case_dir / "STATE.yaml"
        state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
        db_path = case_dir / "intelligence_store.sqlite"
        write_db(db_path, "2099-01-01T00:00:00+00:00")
        latest_ngi_path = case_dir / "latest_ngi.json"
        write_latest_ngi(
            latest_ngi_path,
            first_principles_probability=0.52,
            market_yes_probability=0.62,
        )
        latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
        if context == "latest_ngi":
            latest_ngi[key] = replacement
        else:
            latest_ngi["target_detail"][key] = replacement
        latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

        result = run_cli(state_path, db_path, latest_ngi_path)

        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr.strip() == f"{context}.{key} must be a JSON number between 0 and 1"


def test_verify_runtime_ops_health_rejects_malformed_probability_mode(tmp_path: Path):
    for context in ("target_detail", "latest_ngi"):
        case_dir = tmp_path / context
        case_dir.mkdir()
        state_path = case_dir / "STATE.yaml"
        state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
        db_path = case_dir / "intelligence_store.sqlite"
        write_db(db_path, "2099-01-01T00:00:00+00:00")
        latest_ngi_path = case_dir / "latest_ngi.json"
        write_latest_ngi(
            latest_ngi_path,
            first_principles_probability=0.52,
            market_yes_probability=0.60,
        )
        latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
        if context == "target_detail":
            latest_ngi["target_detail"]["probability_mode"] = ["yes_is_peace"]
        else:
            latest_ngi["probability_mode"] = ["yes_is_peace"]
        latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

        result = run_cli(state_path, db_path, latest_ngi_path)

        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr.strip() == f"{context}.probability_mode must be a non-empty string"


def test_verify_runtime_ops_health_rejects_malformed_active_target_identity(tmp_path: Path):
    for context, key, replacement in (
        ("market_target", "market_id", ["1517836"]),
        ("market_target", "market_name", 1517836),
        ("target_detail", "market_id", ""),
        ("target_detail", "market_question", ["question"]),
    ):
        case_dir = tmp_path / f"{context}-{key}"
        case_dir.mkdir()
        state_path = case_dir / "STATE.yaml"
        state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
        db_path = case_dir / "intelligence_store.sqlite"
        write_db(db_path, "2099-01-01T00:00:00+00:00")
        latest_ngi_path = case_dir / "latest_ngi.json"
        write_latest_ngi(
            latest_ngi_path,
            first_principles_probability=0.52,
            market_yes_probability=0.60,
        )
        latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
        latest_ngi[context][key] = replacement
        latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

        result = run_cli(state_path, db_path, latest_ngi_path)

        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr.strip() == f"latest_ngi.{context}.{key} must be a non-empty string"


def test_verify_runtime_ops_health_strips_active_target_identity_fields(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
        market_closed=True,
        market_accepting_orders=False,
    )
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["market_target"]["market_id"] = " 1517836 "
    latest_ngi["market_target"]["market_name"] = (
        " Trump announces end of military operations against Iran by June 30th "
    )
    latest_ngi["target_detail"]["market_id"] = " 1517836 "
    latest_ngi["target_detail"]["market_question"] = (
        " Trump announces end of military operations against Iran by June 30th? "
    )
    latest_ngi["target_detail"]["probability_mode"] = " yes_is_peace "
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["market_target_id"] == "1517836"
    assert (
        payload["market_target_name"]
        == "Trump announces end of military operations against Iran by June 30th"
    )
    assert payload["probability_mode"] == "yes_is_peace"
    assert payload["active_target_reselection"]["runtime_target_id"] == "1517836"
    assert (
        payload["active_target_reselection"]["market_question"]
        == "Trump announces end of military operations against Iran by June 30th?"
    )


def test_verify_runtime_ops_health_fails_when_rollover_candidate_probability_is_malformed(
    tmp_path: Path,
):
    for replacement in ("0.42", True, 1.2):
        case_dir = tmp_path / f"runtime-source-yes-probability-{str(replacement).lower()}"
        case_dir.mkdir()
        state_path = case_dir / "STATE.yaml"
        state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
        db_path = case_dir / "intelligence_store.sqlite"
        write_db(db_path, "2099-01-01T00:00:00+00:00")
        latest_ngi_path = case_dir / "latest_ngi.json"
        write_latest_ngi(
            latest_ngi_path,
            first_principles_probability=0.52,
            market_yes_probability=0.60,
            market_closed=True,
            market_accepting_orders=False,
        )
        runtime_source_path = case_dir / "polymarket-runtime.json"
        write_runtime_source(
            runtime_source_path,
            items=[
                {
                    "external_id": "rollover-1518000",
                    "title": "Open successor market",
                    "url": "open-successor",
                    "collected_at_utc": "2099-01-01T00:05:00+00:00",
                    "metadata": {
                        "market_id": "rollover-1518000",
                        "slug": "open-successor",
                        "yes_probability": replacement,
                        "active": True,
                        "closed": False,
                        "accepting_orders": True,
                        "source_config": {"label": "Open successor market"},
                    },
                }
            ],
        )

        result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

        assert result.returncode == 1
        assert result.stdout == ""
        assert (
            result.stderr.strip()
            == "runtime_source evidence.items[0].metadata.yes_probability must be a JSON number between 0 and 1"
        )


def test_verify_runtime_ops_health_fails_when_runtime_source_item_timestamp_is_malformed(
    tmp_path: Path,
):
    for key in ("collected_at_utc", "published_at_utc"):
        case_dir = tmp_path / key
        case_dir.mkdir()
        state_path = case_dir / "STATE.yaml"
        state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
        db_path = case_dir / "intelligence_store.sqlite"
        write_db(db_path, "2099-01-01T00:00:00+00:00")
        latest_ngi_path = case_dir / "latest_ngi.json"
        write_latest_ngi(
            latest_ngi_path,
            first_principles_probability=0.52,
            market_yes_probability=0.60,
            market_closed=True,
            market_accepting_orders=False,
        )
        runtime_source_path = case_dir / "polymarket-runtime.json"
        item = {
            "external_id": "rollover-1518000",
            "title": "Open successor market",
            "url": "open-successor",
            "metadata": {
                "market_id": "rollover-1518000",
                "slug": "open-successor",
                "yes_probability": 0.42,
                "active": True,
                "closed": False,
                "accepting_orders": True,
                "source_config": {"label": "Open successor market"},
            },
        }
        item[key] = "not-a-timestamp"
        write_runtime_source(runtime_source_path, items=[item])

        result = run_cli(state_path, db_path, latest_ngi_path, runtime_source_path)

        assert result.returncode == 1
        assert result.stdout == ""
        assert (
            result.stderr.strip()
            == f"runtime_source evidence.items[0].{key} must be an ISO-8601 timestamp"
        )


def test_verify_runtime_ops_health_fails_when_latest_ngi_target_detail_is_not_an_object(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    latest_ngi_path.write_text(
        json.dumps(
            {
                "timestamp_utc": "2099-01-01T00:00:00+00:00",
                "first_principles_probability": 0.52,
                "target_detail": ["not-a-json-object"],
            }
        ),
        encoding="utf-8",
    )

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "latest_ngi.target_detail must be a JSON object"


def test_verify_runtime_ops_health_fails_when_latest_ngi_payload_is_not_an_object(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    latest_ngi_path.write_text(json.dumps(["not-a-json-object"]), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "latest_ngi payload must be a JSON object"


def test_verify_runtime_ops_health_fails_when_latest_ngi_market_target_is_not_an_object(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    latest_ngi_path.write_text(
        json.dumps(
            {
                "timestamp_utc": "2099-01-01T00:00:00+00:00",
                "first_principles_probability": 0.52,
                "market_target": "not-a-json-object",
                "target_detail": {"market_yes_probability": 0.645},
            }
        ),
        encoding="utf-8",
    )

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "latest_ngi.market_target must be a JSON object"


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


def test_verify_runtime_ops_health_fails_when_latest_ngi_timestamp_is_malformed(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    latest_ngi_path.write_text(
        json.dumps(
            {
                "timestamp_utc": "not-a-timestamp",
                "first_principles_probability": 0.52,
                "target_detail": {"market_yes_probability": 0.645},
            }
        ),
        encoding="utf-8",
    )

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "latest_ngi.timestamp_utc must be an ISO-8601 timestamp"


def test_verify_runtime_ops_health_fails_when_market_snapshot_timestamp_is_malformed(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "not-a-timestamp")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.52,
        market_yes_probability=0.60,
    )

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "market_snapshots.snapshot_at_utc must be an ISO-8601 timestamp"
