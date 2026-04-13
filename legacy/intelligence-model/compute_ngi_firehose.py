#!/usr/bin/env python3
"""
Compute NGI using first-principles probability derived from Firehose events.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
import math

FIREHOSE_EVENTS_PATH = "/Users/knowlet/.openclaw/workspace/shared-projects/firehose-daemon/events.jsonl"

# Market configuration: map market slug/id to a set of Firehose tags that indicate escalation (negative for peace)
# We define a default set for the US-Iran ceasefire market.
MARKET_CONFIG = {
    "us-x-iran-ceasefire-by-april-30": {
        "slug": "us-x-iran-ceasefire-by-april-30",
        "id": "1466016",
        "escalation_tags": {
            "kinetic-isr-ira",   # Israel-Iran kinetic
            "kinetic-redsea",    # Red Sea
            "kinetic-kharg",     # Kharg Island
            "kinetic-ukr-deep",  # Ukraine deep strikes (proxy?)
            # Note: we treat any high-priority kinetic event as escalation for this regional market
        },
        # Weight by priority: high=1.0, medium=0.5, low=0.1
        "priority_weights": {"high": 1.0, "medium": 0.5, "low": 0.1},
        # Mapping from event count to first-principles probability of ceasefire (Yes)
        # We use a simple decreasing function: p = 1 / (1 + count / scale)
        "scale": 10.0,  # tune this
    },
    # Add other markets as needed
}


def parse_iso8601(timestamp_str):
    """Parse ISO8601 string to timezone-aware datetime."""
    # Remove trailing Z and add +00:00 if needed
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str[:-1] + '+00:00'
    return datetime.fromisoformat(timestamp_str)


def load_recent_events(hours=24):
    """Load Firehose events from the last `hours` hours."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    events = []
    if not os.path.exists(FIREHOSE_EVENTS_PATH):
        print(f"Error: Firehose events file not found at {FIREHOSE_EVENTS_PATH}", file=sys.stderr)
        return events
    with open(FIREHOSE_EVENTS_PATH, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                # Parse received_at
                recv_str = event.get('received_at')
                if not recv_str:
                    continue
                recv_time = parse_iso8601(recv_str)
                if recv_time >= cutoff:
                    events.append(event)
            except (json.JSONDecodeError, ValueError) as e:
                # Skip malformed lines
                continue
    return events


def compute_first_principles_probability(events, market_key):
    """Compute first-principles probability of market outcome (Yes) from events."""
    config = MARKET_CONFIG.get(market_key)
    if not config:
        print(f"Warning: No config for market key {market_key}; falling back to default config.", file=sys.stderr)
        # fallback to first available config
        config = next(iter(MARKET_CONFIG.values()))

    escalation_tags = config["escalation_tags"]
    priority_weights = config["priority_weights"]
    scale = config["scale"]

    score = 0.0
    for ev in events:
        tag = ev.get('tag')
        priority = ev.get('priority')
        if tag in escalation_tags and priority in priority_weights:
            score += priority_weights[priority]

    # Convert score to probability: higher score (more escalation) -> lower probability of ceasefire (Yes)
    # Using logistic-like function: p = 1 / (1 + score/scale)
    p_yes = 1.0 / (1.0 + score / scale)
    return p_yes


def fetch_market_probability(market_id):
    """Fetch the current Polymarket probability for a market ID."""
    import requests
    url = f"https://gamma-api.polymarket.com/markets/{market_id}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        outcomes_raw = data.get('outcomes')
        outcome_prices_raw = data.get('outcomePrices')
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
        # Find Yes outcome
        for i, outcome in enumerate(outcomes):
            if isinstance(outcome, str) and outcome.lower() == 'yes':
                try:
                    return float(outcome_prices[i])
                except (ValueError, IndexError):
                    return None
        # Default to first outcome
        try:
            return float(outcome_prices[0])
        except (ValueError, IndexError):
            return None
    except Exception as e:
        print(f"Error fetching market {market_id}: {e}", file=sys.stderr)
        return None


def compute_ngi(fp_probability, pm_probability):
    """Compute Narrative Gap Index."""
    if fp_probability is None or pm_probability is None:
        return None
    return abs(fp_probability - pm_probability)


def main():
    # Allow running without args by using state_config as source of truth.
    market_input = sys.argv[1] if len(sys.argv) >= 2 else None
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24

    # If no market specified, try to read active target from state_config.json
    if not market_input:
        state_path = os.path.join(os.path.dirname(__file__), 'state_config.json')
        try:
            with open(state_path, 'r') as sf:
                state = json.load(sf)
            current_state = state.get('current_state')
            target = state.get('states', {}).get(current_state, {}).get('target')
            if target and target.get('type') == 'polymarket':
                market_input = target.get('market_slug') or target.get('market_id')
                print(f"Info: No market arg provided, using state_config current_state={current_state}, target={market_input}", file=sys.stderr)
            else:
                print("Error: state_config does not provide a polymarket target for the current state.", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            print(f"Error: Unable to load state_config.json: {e}", file=sys.stderr)
            sys.exit(1)

    # Determine if input is slug or id and find matching config
    market_key = None
    market_id = None
    for key, config in MARKET_CONFIG.items():
        if market_input == config["slug"] or market_input == config["id"] or market_input == key:
            market_key = key
            market_id = config["id"]
            break

    # If not found in MARKET_CONFIG, try to interpret market_input as an ID or slug from state_config
    if not market_key:
        # If market_input looks like an integer id, use it directly
        if market_input.isdigit():
            market_id = market_input
            market_key = next(iter(MARKET_CONFIG.keys()))  # fallback to default config for scoring logic
            print(f"Warning: Market not in MARKET_CONFIG; using default scoring config and market_id={market_id}", file=sys.stderr)
        else:
            # Try to find in state_config if available
            try:
                with open(os.path.join(os.path.dirname(__file__), 'state_config.json'), 'r') as sf:
                    state = json.load(sf)
                # search states for matching market_slug
                found = False
                for st_name, st_obj in state.get('states', {}).items():
                    t = st_obj.get('target') or {}
                    if t.get('market_slug') == market_input or t.get('market_id') == market_input:
                        market_id = t.get('market_id')
                        market_key = next(iter(MARKET_CONFIG.keys()))
                        found = True
                        break
                if not found:
                    print(f"Error: Market '{market_input}' not configured and not found in state_config.", file=sys.stderr)
                    sys.exit(1)
                else:
                    print(f"Info: Found market in state_config, using market_id={market_id} with default scoring config.", file=sys.stderr)
            except Exception as e:
                print(f"Error: Market '{market_input}' not configured and state_config not readable: {e}", file=sys.stderr)
                sys.exit(1)

    # Load recent Firehose events
    events = load_recent_events(hours=hours)
    if not events:
        print(f"Warning: No events found in the last {hours}h. Using zero score.", file=sys.stderr)

    # Compute first-principles probability
    fp_prob = compute_first_principles_probability(events, market_key)
    if fp_prob is None:
        print("Error: Could not compute first-principles probability.", file=sys.stderr)
        sys.exit(1)

    # Fetch Polymarket probability
    pm_prob = fetch_market_probability(market_id)
    if pm_prob is None:
        print("Error: Could not fetch Polymarket probability.", file=sys.stderr)
        sys.exit(1)

    # Compute NGI
    ngi = compute_ngi(fp_prob, pm_prob)
    if ngi is None:
        print("Error: Could not compute NGI.", file=sys.stderr)
        sys.exit(1)

    result = {
        "market_slug": MARKET_CONFIG.get(market_key, {}).get("slug") or market_input,
        "market_id": market_id,
        "market_question": None,
        "first_principles_probability": fp_prob,
        "polymarket_yes_probability": pm_prob,
        "ngi": ngi,
        "ngi_percentage": ngi * 100,
        "events_analyzed": len(events),
        "hours_lookback": hours,
    }

    print(json.dumps(result, indent=2))

    # Interpretation
    if ngi < 0.05:
        print("\nInterpretation: Market and data are in alignment (NGI < 5pp).")
    elif ngi < 0.15:
        print("\nInterpretation: Minor gap worth monitoring (5pp ≤ NGI < 15pp).")
    elif ngi < 0.30:
        print("\nInterpretation: Significant gap - consider deeper analysis (15pp ≤ NGI < 30pp).")
    else:
        print("\nInterpretation: Major gap - immediate attention recommended (NGI ≥ 30pp).")


if __name__ == "__main__":
    main()
