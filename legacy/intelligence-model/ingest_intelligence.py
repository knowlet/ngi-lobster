#!/usr/bin/env python3
import json
import os
import sqlite3
import subprocess
import sys
from collections import deque
from datetime import datetime, timezone

import requests
from state_config import load_state_config, get_current_state, get_state_bundle, get_active_target, get_fallback_target

WORKSPACE_DIR = "/Users/knowlet/.openclaw/workspace"
PROJECT_DIR = os.path.join(WORKSPACE_DIR, "shared-projects", "intelligence-model")
DB_FILE = os.environ.get("INTELLIGENCE_DB_FILE") or os.path.join(PROJECT_DIR, "intelligence_store.sqlite")
SCHEMA_FILE = os.path.join(PROJECT_DIR, "intelligence_schema.sql")
HEARTBEAT_STATE = os.path.join(WORKSPACE_DIR, "memory", "heartbeat-state.json")
MORNING_STATE = os.path.join(WORKSPACE_DIR, "shared-projects", "morning-report", "STATE.yaml")
EVENING_STATE = os.path.join(WORKSPACE_DIR, "shared-projects", "evening-report", "STATE.yaml")
FIREHOSE_EVENTS = os.path.join(WORKSPACE_DIR, "shared-projects", "firehose-daemon", "events.jsonl")
SCRIPTS_DIR = os.path.join(WORKSPACE_DIR, "scripts")
FINANCE_FETCHER = os.path.join(WORKSPACE_DIR, "tools", "finance_fetcher", "fetch_finance.py")

POLYMARKET_BASE = "https://gamma-api.polymarket.com"


def get_polymarket_targets_from_state():
    """Select polymarket targets from current state config (active + fallback)."""
    config = load_state_config()
    state = get_current_state(config)
    bundle = get_state_bundle(config, state)

    targets = []
    for candidate in (get_active_target(bundle), get_fallback_target(bundle)):
        if not candidate or candidate.get("type") != "polymarket":
            continue
        targets.append(
            {
                "topic_slug": candidate.get("topic_slug") or "us_iran_ceasefire",
                "market_id": str(candidate.get("market_id")),
                "market_slug": candidate.get("market_slug"),
                "market_name": candidate.get("market_name"),
            }
        )
    return targets


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def ensure_schema(conn):
    raw = read_text(SCHEMA_FILE)
    if not raw:
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")
    conn.executescript(raw)
    conn.commit()


def parse_top_level_yaml_scalars(path):
    raw = read_text(path)
    if not raw:
        return {}
    out = {}
    for line in raw.splitlines():
        if not line or line.startswith(" ") or line.startswith("\t") or line.strip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip().strip("'").strip('"')
    return out


def topic_id(cur, slug):
    row = cur.execute("SELECT id FROM topics WHERE slug=?", (slug,)).fetchone()
    return row[0] if row else None


def source_id(cur, name):
    row = cur.execute("SELECT id FROM sources WHERE source_name=?", (name,)).fetchone()
    return row[0] if row else None


def normalize_iso(dt_str):
    if not dt_str:
        return None
    return dt_str.replace("Z", "+00:00") if dt_str.endswith("Z") else dt_str


def event_topic_slug(event):
    tag = (event.get("tag") or "").lower()
    title = (event.get("title") or "").lower()
    snippet = (event.get("snippet") or "").lower()
    blob = f"{tag} {title} {snippet}"
    if "iran" in blob or "hormuz" in blob or "tehran" in blob:
        return "iran_conflict"
    if "nvidia" in blob or "openai" in blob or "anthropic" in blob or "google" in blob or "apple" in blob:
        return "ai_bigtech"
    return None


def upsert_report_run(cur, report_kind, state_path):
    doc = parse_top_level_yaml_scalars(state_path)
    if not doc:
        return
    run_date = doc.get("run_date")
    workflow_status = doc.get("status")
    updated_at = doc.get("updated_at") or datetime.now(timezone.utc).isoformat()
    delivered = 1 if workflow_status == "completed" or (doc.get("delivery") and "delivered" in str(doc.get("delivery"))) else 0
    summary = f"status={workflow_status}; last_error={doc.get('last_error')}"
    
    cur.execute(
        """
        INSERT INTO report_runs (
            report_kind, run_date, workflow_status, source_path, headline,
            summary_text, artifact_text, delivered, delivered_to,
            created_at_utc, updated_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(report_kind, run_date) DO UPDATE SET
            workflow_status=excluded.workflow_status,
            source_path=excluded.source_path,
            headline=excluded.headline,
            summary_text=excluded.summary_text,
            delivered=excluded.delivered,
            delivered_to=excluded.delivered_to,
            updated_at_utc=excluded.updated_at_utc
        """,
        (
            report_kind,
            run_date,
            workflow_status,
            state_path,
            f"{report_kind} report {run_date}",
            summary,
            None,
            delivered,
            None,
            updated_at,
            updated_at,
        ),
    )
    
    # Write report_data_links for the current run
    report_run_id = cur.execute("SELECT id FROM report_runs WHERE report_kind=? AND run_date=?", (report_kind, run_date)).fetchone()[0]
    
    # Link to topics involved in this report (best effort based on state or report kind)
    links = []
    if report_kind == "morning":
        # Morning report usually covers major topics
        for slug in ["us_iran_ceasefire", "iran_conflict", "crude_oil_end_march", "ai_bigtech"]:
            tid = topic_id(cur, slug)
            if tid:
                links.append((report_run_id, tid, "topics", tid, "Standard morning coverage"))
    
    for link in links:
        cur.execute(
            """
            INSERT INTO report_data_links (report_run_id, topic_id, data_table, data_row_id, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            link
        )


def ingest_openalice_status(cur):
    raw = read_text(HEARTBEAT_STATE)
    if not raw:
        return
    try:
        payload = json.loads(raw)
    except Exception:
        return
    obs = ((payload.get("observations") or {}).get("openAlice") or {})
    if not obs:
        return
    cur.execute(
        """
        INSERT INTO first_principles_snapshots (
            topic_id, source_id, signal_type, metric_name, metric_value, metric_unit,
            score, snapshot_at_utc, collected_at_utc, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            topic_id(cur, "openalice_status"),
            source_id(cur, "openalice"),
            "service_health",
            "openalice_online",
            1 if obs.get("status") == "online" else 0,
            "boolean",
            1.0 if obs.get("status") == "online" else 0.0,
            obs.get("lastCheckedAt") or datetime.now(timezone.utc).isoformat(),
            datetime.now(timezone.utc).isoformat(),
            json.dumps(obs, ensure_ascii=False),
        ),
    )


def fetch_polymarket_market(market_id):
    url = f"{POLYMARKET_BASE}/markets/{market_id}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def ingest_polymarket(cur):
    sid = source_id(cur, "polymarket")
    now = datetime.now(timezone.utc).isoformat()
    targets = get_polymarket_targets_from_state()
    for market in targets:
        try:
            payload = fetch_polymarket_market(market["market_id"])
        except Exception as e:
            print(f"polymarket fetch failed for {market['market_id']}: {e}")
            continue

        outcomes_raw = payload.get("outcomes")
        prices_raw = payload.get("outcomePrices")
        try:
            outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
            prices = json.loads(prices_raw) if isinstance(prices_raw, str) else prices_raw
        except Exception:
            outcomes, prices = outcomes_raw, prices_raw
        yes_prob = None
        no_prob = None
        if isinstance(outcomes, list) and isinstance(prices, list):
            for i, outcome in enumerate(outcomes):
                label = str(outcome).lower()
                try:
                    price = float(prices[i])
                except Exception:
                    continue
                if label == "yes":
                    yes_prob = price
                elif label == "no":
                    no_prob = price
            if yes_prob is None and prices:
                try:
                    yes_prob = float(prices[0])
                except Exception:
                    pass
            if no_prob is None and yes_prob is not None:
                no_prob = max(0.0, 1.0 - yes_prob)

        cur.execute(
            """
            INSERT INTO prediction_market_snapshots (
                topic_id, source_id, platform, market_id, market_slug, market_name,
                contract_deadline_utc, yes_probability, no_probability, spread_pct,
                volume_24h, open_interest, change_pp_24h, snapshot_at_utc, collected_at_utc, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic_id(cur, market["topic_slug"]),
                sid,
                "polymarket",
                str(payload.get("id") or market["market_id"]),
                payload.get("slug"),
                payload.get("question") or market["market_name"],
                normalize_iso(payload.get("endDate") or payload.get("end_date_iso")),
                yes_prob,
                no_prob,
                None,
                payload.get("oneDayVolume") or payload.get("volume24hr") or payload.get("volume24h"),
                payload.get("liquidity") or payload.get("openInterest") or payload.get("open_interest"),
                payload.get("oneDayPriceChange") or payload.get("change24h"),
                now,
                now,
                json.dumps(payload, ensure_ascii=False),
            ),
        )


def ingest_firehose(cur, limit=300):
    if not os.path.exists(FIREHOSE_EVENTS):
        return
    sid = source_id(cur, "firehose")
    now = datetime.now(timezone.utc).isoformat()
    with open(FIREHOSE_EVENTS, "r", encoding="utf-8", errors="ignore") as f:
        tail = deque(f, maxlen=limit)
    for line in tail:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except Exception:
            continue
        received_at = normalize_iso(event.get("received_at"))
        url = event.get("url")
        title = event.get("title")
        tag = event.get("tag")
        exists = cur.execute(
            "SELECT 1 FROM firehose_events WHERE received_at_utc=? AND IFNULL(url,'')=IFNULL(?, '') AND IFNULL(title,'')=IFNULL(?, '') LIMIT 1",
            (received_at, url, title),
        ).fetchone()
        if exists:
            continue
        slug = event_topic_slug(event)
        cur.execute(
            """
            INSERT INTO firehose_events (
                topic_id, source_id, received_at_utc, publish_time_utc, tag, priority,
                title, url, snippet, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic_id(cur, slug) if slug else None,
                sid,
                received_at or now,
                normalize_iso(event.get("publish_time")),
                tag,
                event.get("priority"),
                title,
                url,
                event.get("snippet"),
                json.dumps(event, ensure_ascii=False),
            ),
        )

def ingest_market_data(cur):
    sid = source_id(cur, "finance_fetcher")
    if not sid:
        cur.execute("INSERT INTO sources (source_type, source_name, trust_level) VALUES ('agent', 'finance_fetcher', 'high')")
        sid = source_id(cur, "finance_fetcher")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Direct Ingestion of some key assets via a simple public API to ensure "market_snapshots" is populated
    assets = [
        {"symbol": "BTC/USD", "url": "https://api.coinbase.com/v2/prices/BTC-USD/spot", "topic": "ai_bigtech", "type": "crypto"}, 
        {"symbol": "Crude Oil", "url": "https://query1.finance.yahoo.com/v8/finance/chart/CL=F?interval=1m&range=1d", "topic": "crude_oil_end_march", "type": "futures"},
        {"symbol": "TWSE", "url": "https://query1.finance.yahoo.com/v8/finance/chart/^TWII?interval=1m&range=1d", "topic": "taiwan_market", "type": "index"},
        {"symbol": "2330.TW", "url": "https://query1.finance.yahoo.com/v8/finance/chart/2330.TW?interval=1m&range=1d", "topic": "taiwan_market", "type": "equity"},
    ]
    
    for asset in assets:
        # Avoid fetching if we are running the smoke test to have controlled state
        if os.environ.get("SMOKE_TEST") == "1":
            continue
        try:
            # Ensure topic exists
            if asset["topic"]:
                tid = topic_id(cur, asset["topic"])
                if not tid:
                    cur.execute("INSERT INTO topics (slug, name, category) VALUES (?, ?, ?)", 
                                (asset["topic"], asset["topic"].replace("_", " ").title(), "market"))
                    tid = topic_id(cur, asset["topic"])
            else:
                tid = None

            # Skip real fetch if we are in environment where it might fail or if we want to force DQ check failure
            # In a real environment, this fetches from Yahoo/Coinbase
            resp = requests.get(asset["url"], timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()
                price = None
                volume = None
                change_pct = None
                
                if "coinbase" in asset["url"]:
                    price = float(data["data"]["amount"])
                elif "yahoo" in asset["url"]:
                    meta = data["chart"]["result"][0]["meta"]
                    price = meta.get("regularMarketPrice")
                    previous_close = meta.get("previousClose")
                    if price and previous_close:
                        change_pct = ((price - previous_close) / previous_close) * 100
                    
                    # Try to get volume from indicators if available
                    try:
                        volumes = data["chart"]["result"][0]["indicators"]["quote"][0].get("volume", [])
                        if volumes:
                            volume = next((v for v in reversed(volumes) if v is not None), None)
                    except:
                        pass
                
                if price:
                    cur.execute(
                        """
                        INSERT INTO market_snapshots (
                            topic_id, source_id, symbol, market_type, price, volume, change_pct_24h, snapshot_at_utc, collected_at_utc, raw_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            tid,
                            sid,
                            asset["symbol"],
                            asset["type"],
                            price,
                            volume,
                            change_pct,
                            now,
                            now,
                            json.dumps(data, ensure_ascii=False)
                        )
                    )
        except Exception as e:
            print(f"Direct asset fetch failed for {asset['symbol']}: {e}")

def validate_twse_data(cur):
    """
    DQ guardrail for TWSE data.
    Required symbols: TWSE, 2330.TW
    Required fields: price (not null), volume (not null/0 unless explicitly handled)
    """
    now_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    required_symbols = ["TWSE", "2330.TW"]
    missing = []
    bad_fields = []

    for sym in required_symbols:
        # Check if we have a snapshot for today
        row = cur.execute(
            "SELECT price, volume, snapshot_at_utc FROM market_snapshots WHERE symbol = ? AND date(snapshot_at_utc) = ? ORDER BY snapshot_at_utc DESC LIMIT 1",
            (sym, now_date)
        ).fetchone()

        if not row:
            missing.append(sym)
            continue

        price, volume, snapshot_at = row
        if price is None:
            bad_fields.append(f"{sym}: price is null")
        
        # volume 0 is often a sign of bad data/closed market when it shouldn't be, 
        # but the requirement is "not missing". If the source really has no volume,
        # it should be null, but we don't allow "silent 0" if it's meant to be missing.
        if volume is None:
            bad_fields.append(f"{sym}: volume is null")

    if missing or bad_fields:
        error_msg = f"DQ_FAIL: Taiwan Stock Data Incomplete.\nMissing symbols: {missing}\nBad fields: {bad_fields}"
        print(error_msg, file=sys.stderr)
        
        # Write to STATE.yaml for twse-close-report or heartbeat-state
        dq_state = {
            "dq_status": "fail",
            "last_dq_error": error_msg.replace("\n", " | "),
            "last_dq_check": datetime.now(timezone.utc).isoformat()
        }
        state_path = os.path.join(WORKSPACE_DIR, "shared-projects", "twse-close-report", "STATE.yaml")
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                for k, v in dq_state.items():
                    f.write(f"{k}: \"{v}\"\n")
        except Exception as e:
            print(f"Failed to write DQ state: {e}", file=sys.stderr)

        sys.exit(1)
    
    # Success state
    state_path = os.path.join(WORKSPACE_DIR, "shared-projects", "twse-close-report", "STATE.yaml")
    try:
        with open(state_path, "w", encoding="utf-8") as f:
            f.write(f"dq_status: \"pass\"\n")
            f.write(f"last_dq_check: \"{datetime.now(timezone.utc).isoformat()}\"\n")
    except Exception:
        pass
    print("DQ_PASS: TWSE data validated.")

def main():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    try:
        ensure_schema(conn)
        cur = conn.cursor()
        upsert_report_run(cur, "morning", MORNING_STATE)
        upsert_report_run(cur, "evening", EVENING_STATE)
        ingest_openalice_status(cur)
        ingest_polymarket(cur)
        ingest_firehose(cur)
        ingest_market_data(cur)
        conn.commit()
        
        # Quality check after ingestion
        validate_twse_data(cur)
        
    finally:
        conn.close()
        print("ingestion complete")


if __name__ == "__main__":
    main()
