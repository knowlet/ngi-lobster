from __future__ import annotations

import json
import os
from datetime import datetime, timezone

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
    return {
        "source": "polymarket",
        "new_count": len(result.items),
        "cursor": result.next_cursor,
        "cursor_state": cursor_state,
        "items": [item.__dict__ for item in result.items],
        "metadata": result.metadata,
    }
