from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone

from lobster_ingest.adapters import RssFeedAdapter


def _feeds(ctx=None) -> list[dict]:
    if ctx and ctx.config.get("feeds"):
        return ctx.config["feeds"]
    raw = os.environ.get("WATCHLIST_FEEDS_JSON", "[]")
    return json.loads(raw)


def ingest(ctx=None) -> dict:
    feeds = _feeds(ctx)
    items = []
    cursors = {}
    cursor_state = {
        "schema_version": "v1",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cursors": {},
    }
    for feed in feeds:
        adapter = RssFeedAdapter(
            source_id=feed["source_id"],
            source_type=feed.get("source_type", "watchlist_signal"),
            url=feed["url"],
        )
        result = adapter.fetch(feed.get("since_cursor"))
        items.extend(asdict(item) for item in result.items)
        cursors[feed["source_id"]] = result.next_cursor
        cursor_state["cursors"][feed["source_id"]] = {
            "source_id": feed["source_id"],
            "cursor": result.next_cursor,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "metadata": {"url": feed["url"], "source_type": feed.get("source_type", "watchlist_signal")},
        }
    return {
        "source": "watchlist",
        "new_count": len(items),
        "items": items,
        "cursors": cursors,
        "cursor_state": cursor_state,
    }
