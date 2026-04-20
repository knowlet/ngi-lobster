from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
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

from lobster_runtime import (
    ThesisRuntimeInput,
    compare_targets,
    rebuild_runtime_index,
    replay_compare_from_artifacts,
    run_thesis_runtime,
    trace_run_lineage,
)
from lobster_runtime import runtime_spine
from lobster_runtime.runtime_spine import load_thesis_runtime_inputs


def _source_payloads() -> tuple[dict, dict, dict]:
    official = {
        "plugin": "official-statements-tracker",
        "run_id": "official-20260419T120000Z",
        "ran_at_utc": "2026-04-19T12:00:00+00:00",
        "evidence": {
            "items": [
                {
                    "external_id": "stmt-1",
                    "title": "Official statement warns of retaliation",
                    "description": "Leadership says retaliation remains on the table.",
                    "url": "https://example.com/statement-1",
                    "published_at_utc": "2026-04-19T11:30:00+00:00",
                    "source_id": "official-feed",
                    "source_type": "official_statement",
                    "metadata": {
                        "semantic_tags": ["official_statement", "retaliation"],
                        "location": "Tehran",
                    },
                }
            ],
        },
    }
    watchlist = {
        "plugin": "watchlist-tracker",
        "run_id": "watch-20260419T121500Z",
        "ran_at_utc": "2026-04-19T12:15:00+00:00",
        "evidence": {
            "items": [
                {
                    "external_id": "watch-1",
                    "title": "Convoy and energy market stress signal",
                    "description": "Analyst watchlist flags elevated logistics and energy stress.",
                    "url": "https://example.com/watch-1",
                    "published_at_utc": "2026-04-19T12:10:00+00:00",
                    "source_id": "watch-feed",
                    "source_type": "analyst_watchlist",
                    "metadata": {
                        "semantic_tags": ["watchlist", "energy_proxy", "logistics_proxy"],
                        "location": "Gulf",
                    },
                }
            ],
        },
    }
    polymarket = {
        "plugin": "polymarket-tracker",
        "run_id": "poly-20260419T122000Z",
        "ran_at_utc": "2026-04-19T12:20:00+00:00",
        "evidence": {
            "items": [
                {
                    "external_id": "1517836",
                    "title": "Military operations end by June 30?",
                    "url": "military-operations-end-by-june-30",
                    "source_id": "polymarket",
                    "source_type": "prediction_market",
                    "metadata": {
                        "market_id": "1517836",
                        "slug": "military-operations-end-by-june-30",
                        "yes_probability": 0.72,
                        "active": True,
                        "closed": False,
                        "semantic_frame": "military_operations_end_by_deadline",
                        "probability_direction": "yes_is_peace",
                    },
                }
            ],
        },
    }
    return official, watchlist, polymarket


def _target_registry() -> list[dict]:
    return [
        {
            "market_id": "1517836",
            "market_slug": "military-operations-end-by-june-30",
            "market_question": "Military operations end by June 30?",
            "semantic_frame": "military_operations_end_by_deadline",
            "probability_direction": "yes_is_peace",
            "aliases": ["operations end by june 30", "june 30 end market"],
            "resolution_mode": "registry_first",
        }
    ]


def _install_runtime_source_artifacts(
    workspace: Path,
    official: dict,
    watchlist: dict,
    polymarket: dict,
) -> None:
    source_root = workspace / "lobster-intel" / "data" / "runtime" / "sources"
    for source_id, payload in [
        ("official-statements-tracker", official),
        ("watchlist-tracker", watchlist),
        ("polymarket-tracker", polymarket),
    ]:
        source_dir = source_root / source_id
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "latest.json").write_text(json.dumps(payload), encoding="utf-8")


def _install_thesis_registry(workspace: Path, thesis_id: str, entries: list[dict]) -> Path:
    registry_path = workspace / "lobster-intel" / "data" / "runtime" / "thesis-registry" / f"{thesis_id}.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(entries), encoding="utf-8")
    return registry_path


def test_runtime_spine_run_writes_full_artifact_chain(tmp_path: Path):
    official, watchlist, polymarket = _source_payloads()

    result = run_thesis_runtime(
        ThesisRuntimeInput(
            thesis_id="gooaye",
            workspace_dir=tmp_path,
            official_statements=official,
            watchlist=watchlist,
            polymarket=polymarket,
            target_registry=_target_registry(),
            semantic_frame="military_operations_end_by_deadline",
            probability_direction="yes_is_peace",
            state="ACTIVE_TRUCE",
            now_utc="2026-04-19T12:30:00+00:00",
        )
    )

    runtime_snapshot = result.runtime_snapshot
    compare_artifact = result.compare_artifact
    alert_artifact = result.alert_artifact
    delivery_receipt = result.delivery_receipt

    assert runtime_snapshot["state"] == "ACTIVE_TRUCE"
    assert runtime_snapshot["compare_mode"] == "full_compare"
    assert runtime_snapshot["P_AI"] == pytest.approx(0.25)
    assert runtime_snapshot["market_implied_probability"] == pytest.approx(0.72)
    assert runtime_snapshot["ngi_gap"] == pytest.approx(-0.47)
    assert runtime_snapshot["active_target"]["market_id"] == "1517836"
    assert compare_artifact["compare_mode"] == "full_compare"
    assert compare_artifact["runtime_target_id"] == "1517836"
    assert compare_artifact["market_target_id"] == "1517836"
    assert alert_artifact["should_send"] is True
    assert alert_artifact["reason_code"] == "first_run_gap_detected"
    assert delivery_receipt["sink"] == "openclaw_heartbeat"
    assert delivery_receipt["delivery_status"] == "delivered"

    assert Path(result.paths["runtime_latest"]).exists()
    assert Path(result.paths["compare"]).exists()
    assert Path(result.paths["delivery_receipt"]).exists()

    replayed_compare = replay_compare_from_artifacts(tmp_path, "gooaye", result.run_id)
    assert replayed_compare["compare_mode"] == compare_artifact["compare_mode"]
    assert replayed_compare["runtime_target_id"] == compare_artifact["runtime_target_id"]

    lineage = trace_run_lineage(tmp_path, "gooaye", result.run_id)
    assert lineage["receipt_to_alert"] == [delivery_receipt["alert_artifact_id"]]
    assert len(lineage["fusion_to_observations"]) >= 2
    assert len(lineage["observation_to_evidence"]) >= 2


def test_compare_engine_routes_full_degraded_and_suppressed():
    full_compare = compare_targets(
        active_target={
            "market_id": "1517836",
            "market_slug": "military-operations-end-by-june-30",
            "market_question": "Military operations end by June 30?",
            "semantic_frame": "military_operations_end_by_deadline",
            "probability_direction": "yes_is_peace",
            "resolution_mode": "registry_first",
            "fallback_used": False,
        },
        market_candidate={
            "market_id": "1517836",
            "market_slug": "military-operations-end-by-june-30",
            "market_question": "Military operations end by June 30?",
            "semantic_frame": "military_operations_end_by_deadline",
            "probability_direction": "yes_is_peace",
        },
    )
    assert full_compare["compare_mode"] == "full_compare"
    assert full_compare["fallback_reason_codes"] == []

    degraded_compare = compare_targets(
        active_target={
            "market_id": "1517836",
            "market_slug": "military-operations-end-by-june-30",
            "market_question": "Military operations end by June 30?",
            "semantic_frame": "military_operations_end_by_deadline",
            "probability_direction": "yes_is_peace",
            "resolution_mode": "live_search_fallback",
            "fallback_used": True,
        },
        market_candidate={
            "market_id": "1517836",
            "market_slug": "military-operations-end-by-june-30",
            "market_question": "Military operations end by June 30?",
            "semantic_frame": "military_operations_end_by_deadline",
            "probability_direction": "yes_is_peace",
        },
    )
    assert degraded_compare["compare_mode"] == "degraded_compare"
    assert "live_search_fallback" in degraded_compare["fallback_reason_codes"]

    suppressed_compare = compare_targets(
        active_target={
            "market_id": "legacy-430",
            "market_slug": "legacy-ceasefire-april-30",
            "market_question": "Ceasefire by April 30?",
            "semantic_frame": "ceasefire_by_april_deadline",
            "probability_direction": "yes_is_peace",
            "resolution_mode": "registry_first",
            "fallback_used": False,
        },
        market_candidate={
            "market_id": "1517836",
            "market_slug": "military-operations-end-by-june-30",
            "market_question": "Military operations end by June 30?",
            "semantic_frame": "military_operations_end_by_deadline",
            "probability_direction": "yes_is_peace",
        },
    )
    assert suppressed_compare["compare_mode"] == "suppressed"
    assert "target_identity_mismatch" in suppressed_compare["fallback_reason_codes"]


def test_parse_iso_returns_offset_aware_datetimes_for_z_and_naive_inputs():
    zulu = runtime_spine._parse_iso("2026-04-19T12:30:00Z")
    naive = runtime_spine._parse_iso("2026-04-19T12:30:00")

    assert zulu == datetime(2026, 4, 19, 12, 30, tzinfo=timezone.utc)
    assert zulu.tzinfo == timezone.utc
    assert naive == datetime(2026, 4, 19, 12, 30, tzinfo=timezone.utc)
    assert naive.tzinfo == timezone.utc


def test_resolve_active_target_avoids_alias_substring_false_positive():
    inp = ThesisRuntimeInput(
        thesis_id="gooaye",
        workspace_dir=".",
        target_registry=[
            {
                "market_id": "registry-war-target",
                "market_question": "War by June?",
                "semantic_frame": "war_by_deadline",
                "probability_direction": "yes_is_peace",
                "aliases": ["war"],
            }
        ],
        semantic_frame="war_by_deadline",
        probability_direction="yes_is_peace",
    )
    observations = [
        {
            "artifact_id": "observation:market:software",
            "event_type": "market_candidate",
            "extractive_rationale": "Software platform launches by June?",
            "metadata": {
                "market_id": "software-1",
                "market_slug": "software-platform-launches-by-june",
                "market_question": "Software platform launches by June?",
                "semantic_frame": "software_release",
                "probability_direction": "yes_is_peace",
                "yes_probability": 0.55,
                "active": True,
                "closed": False,
            },
        }
    ]

    active_target, _market_candidate = runtime_spine.resolve_active_target(inp, observations)

    assert active_target is None
    assert _market_candidate is not None
    assert _market_candidate["market_id"] == "software-1"


def test_runtime_index_can_be_rebuilt_from_artifacts(tmp_path: Path):
    official, watchlist, polymarket = _source_payloads()
    result = run_thesis_runtime(
        ThesisRuntimeInput(
            thesis_id="gooaye",
            workspace_dir=tmp_path,
            official_statements=official,
            watchlist=watchlist,
            polymarket=polymarket,
            target_registry=_target_registry(),
            semantic_frame="military_operations_end_by_deadline",
            probability_direction="yes_is_peace",
            state="ACTIVE_TRUCE",
            now_utc="2026-04-19T12:30:00+00:00",
        )
    )

    db_path = rebuild_runtime_index(tmp_path, "gooaye")
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "select run_id, compare_mode, should_send from runtime_runs where run_id = ?",
            (result.run_id,),
        ).fetchone()
    assert row == (result.run_id, "full_compare", 1)

    db_path.unlink()
    rebuilt_path = rebuild_runtime_index(tmp_path, "gooaye")
    assert rebuilt_path.exists()


def test_rebuild_runtime_index_preserves_runtime_runs_indexes(tmp_path: Path):
    official, watchlist, polymarket = _source_payloads()
    run_thesis_runtime(
        ThesisRuntimeInput(
            thesis_id="gooaye",
            workspace_dir=tmp_path,
            official_statements=official,
            watchlist=watchlist,
            polymarket=polymarket,
            target_registry=_target_registry(),
            semantic_frame="military_operations_end_by_deadline",
            probability_direction="yes_is_peace",
            state="ACTIVE_TRUCE",
            now_utc="2026-04-19T12:30:00+00:00",
        )
    )

    db_path = rebuild_runtime_index(tmp_path, "gooaye")
    with sqlite3.connect(db_path) as conn:
        conn.execute("create index runtime_runs_compare_mode_idx on runtime_runs(compare_mode)")
        conn.commit()

    rebuild_runtime_index(tmp_path, "gooaye")

    with sqlite3.connect(db_path) as conn:
        indexes = {row[0] for row in conn.execute("select name from sqlite_master where type = 'index'")}
    assert "runtime_runs_compare_mode_idx" in indexes


def test_rebuild_runtime_index_closes_sqlite_connection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    official, watchlist, polymarket = _source_payloads()
    run_thesis_runtime(
        ThesisRuntimeInput(
            thesis_id="gooaye",
            workspace_dir=tmp_path,
            official_statements=official,
            watchlist=watchlist,
            polymarket=polymarket,
            target_registry=_target_registry(),
            semantic_frame="military_operations_end_by_deadline",
            probability_direction="yes_is_peace",
            state="ACTIVE_TRUCE",
            now_utc="2026-04-19T12:30:00+00:00",
        )
    )

    real_connect = runtime_spine.sqlite3.connect
    recorded: dict[str, object] = {}

    class RecordingConnection:
        def __init__(self, *args, **kwargs):
            self._inner = real_connect(*args, **kwargs)
            self.closed = False

        def __getattr__(self, name: str):
            return getattr(self._inner, name)

        def __enter__(self):
            self._inner.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            return self._inner.__exit__(exc_type, exc, tb)

        def close(self):
            self.closed = True
            return self._inner.close()

    def recording_connect(*args, **kwargs):
        conn = RecordingConnection(*args, **kwargs)
        recorded["conn"] = conn
        return conn

    monkeypatch.setattr(runtime_spine.sqlite3, "connect", recording_connect)

    rebuild_runtime_index(tmp_path, "gooaye")

    assert "conn" in recorded
    assert getattr(recorded["conn"], "closed") is True


def test_run_thesis_runtime_cli_writes_latest_runtime_snapshot(tmp_path: Path):
    official, watchlist, polymarket = _source_payloads()
    _install_runtime_source_artifacts(tmp_path, official, watchlist, polymarket)
    official_path = tmp_path / "official.json"
    watchlist_path = tmp_path / "watchlist.json"
    polymarket_path = tmp_path / "polymarket.json"
    registry_path = tmp_path / "registry.json"

    official_path.write_text(json.dumps(official), encoding="utf-8")
    watchlist_path.write_text(json.dumps(watchlist), encoding="utf-8")
    polymarket_path.write_text(json.dumps(polymarket), encoding="utf-8")
    registry_path.write_text(json.dumps(_target_registry()), encoding="utf-8")

    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "lobster-intel/scripts/run_thesis_runtime.py",
            "--workspace",
            str(tmp_path),
            "--thesis-id",
            "gooaye",
            "--official",
            str(official_path),
            "--watchlist",
            str(watchlist_path),
            "--polymarket",
            str(polymarket_path),
            "--registry-file",
            str(registry_path),
            "--semantic-frame",
            "military_operations_end_by_deadline",
            "--probability-direction",
            "yes_is_peace",
            "--now-utc",
            "2026-04-19T12:30:00+00:00",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["compare_mode"] == "full_compare"
    assert payload["input_contract"]["source_resolution"]["official_statements"]["mode"] == "explicit"
    assert payload["input_contract"]["source_resolution"]["watchlist"]["mode"] == "explicit"
    assert payload["input_contract"]["source_resolution"]["polymarket"]["mode"] == "explicit"
    assert (tmp_path / Path(payload["artifact_paths"]["runtime_latest"])).exists()
    assert (tmp_path / Path(payload["artifact_paths"]["delivery_receipt"])).exists()


def test_run_thesis_runtime_cli_discovers_installed_source_artifacts(tmp_path: Path):
    official, watchlist, polymarket = _source_payloads()
    _install_runtime_source_artifacts(tmp_path, official, watchlist, polymarket)
    registry_path = _install_thesis_registry(tmp_path, "gooaye", _target_registry())

    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "lobster-intel/scripts/run_thesis_runtime.py",
            "--workspace",
            str(tmp_path),
            "--thesis-id",
            "gooaye",
            "--now-utc",
            "2026-04-19T12:30:00+00:00",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["compare_mode"] == "full_compare"
    assert payload["input_contract"]["source_resolution"]["official_statements"]["mode"] == "discovered"
    assert payload["input_contract"]["source_resolution"]["watchlist"]["mode"] == "discovered"
    assert payload["input_contract"]["source_resolution"]["polymarket"]["mode"] == "discovered"
    assert payload["input_contract"]["source_resolution"]["official_statements"]["path"].endswith(
        "lobster-intel/data/runtime/sources/official-statements-tracker/latest.json"
    )
    assert payload["input_contract"]["registry_resolution"]["mode"] == "discovered"
    assert payload["input_contract"]["registry_resolution"]["path"] == str(registry_path)
    assert Path(payload["artifact_paths"]["runtime_latest"]).exists()


def test_load_thesis_runtime_inputs_prefers_explicit_registry_file(tmp_path: Path):
    official, watchlist, polymarket = _source_payloads()
    _install_runtime_source_artifacts(tmp_path, official, watchlist, polymarket)
    _install_thesis_registry(tmp_path, "gooaye", _target_registry())
    explicit_registry_path = tmp_path / "explicit-registry.json"
    explicit_registry_path.write_text(
        json.dumps(
            [
                {
                    "market_id": "explicit-target",
                    "market_slug": "explicit-market",
                    "market_question": "Explicit market target?",
                    "semantic_frame": "military_operations_end_by_deadline",
                    "probability_direction": "yes_is_peace",
                    "aliases": ["explicit target"],
                    "resolution_mode": "registry_first",
                }
            ]
        ),
        encoding="utf-8",
    )

    payload = load_thesis_runtime_inputs(
        tmp_path,
        thesis_id="gooaye",
        registry_file=explicit_registry_path,
    )

    assert payload["registry_resolution"]["mode"] == "explicit"
    assert payload["registry_resolution"]["path"] == str(explicit_registry_path)
    assert payload["target_registry"][0]["market_id"] == "explicit-target"


def test_run_thesis_runtime_cli_fails_when_installed_source_artifacts_are_missing(tmp_path: Path):
    official, _watchlist, polymarket = _source_payloads()
    source_root = tmp_path / "lobster-intel" / "data" / "runtime" / "sources"
    for source_id, payload in [
        ("official-statements-tracker", official),
        ("polymarket-tracker", polymarket),
    ]:
        source_dir = source_root / source_id
        source_dir.mkdir(parents=True, exist_ok=True)
        (source_dir / "latest.json").write_text(json.dumps(payload), encoding="utf-8")

    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "lobster-intel/scripts/run_thesis_runtime.py",
            "--workspace",
            str(tmp_path),
            "--thesis-id",
            "gooaye",
            "--now-utc",
            "2026-04-19T12:30:00+00:00",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "watchlist-tracker/latest.json" in result.stderr
