#!/usr/bin/env python3
"""
Run NGI fusion monitor, store result, and track whether alert should be sent.
"""
import json
import os
import sys
import subprocess
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOBSTER_PACKAGES = Path(
    os.environ.get("LOBSTER_PACKAGES_DIR")
    or (REPO_ROOT / "lobster-intel" / "packages")
).resolve()
for package_dir in (
    LOBSTER_PACKAGES / "lobster-core",
    LOBSTER_PACKAGES / "lobster-runtime",
    LOBSTER_PACKAGES / "lobster-delivery",
):
    package_dir_str = str(package_dir)
    if package_dir_str not in sys.path:
        sys.path.insert(0, package_dir_str)

from lobster_runtime import (
    TARGET_CONTRACT_MISMATCH_REASON,
    TARGET_CONTRACT_OK_REASON,
    build_explanation,
    build_signature,
    should_send_alert,
)

# Paths
SCRIPT_DIR = "/Users/knowlet/.openclaw/workspace/shared-projects/intelligence-model"
FUSION_SCRIPT = os.path.join(SCRIPT_DIR, "compute_ngi_fusion.py")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "latest_ngi.json")
ALERT_STATE_FILE = os.path.join(SCRIPT_DIR, "last_alert_state.json")
DB_FILE = os.path.join(SCRIPT_DIR, "ngi_history.sqlite")
UNIFIED_DB_FILE = os.path.join(SCRIPT_DIR, "intelligence_store.sqlite")

# Gap threshold on top of trigger conditions emitted by compute_ngi_fusion.py
ALERT_THRESHOLD = 0.15


def _iso_to_run_token(timestamp_utc):
    if not timestamp_utc:
        return "legacy-monitor-unknown"
    return (
        "legacy-monitor-"
        + str(timestamp_utc).replace(':', '').replace('-', '').replace('+00:00', 'Z').replace('+0000', 'Z')
    )


def _map_public_reason_code(alert_decision, alert_reason):
    if alert_decision == 'would_send':
        return alert_reason
    if alert_reason == TARGET_CONTRACT_MISMATCH_REASON:
        return TARGET_CONTRACT_MISMATCH_REASON
    return TARGET_CONTRACT_OK_REASON


def _build_alert_contract_payload(data, alert_decision, alert_reason, expl=None):
    market_target = data.get('market_target') or {}
    runtime_target_id = market_target.get('market_id') or market_target.get('market_slug')
    runtime_target_name = market_target.get('market_name') or market_target.get('market_question')
    run_token = _iso_to_run_token(data.get('timestamp_utc'))
    public_reason_code = _map_public_reason_code(alert_decision, alert_reason)
    disposition = {
        'should_send': alert_decision == 'would_send',
        'decision': 'would_send' if alert_decision == 'would_send' else 'suppressed',
        'reason_code': public_reason_code,
        'runtime_target_id': runtime_target_id,
        'runtime_target_name': runtime_target_name,
        'alert_target_id': runtime_target_id,
        'target_contract_match': None if not runtime_target_id else True,
        'contract_version': data.get('contract_version') or 'legacy-monitor-contract-v1',
        'e2e_run_id': run_token,
    }
    explain_contract = {
        'disposition': disposition['decision'],
        'reason_code': public_reason_code,
        'runtime_target_id': runtime_target_id,
        'runtime_target_name': runtime_target_name,
        'alert_target_id': runtime_target_id,
        'target_contract_match': disposition['target_contract_match'],
        'contract_version': disposition['contract_version'],
        'e2e_run_id': run_token,
        'internal_runtime_reason_code': alert_reason,
    }
    payload = {
        **data,
        'alert_disposition': disposition,
        'alert_explain_contract': explain_contract,
    }
    if payload.get('P_AI') is None and payload.get('first_principles_probability') is not None:
        payload['P_AI'] = payload.get('first_principles_probability')
    if payload.get('explain') is None and expl is not None:
        payload['explain'] = expl
    return payload


def run_fusion():
    try:
        result = subprocess.run(
            [sys.executable, FUSION_SCRIPT],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=SCRIPT_DIR
        )
        if result.returncode != 0:
            print(f"Fusion script failed: {result.stderr}", file=sys.stderr)
            return None

        lines = result.stdout.strip().split('\n')
        json_lines = []
        in_json = False
        for line in lines:
            if line.strip().startswith('{'):
                in_json = True
            if in_json:
                json_lines.append(line)
            if in_json and line.strip().endswith('}'):
                break
        data = json.loads('\n'.join(json_lines))
        return data
    except Exception as e:
        print(f"Error running fusion script: {e}", file=sys.stderr)
        return None


def ensure_db():
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ngi_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_utc TEXT NOT NULL,
                market_name TEXT,
                market_prob REAL,
                fp_prob REAL,
                ngi REAL,
                ngi_percentage REAL,
                adsb_count INTEGER,
                adsb_peace_score REAL,
                adsb_used INTEGER,
                firehose_events_analyzed INTEGER,
                firehose_peace_score REAL,
                threshold REAL,
                threshold_crossed INTEGER,
                alert_decision TEXT,
                alert_reason TEXT,
                reasons_json TEXT,
                market_misses_json TEXT,
                watch_next_json TEXT,
                raw_json TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _ngi_insert_tuple(data, expl, alert_decision, alert_reason):
    adsb = data.get('adsb') or {}
    firehose = data.get('firehose') or {}
    market_target = data.get('market_target') or {}
    return (
        data.get('timestamp_utc'),
        market_target.get('market_name') or 'unknown_target',
        data.get('market_escalation_probability'),
        data.get('first_principles_escalation_probability'),
        data.get('ngi'),
        data.get('ngi_percentage'),
        adsb.get('count'),
        adsb.get('peace_score'),
        1 if adsb.get('used') else 0,
        firehose.get('events_analyzed'),
        firehose.get('peace_score'),
        ALERT_THRESHOLD,
        1 if (data.get('ngi') is not None and data.get('ngi') > ALERT_THRESHOLD) else 0,
        alert_decision,
        alert_reason,
        json.dumps((expl or {}).get('reasons', []), ensure_ascii=False),
        json.dumps((expl or {}).get('market_misses', []), ensure_ascii=False),
        json.dumps((expl or {}).get('watch_next', []), ensure_ascii=False),
        json.dumps(data, ensure_ascii=False)
    )


def _insert_into_ngi_runs(db_path, data, expl, alert_decision, alert_reason):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO ngi_runs (
                timestamp_utc, market_name, market_prob, fp_prob, ngi, ngi_percentage,
                adsb_count, adsb_peace_score, adsb_used,
                firehose_events_analyzed, firehose_peace_score,
                threshold, threshold_crossed, alert_decision, alert_reason,
                reasons_json, market_misses_json, watch_next_json, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            _ngi_insert_tuple(data, expl, alert_decision, alert_reason)
        )
        conn.commit()
    finally:
        conn.close()


def write_run_to_db(data, expl, alert_decision, alert_reason):
    ensure_db()
    _insert_into_ngi_runs(DB_FILE, data, expl, alert_decision, alert_reason)
    if os.path.exists(UNIFIED_DB_FILE):
        _insert_into_ngi_runs(UNIFIED_DB_FILE, data, expl, alert_decision, alert_reason)


def load_alert_state():
    try:
        with open(ALERT_STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def save_alert_state(state):
    try:
        with open(ALERT_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Failed to write alert state: {e}", file=sys.stderr)


def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Running NGI monitor...")
    data = run_fusion()
    if data is None:
        print("Failed to compute NGI.", file=sys.stderr)
        sys.exit(1)

    ngi = data.get('ngi')
    expl = build_explanation(data) if ngi is not None else None
    gap_triggered = bool(data.get('gap_triggered'))

    if ngi is not None and gap_triggered and ngi > ALERT_THRESHOLD:
        decision = should_send_alert(data, expl, load_alert_state())
        if decision.should_send:
            alert_decision = 'would_send'
            alert_reason = decision.reason
            save_alert_state(build_signature(data, expl))
            write_run_to_db(data, expl, alert_decision, alert_reason)
            print(f"Gap triggered and above threshold; stored as would_send: {decision.reason}")
        else:
            alert_decision = 'suppressed'
            alert_reason = decision.reason
            write_run_to_db(data, expl, alert_decision, alert_reason)
            print(f"Gap triggered but suppressed: {decision.reason}")
    else:
        # Keep last_alert_state aligned with current state/target context even when no alert fires.
        save_alert_state(build_signature(data, expl or {
            "reasons": [], "reason_keys": [], "market_misses": [], "miss_keys": [], "watch_next": [], "watch_keys": []
        }))
        alert_decision = 'below_threshold'
        alert_reason = 'no_actionable_gap'
        write_run_to_db(data, expl, alert_decision, alert_reason)
        print(f"No actionable gap (ngi={ngi}, gap_triggered={gap_triggered}).")

    data = _build_alert_contract_payload(data, alert_decision, alert_reason, expl)
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Result written to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Failed to write output file: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
