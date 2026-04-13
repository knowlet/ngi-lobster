from __future__ import annotations

import json
import os

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
    for feed in feeds:
        adapter = RssFeedAdapter(
            source_id=feed["source_id"],
            source_type=feed.get("source_type", "watchlist_signal"),
            url=feed["url"],
        )
        result = adapter.fetch(feed.get("since_cursor"))
        items.extend(item.__dict__ for item in result.items)
        cursors[feed["source_id"]] = result.next_cursor
    return {
        "source": "watchlist",
        "new_count": len(items),
        "items": items,
        "cursors": cursors,
    }
