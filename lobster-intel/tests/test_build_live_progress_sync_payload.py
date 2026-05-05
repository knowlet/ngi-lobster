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
    target_contract_match: object = True,
):
    alert_disposition = {
        "decision": "would_send",
        "should_send": True,
        "reason_code": "ngi_changed_major",
        "target_contract_match": target_contract_match,
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
    assert payload["blocking_summary"] == {
        "runtime_target_id": "1517836",
        "market_question": "Trump announces end of military operations against Iran by June 30th?",
        "reselection_required": False,
        "next_contract_action": "keep_active_target",
        "rollover_candidate_blocker": None,
        "rollover_candidate_diagnostics": None,
        "rollover_candidate": None,
    }
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


def test_build_live_progress_sync_payload_exports_active_target_reselection_acceptance(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.12,
        market_yes_probability=0.54,
    )
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["target_detail"]["market_closed"] = True
    latest_ngi["target_detail"]["market_accepting_orders"] = False
    latest_ngi["alert_disposition"]["decision"] = "suppressed"
    latest_ngi["alert_disposition"]["should_send"] = False
    latest_ngi["alert_disposition"].pop("delivery_proof")
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")
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

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["sync_status"] == "blocking"
    assert payload["active_target_reselection"] == {
        "runtime_target_id": "1517836",
        "market_question": "Trump announces end of military operations against Iran by June 30th?",
        "reselection_required": True,
        "next_contract_action": "reselect_active_target",
        "rollover_candidate_blocker": None,
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
    }


def test_build_live_progress_sync_payload_uses_state_config_fallback_when_runtime_source_has_no_successor(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        first_principles_probability=0.12,
        market_yes_probability=0.54,
    )
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["target_detail"]["market_closed"] = True
    latest_ngi["target_detail"]["market_accepting_orders"] = False
    latest_ngi["alert_disposition"]["decision"] = "suppressed"
    latest_ngi["alert_disposition"]["should_send"] = False
    latest_ngi["alert_disposition"].pop("delivery_proof")
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")
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

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(state_path), str(db_path), str(latest_ngi_path), str(runtime_source_path)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        env={**__import__("os").environ, "LOBSTER_STATE_CONFIG_PATH": str(state_config_path)},
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["active_target_reselection"]["rollover_candidate"] == {
        "market_id": "1517835",
        "market_slug": "fallback-market",
        "market_name": "Fallback target",
        "market_question": "Fallback target",
        "probability_mode": "yes_is_peace",
        "source": "state_config_fallback",
        "state": "ACTIVE_TRUCE",
    }
    assert (
        payload["active_target_reselection"]["rollover_candidate_blocker"]
        == "configured_successor_pending_validation"
    )


def test_build_live_progress_sync_payload_requires_operator_market_question(
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
    )
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["target_detail"].pop("market_question")
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "latest_ngi.target_detail.market_question must be a non-empty string"


def test_build_live_progress_sync_payload_strips_operator_market_question(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["target_detail"]["market_question"] = (
        "  Trump announces end of military operations against Iran by June 30th?  "
    )
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert (
        payload["blocking_summary"]["market_question"]
        == "Trump announces end of military operations against Iran by June 30th?"
    )
    assert (
        payload["market_target"]["market_question"]
        == "Trump announces end of military operations against Iran by June 30th?"
    )


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


def test_build_live_progress_sync_payload_treats_serialized_should_send_as_positive_delivery(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, include_delivery_proof=False)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["alert_disposition"]["decision"] = "suppressed"
    latest_ngi["alert_disposition"]["should_send"] = "true"
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "missing latest_ngi.alert_disposition.delivery_proof"


def test_build_live_progress_sync_payload_rejects_ambiguous_should_send(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["alert_disposition"]["decision"] = "suppressed"
    latest_ngi["alert_disposition"]["should_send"] = "unknown"
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert (
        result.stderr.strip()
        == "latest_ngi.alert_disposition.should_send must be a boolean-equivalent value"
    )


def test_build_live_progress_sync_payload_treats_explicit_false_should_send_as_non_positive(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, include_delivery_proof=False)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["alert_disposition"]["should_send"] = False
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0, result.stderr
    sync_payload = json.loads(result.stdout)
    assert "delivery_proof" not in sync_payload["alert_disposition"]


def test_build_live_progress_sync_payload_rejects_malformed_delivery_proof(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, include_delivery_proof=False)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["alert_disposition"]["decision"] = "suppressed"
    latest_ngi["alert_disposition"]["should_send"] = False
    latest_ngi["alert_disposition"]["delivery_proof"] = ["not-a-json-object"]
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "latest_ngi.alert_disposition.delivery_proof must be a JSON object"


def test_build_live_progress_sync_payload_rejects_malformed_non_positive_delivery_proof_fields(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["alert_disposition"]["decision"] = "suppressed"
    latest_ngi["alert_disposition"]["should_send"] = False
    latest_ngi["alert_disposition"]["delivery_proof"]["boundary"] = 123
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert (
        result.stderr.strip()
        == "latest_ngi.alert_disposition.delivery_proof.boundary must be a non-empty string"
    )


def test_build_live_progress_sync_payload_rejects_malformed_contract_envelope_fields(
    tmp_path: Path,
):
    for field, replacement in (
        ("decision", ["suppressed"]),
        ("reason_code", ["not-a-string"]),
        ("contract_version", 123),
        ("e2e_run_id", " "),
    ):
        case_dir = tmp_path / field
        case_dir.mkdir()
        state_path = case_dir / "STATE.yaml"
        state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
        db_path = case_dir / "intelligence_store.sqlite"
        write_db(db_path, "2099-01-01T00:00:00+00:00")
        latest_ngi_path = case_dir / "latest_ngi.json"
        write_latest_ngi(latest_ngi_path)
        latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
        latest_ngi["alert_disposition"][field] = replacement
        latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

        result = run_cli(state_path, db_path, latest_ngi_path)

        assert result.returncode == 1
        assert result.stdout == ""
        assert (
            result.stderr.strip()
            == f"latest_ngi.alert_disposition.{field} must be a non-empty string"
        )


def test_build_live_progress_sync_payload_strips_contract_envelope_basis_fields(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, include_delivery_proof=False)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi.pop("explain")
    latest_ngi["alert_disposition"]["decision"] = " suppressed "
    latest_ngi["alert_disposition"]["should_send"] = False
    latest_ngi["alert_disposition"]["reason_code"] = " no_change "
    latest_ngi["alert_disposition"]["contract_version"] = " legacy-monitor-contract-v1 "
    latest_ngi["alert_disposition"]["e2e_run_id"] = " legacy-monitor-20260501T002054.879803Z "
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0, result.stderr
    sync_payload = json.loads(result.stdout)
    assert (
        sync_payload["basis_lines"]["logistics"]
        == "live alert disposition suppressed / no_change"
    )
    assert sync_payload["alert_disposition"]["contract_version"] == "legacy-monitor-contract-v1"
    assert sync_payload["alert_disposition"]["e2e_run_id"] == "legacy-monitor-20260501T002054.879803Z"


def test_build_basis_lines_falls_back_to_unknown_for_blank_contract_fields():
    import importlib.util

    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("build_live_progress_sync_payload", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    latest_ngi = {
        "alert_disposition": {"decision": "   ", "reason_code": "	"},
    }
    ops_health = {
        "first_principles_probability": 0.25,
        "market_yes_probability": 0.75,
        "blockers": [],
    }

    basis = module._build_basis_lines(latest_ngi=latest_ngi, ops_health=ops_health)

    assert basis["logistics"] == "live alert disposition unknown / unknown"


def test_build_live_progress_sync_payload_requires_machine_readable_positive_delivery_proof(tmp_path: Path):
    for missing_key in ("boundary", "proof_id"):
        case_dir = tmp_path / missing_key
        case_dir.mkdir()
        state_path = case_dir / "STATE.yaml"
        state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
        db_path = case_dir / "intelligence_store.sqlite"
        write_db(db_path, "2099-01-01T00:00:00+00:00")
        latest_ngi_path = case_dir / "latest_ngi.json"
        write_latest_ngi(latest_ngi_path)
        latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
        latest_ngi["alert_disposition"]["delivery_proof"].pop(missing_key)
        if missing_key == "proof_id":
            latest_ngi["alert_disposition"]["delivery_proof"].pop("sink_message_id")
        latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

        result = run_cli(state_path, db_path, latest_ngi_path)

        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr.strip() == f"missing latest_ngi.alert_disposition.delivery_proof.{missing_key}"


def test_build_live_progress_sync_payload_requires_string_positive_delivery_proof_fields(tmp_path: Path):
    for field, replacement in (("boundary", 123), ("proof_id", ["not-a-string"])):
        case_dir = tmp_path / field
        case_dir.mkdir()
        state_path = case_dir / "STATE.yaml"
        state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
        db_path = case_dir / "intelligence_store.sqlite"
        write_db(db_path, "2099-01-01T00:00:00+00:00")
        latest_ngi_path = case_dir / "latest_ngi.json"
        write_latest_ngi(latest_ngi_path)
        latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
        latest_ngi["alert_disposition"]["delivery_proof"][field] = replacement
        if field == "proof_id":
            latest_ngi["alert_disposition"]["delivery_proof"].pop("sink_message_id")
        latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

        result = run_cli(state_path, db_path, latest_ngi_path)

        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr.strip() == (
            f"latest_ngi.alert_disposition.delivery_proof.{field} must be a non-empty string"
        )


def test_build_live_progress_sync_payload_allows_sink_message_id_when_proof_id_is_blank(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["alert_disposition"]["delivery_proof"]["proof_id"] = " "
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0, result.stderr
    sync_payload = json.loads(result.stdout)
    assert (
        sync_payload["alert_disposition"]["delivery_proof"]["sink_message_id"]
        == "heartbeat:legacy-monitor-20260501T002054.879803Z"
    )


def test_build_live_progress_sync_payload_omits_blank_delivery_proof_fields(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["alert_disposition"]["delivery_proof"]["proof_id"] = " "
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0, result.stderr
    sync_payload = json.loads(result.stdout)
    assert "proof_id" not in sync_payload["alert_disposition"]["delivery_proof"]
    assert (
        sync_payload["alert_disposition"]["delivery_proof"]["sink_message_id"]
        == "heartbeat:legacy-monitor-20260501T002054.879803Z"
    )


def test_build_live_progress_sync_payload_rejects_positive_delivery_without_contract_match(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, target_contract_match="false")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "positive latest_ngi.alert_disposition.target_contract_match must be true"


def test_build_live_progress_sync_payload_rejects_ambiguous_contract_match(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, target_contract_match="unknown")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "positive latest_ngi.alert_disposition.target_contract_match must be true"


def test_build_live_progress_sync_payload_rejects_ambiguous_non_positive_contract_match(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, include_delivery_proof=False)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["alert_disposition"]["decision"] = "suppressed"
    latest_ngi["alert_disposition"]["should_send"] = False
    latest_ngi["alert_disposition"]["target_contract_match"] = "unknown"
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert (
        result.stderr.strip()
        == "latest_ngi.alert_disposition.target_contract_match must be a boolean-equivalent value"
    )


def test_build_live_progress_sync_payload_rejects_stale_latest_ngi(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(
        latest_ngi_path,
        timestamp_utc="2026-04-20T00:00:00+00:00",
        first_principles_probability=0.52,
        market_yes_probability=0.60,
    )

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "latest_ngi.json is stale"


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


def test_build_live_progress_sync_payload_strips_delivery_proof_fields(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["alert_disposition"]["delivery_proof"] = {
        "boundary": " openclaw_heartbeat ",
        "proof_id": " heartbeat:legacy-monitor-20260501T002054.879803Z ",
        "sink_message_id": " heartbeat:legacy-monitor-20260501T002054.879803Z ",
    }
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0, result.stderr
    sync_payload = json.loads(result.stdout)
    assert sync_payload["alert_disposition"]["delivery_proof"] == {
        "boundary": "openclaw_heartbeat",
        "proof_id": "heartbeat:legacy-monitor-20260501T002054.879803Z",
        "sink_message_id": "heartbeat:legacy-monitor-20260501T002054.879803Z",
    }


def test_build_live_progress_sync_payload_omits_empty_non_positive_delivery_proof(
    tmp_path: Path,
):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["alert_disposition"]["decision"] = "suppressed"
    latest_ngi["alert_disposition"]["should_send"] = False
    latest_ngi["alert_disposition"]["target_contract_match"] = False
    latest_ngi["alert_disposition"]["delivery_proof"] = {
        "boundary": " ",
        "proof_id": "",
        "sink_message_id": " ",
    }
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0, result.stderr
    sync_payload = json.loads(result.stdout)
    assert "delivery_proof" not in sync_payload["alert_disposition"]


def test_build_live_progress_sync_payload_canonicalizes_alert_boolean_fields(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["alert_disposition"]["should_send"] = " yes "
    latest_ngi["alert_disposition"]["target_contract_match"] = " on "
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 0, result.stderr
    sync_payload = json.loads(result.stdout)
    assert sync_payload["alert_disposition"]["should_send"] is True
    assert sync_payload["alert_disposition"]["target_contract_match"] is True


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


def test_build_live_progress_sync_payload_rejects_malformed_latest_ngi_json(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    latest_ngi_path.write_text("{", encoding="utf-8")

    result = run_cli(state_path, db_path, latest_ngi_path)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "latest_ngi payload must be valid JSON"


def test_build_live_progress_sync_payload_fails_when_latest_ngi_is_not_an_object(tmp_path: Path):
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


def test_build_live_progress_sync_payload_fails_when_latest_ngi_objects_are_malformed(tmp_path: Path):
    for key in ("market_target", "target_detail", "alert_disposition"):
        case_dir = tmp_path / key
        case_dir.mkdir()
        state_path = case_dir / "STATE.yaml"
        state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
        db_path = case_dir / "intelligence_store.sqlite"
        write_db(db_path, "2099-01-01T00:00:00+00:00")
        latest_ngi_path = case_dir / "latest_ngi.json"
        write_latest_ngi(latest_ngi_path)
        latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
        latest_ngi[key] = ["not-a-json-object"]
        latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")

        result = run_cli(state_path, db_path, latest_ngi_path)

        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr.strip() == f"latest_ngi.{key} must be a JSON object"


def test_build_live_progress_sync_payload_exports_rollover_candidate_when_target_is_closed(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, first_principles_probability=0.52, market_yes_probability=0.60)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["target_detail"]["market_closed"] = True
    latest_ngi["target_detail"]["market_accepting_orders"] = False
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")
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

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["sync_status"] == "blocking"
    assert payload["blocking_summary"] == {
        "runtime_target_id": "1517836",
        "market_question": "Trump announces end of military operations against Iran by June 30th?",
        "reselection_required": True,
        "next_contract_action": "reselect_active_target",
        "rollover_candidate_blocker": None,
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
    }
    assert payload["active_target"] == {
        "market_closed": True,
        "market_accepting_orders": False,
        "closed_target_blocking": True,
        "reselection_required": True,
        "next_contract_action": "reselect_active_target",
        "rollover_candidate_blocker": None,
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
    }
    assert payload["blockers"] == ["market_closed=true", "market_accepting_orders=false"]


def test_build_live_progress_sync_payload_explains_missing_rollover_candidate(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\n', encoding="utf-8")
    db_path = tmp_path / "intelligence_store.sqlite"
    write_db(db_path, "2099-01-01T00:00:00+00:00")
    latest_ngi_path = tmp_path / "latest_ngi.json"
    write_latest_ngi(latest_ngi_path, first_principles_probability=0.52, market_yes_probability=0.60)
    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi["target_detail"]["market_closed"] = True
    latest_ngi["target_detail"]["market_accepting_orders"] = False
    latest_ngi_path.write_text(json.dumps(latest_ngi), encoding="utf-8")
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

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["blocking_summary"] == {
        "runtime_target_id": "1517836",
        "market_question": "Trump announces end of military operations against Iran by June 30th?",
        "reselection_required": True,
        "next_contract_action": "reselect_active_target",
        "rollover_candidate_blocker": "no_explicit_open_accepting_successor",
        "rollover_candidate_diagnostics": {
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
        },
        "rollover_candidate": None,
    }
    assert payload["active_target"]["reselection_required"] is True
    assert payload["active_target"]["rollover_candidate"] is None
    assert (
        payload["active_target"]["rollover_candidate_blocker"]
        == "no_explicit_open_accepting_successor"
    )
    assert payload["active_target"]["rollover_candidate_diagnostics"] == {
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
    assert payload["contract_action"]["rollover_candidate_diagnostics"] == payload["active_target"][
        "rollover_candidate_diagnostics"
    ]
