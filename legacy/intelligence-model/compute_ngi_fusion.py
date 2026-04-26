#!/usr/bin/env python3
"""
Compute NGI using first-principles probability from ADS-B and Firehose events,
with state-based market/proxy target selection.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
import sqlite3
import requests

from state_config import load_state_config, get_current_state, get_state_bundle, get_active_target, get_fallback_target

REPO_ROOT = Path(__file__).resolve().parents[2]
LOBSTER_PACKAGES = Path(
    os.environ.get("LOBSTER_PACKAGES_DIR")
    or (REPO_ROOT / "lobster-intel" / "packages")
).resolve()
for package_dir in (
    LOBSTER_PACKAGES / "lobster-core",
    LOBSTER_PACKAGES / "lobster-runtime",
    LOBSTER_PACKAGES / "lobster-delivery",
    LOBSTER_PACKAGES / "lobster-ingest",
    LOBSTER_PACKAGES / "lobster-plugins",
):
    package_dir_str = str(package_dir)
    if package_dir_str not in sys.path:
        sys.path.insert(0, package_dir_str)

from lobster_runtime import FusionComputationInput, build_fusion_result

# ---------- Configuration ----------
# ADS-B OpenSky bounding box for Iran/Persian Gulf region
ADSB_LAMIN = 24.0   # min latitude
ADSB_LOMIN = 44.0   # min longitude
ADSB_LAMAX = 40.0   # max latitude
ADSB_LOMAX = 64.0   # max longitude
ADSB_URL = f"https://opensky-network.org/api/states/all?lamin={ADSB_LAMIN}&lomin={ADSB_LOMIN}&lamax={ADSB_LAMAX}&lomax={ADSB_LOMAX}"

# Scaling factors for converting raw signal to peace-friendly score (0-1)
# Higher raw value => more tension => lower peace probability
ADSB_SCALE = 15.0   # if aircraft count == ADSB_SCALE, score = 0.5
FIREHOSE_SCALE = 8.0   # if weighted event count per hour == FIREHOSE_SCALE, score = 0.5

# Weights for combining sources (must sum to 1.0)
W_ADSB = 0.4
W_FIREHOSE = 0.6
assert abs(W_ADSB + W_FIREHOSE - 1.0) < 1e-9

# Firehose events file
FIREHOSE_EVENTS_PATH = "/Users/knowlet/.openclaw/workspace/shared-projects/firehose-daemon/events.jsonl"
# Offset file for incremental reading
FIREHOSE_OFFSET_PATH = "/Users/knowlet/.openclaw/workspace/shared-projects/intelligence-model/.firehose_offset"
# Local intelligence DB for proxy extraction
INTELLIGENCE_DB = "/Users/knowlet/.openclaw/workspace/shared-projects/intelligence-model/intelligence_store.sqlite"

# Priority weights for Firehose events
PRIORITY_WEIGHTS = {"high": 1.0, "medium": 0.5, "low": 0.1}

# ---------- End Configuration ----------


def fetch_adsb_count():
    """Fetch current number of aircraft in the region from OpenSky Network."""
    try:
        resp = requests.get(ADSB_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        states = data.get('states')
        if states is None:
            return 0
        return len(states)
    except Exception as e:
        print(f"Warning: ADS-B fetch failed: {e}", file=sys.stderr)
        return None


def adsb_to_peace_score(count, scale=ADSB_SCALE):
    if count is None:
        return None
    return 1.0 / (1.0 + count / scale)


def load_recent_firehose_events(hours=1):
    """Load Firehose events incrementally with string matching."""
    if not os.path.exists(FIREHOSE_EVENTS_PATH):
        print(f"Error: Firehose events file not found at {FIREHOSE_EVENTS_PATH}", file=sys.stderr)
        return []

    last_offset = _load_last_offset()
    file_size = os.path.getsize(FIREHOSE_EVENTS_PATH)
    if last_offset > file_size:
        last_offset = 0

    events_count = {"high": 0, "medium": 0, "low": 0}
    with open(FIREHOSE_EVENTS_PATH, 'r') as f:
        f.seek(last_offset)
        for line in f:
            for p in PRIORITY_WEIGHTS:
                if f'"priority":"{p}"' in line:
                    events_count[p] += 1
                    break
        _save_last_offset(f.tell())

    fake_events = []
    for p, count in events_count.items():
        fake_events.extend([{"priority": p}] * count)
    return fake_events


def firehose_to_peace_score(events, scale=FIREHOSE_SCALE):
    weighted = 0.0
    for ev in events:
        priority = ev.get('priority')
        if priority in PRIORITY_WEIGHTS:
            weighted += PRIORITY_WEIGHTS[priority]
    return 1.0 / (1.0 + weighted / scale)


def _load_last_offset():
    try:
        with open(FIREHOSE_OFFSET_PATH, 'r') as f:
            return int(f.read().strip() or 0)
    except Exception:
        return 0


def _save_last_offset(offset):
    try:
        with open(FIREHOSE_OFFSET_PATH, 'w') as f:
            f.write(str(offset))
    except Exception as e:
        print(f"Warning: could not save offset {offset}: {e}", file=sys.stderr)


def fetch_market_payload(market_id):
    url = f"https://gamma-api.polymarket.com/markets/{market_id}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def extract_yes_probability(payload):
    outcomes_raw = payload.get('outcomes')
    outcome_prices_raw = payload.get('outcomePrices')
    if outcomes_raw is None or outcome_prices_raw is None:
        return None
    try:
        outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
        outcome_prices = json.loads(outcome_prices_raw) if isinstance(outcome_prices_raw, str) else outcome_prices_raw
    except (json.JSONDecodeError, TypeError):
        outcomes = outcomes_raw
        outcome_prices = outcome_prices_raw
    if not isinstance(outcomes, list) or not isinstance(outcome_prices, list):
        return None
    for i, outcome in enumerate(outcomes):
        if isinstance(outcome, str) and outcome.lower() == 'yes':
            try:
                return float(outcome_prices[i])
            except (ValueError, IndexError):
                return None
    try:
        return float(outcome_prices[0])
    except (ValueError, IndexError):
        return None


def clamp01(x):
    return max(0.0, min(1.0, x))


def compute_macro_proxy_probability(target):
    """
    Build escalation probability from local market_snapshots.
    Default: map Crude Oil 24h % change to [0,1].
    """
    symbol = target.get("source_symbol") or "Crude Oil"
    norm = target.get("normalization") or {}
    floor = float(norm.get("change_pct_floor", 0.0))
    ceiling = float(norm.get("change_pct_ceiling", 12.0))
    if ceiling <= floor:
        ceiling = floor + 1.0

    conn = sqlite3.connect(INTELLIGENCE_DB)
    try:
        row = conn.execute(
            """
            SELECT symbol, price, change_pct_24h, snapshot_at_utc
            FROM market_snapshots
            WHERE symbol=?
            ORDER BY snapshot_at_utc DESC
            LIMIT 1
            """,
            (symbol,)
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None, {"error": f"No market_snapshots row for symbol={symbol}"}

    _, price, change_pct_24h, snapshot_at_utc = row
    if change_pct_24h is None:
        return None, {
            "error": f"No change_pct_24h for symbol={symbol}",
            "symbol": symbol,
            "snapshot_at_utc": snapshot_at_utc,
        }

    normalized = (float(change_pct_24h) - floor) / (ceiling - floor)
    escalation_prob = clamp01(normalized)
    return escalation_prob, {
        "symbol": symbol,
        "price": price,
        "change_pct_24h": float(change_pct_24h),
        "snapshot_at_utc": snapshot_at_utc,
        "normalization_floor": floor,
        "normalization_ceiling": ceiling,
    }


def target_to_escalation_probability(target):
    target_type = (target or {}).get("type")

    if target_type == "polymarket":
        market_id = str(target.get("market_id"))
        payload = fetch_market_payload(market_id)
        yes_prob = extract_yes_probability(payload)
        if yes_prob is None:
            return None, payload

        mode = target.get("probability_mode", "yes_is_escalation")
        if mode == "yes_is_peace":
            escalation_prob = 1.0 - yes_prob
        else:
            escalation_prob = yes_prob

        return escalation_prob, {
            "platform": "polymarket",
            "market_id": str(payload.get("id") or market_id),
            "market_slug": payload.get("slug") or target.get("market_slug"),
            "market_question": payload.get("question") or target.get("market_name"),
            "market_yes_probability": yes_prob,
            "market_closed": payload.get("closed"),
            "market_active": payload.get("active"),
            "market_accepting_orders": payload.get("acceptingOrders"),
            "probability_mode": mode,
        }

    if target_type == "macro_proxy":
        escalation_prob, detail = compute_macro_proxy_probability(target)
        if escalation_prob is None:
            return None, detail
        detail.update({
            "platform": "macro_proxy",
            "proxy_key": target.get("proxy_key"),
            "market_question": target.get("market_name"),
            "probability_mode": target.get("probability_mode", "higher_change_is_higher_escalation"),
        })
        return escalation_prob, detail

    return None, {"error": f"Unsupported target type: {target_type}"}


def resolve_market_target(bundle):
    active = get_active_target(bundle)
    fallback = get_fallback_target(bundle)

    if not active:
        return None, None, "no_active_target"

    prob, detail = target_to_escalation_probability(active)
    if prob is not None:
        return active, detail, "active_target"

    if fallback:
        fb_prob, fb_detail = target_to_escalation_probability(fallback)
        if fb_prob is not None:
            return fallback, fb_detail, "fallback_target"
        return None, {"active_error": detail, "fallback_error": fb_detail}, "both_failed"

    return None, {"active_error": detail}, "active_failed"


def main():
    # 1) First-principles signals
    adsb_count = fetch_adsb_count()
    adsb_score = adsb_to_peace_score(adsb_count) if adsb_count is not None else None
    events = load_recent_firehose_events(hours=1)
    firehose_score = firehose_to_peace_score(events)

    if adsb_score is None:
        fp_peace = firehose_score
        used_adsb = False
    else:
        fp_peace = W_ADSB * adsb_score + W_FIREHOSE * firehose_score
        used_adsb = True

    fp_escalation = 1.0 - fp_peace

    # 2) State and target selection
    config = load_state_config()
    state = get_current_state(config)
    bundle = get_state_bundle(config, state)
    target, target_detail, target_mode = resolve_market_target(bundle)

    market_escalation = None
    market_name = None
    market_slug = None
    market_id = None

    if target:
        market_escalation, target_detail = target_to_escalation_probability(target)
        market_name = target.get("market_name") or (target_detail or {}).get("market_question")
        market_slug = target.get("market_slug")
        market_id = target.get("market_id")

    result = build_fusion_result(
        FusionComputationInput(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            state=state,
            logic_summary=bundle.get("logic_summary"),
            target_resolution_mode=target_mode,
            target={
                "type": (target or {}).get("type"),
                "market_id": market_id,
                "market_slug": market_slug,
                "market_name": market_name,
            },
            target_detail=target_detail,
            adsb_count=adsb_count,
            adsb_peace_score=adsb_score,
            adsb_used=used_adsb,
            firehose_events_analyzed=len(events),
            firehose_peace_score=firehose_score,
            adsb_weight=W_ADSB,
            firehose_weight=W_FIREHOSE,
            first_principles_probability=fp_peace,
            first_principles_escalation_probability=fp_escalation,
            market_escalation_probability=market_escalation,
        )
    ).data
    print(json.dumps(result, indent=2))

    ngi = result.get("ngi")
    if ngi is not None:
        if not result.get("gap_triggered"):
            print("\nInterpretation: no actionable gap (either FP escalation not high enough, or market/proxy already reflecting risk).")
        elif ngi < 0.15:
            print("\nInterpretation: small underpricing gap.")
        elif ngi < 0.30:
            print("\nInterpretation: significant underpricing gap.")
        else:
            print("\nInterpretation: major underpricing gap.")


if __name__ == "__main__":
    main()
