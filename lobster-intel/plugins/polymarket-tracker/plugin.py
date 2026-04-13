from __future__ import annotations

import json
import os

from lobster_ingest.adapters import PolymarketAdapter


def _config(ctx=None) -> list[dict]:
    if ctx and ctx.config.get("markets"):
        return ctx.config["markets"]
    raw = os.environ.get("POLYMARKET_MARKETS_JSON", "[]")
    return json.loads(raw)


def ingest(ctx=None) -> dict:
    markets = _config(ctx)
    adapter = PolymarketAdapter(markets=markets)
    result = adapter.fetch()
    return {
        "source": "polymarket",
        "new_count": len(result.items),
        "cursor": result.next_cursor,
        "items": [item.__dict__ for item in result.items],
        "metadata": result.metadata,
    }
