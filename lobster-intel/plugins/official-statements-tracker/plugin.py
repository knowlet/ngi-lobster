from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from lobster_ingest.adapters import RssFeedAdapter


def _feeds(ctx=None) -> list[dict]:
    if ctx and ctx.config.get("feeds"):
        return ctx.config["feeds"]
    raw = os.environ.get("OFFICIAL_STATEMENTS_FEEDS_JSON", "[]")
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
            source_type="official_statement",
            url=feed["url"],
        )
        result = adapter.fetch(feed.get("since_cursor"))
        items.extend(item.__dict__ for item in result.items)
        cursors[feed["source_id"]] = result.next_cursor
        cursor_state["cursors"][feed["source_id"]] = {
            "source_id": feed["source_id"],
            "cursor": result.next_cursor,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "metadata": {"url": feed["url"]},
        }
    return {
        "source": "official_statements",
        "new_count": len(items),
        "items": items,
        "cursors": cursors,
        "cursor_state": cursor_state,
    }
