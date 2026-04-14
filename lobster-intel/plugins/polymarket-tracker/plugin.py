from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from lobster_ingest.adapters import PolymarketAdapter
from lobster_runtime import load_source_state, save_source_state


def _config(ctx=None) -> list[dict]:
    if ctx and ctx.config.get("markets"):
        return ctx.config["markets"]
    raw = os.environ.get("POLYMARKET_MARKETS_JSON", "[]")
    return json.loads(raw)


def _state_path(ctx=None) -> Path | None:
    if ctx and ctx.config.get("state_path"):
        return Path(ctx.config["state_path"])
    raw = os.environ.get("POLYMARKET_STATE_PATH")
    if raw:
        return Path(raw)
    return None


def ingest(ctx=None) -> dict:
    markets = _config(ctx)
    state_path = _state_path(ctx)
    source_state = load_source_state(state_path) if state_path else None
    configured_markets = []
    for market in markets:
        market = dict(market)
        key = str(market.get("id") or market.get("slug") or market.get("label") or len(configured_markets))
        if source_state and key in source_state.cursors and "since_cursor" not in market:
            market["since_cursor"] = source_state.cursors[key].cursor
        configured_markets.append(market)
    adapter = PolymarketAdapter(markets=configured_markets)
    result = adapter.fetch()
    cursor_state = {
        "schema_version": "v1",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cursors": {
            str(item.metadata.get("market_id") or item.external_id): {
                "source_id": str(item.metadata.get("market_id") or item.external_id),
                "cursor": result.next_cursor,
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                "metadata": {"slug": item.metadata.get("slug")},
            }
            for item in result.items
        },
    }
    if source_state:
        for item in result.items:
            key = str(item.metadata.get("market_id") or item.external_id)
            source_state.set_cursor(key, result.next_cursor, {"slug": item.metadata.get("slug")})
    if state_path and source_state:
        save_source_state(state_path, source_state)
    return {
        "source": "polymarket",
        "new_count": len(result.items),
        "cursor": result.next_cursor,
        "cursor_state": cursor_state,
        "items": [asdict(item) for item in result.items],
        "metadata": result.metadata,
        "state_path": str(state_path) if state_path else None,
    }
