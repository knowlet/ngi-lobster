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


def run_cli(state_path: Path, db_path: Path, latest_ngi_path: Path, runtime_source_path: Path | None = None):
    argv = [sys.executable, str(SCRIPT), str(state_path), str(db_path), str(latest_ngi_path)]
    if runtime_source_path is not None:
        argv.append(str(runtime_source_path))
    return subprocess.run(
        argv,
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
