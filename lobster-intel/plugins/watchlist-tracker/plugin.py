from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from lobster_ingest.adapters import RssFeedAdapter
from lobster_runtime import load_source_state, save_source_state


def _feeds(ctx=None) -> list[dict]:
    if ctx and ctx.config.get("feeds"):
        return ctx.config["feeds"]
    raw = os.environ.get("WATCHLIST_FEEDS_JSON", "[]")
    return json.loads(raw)


def _state_path(ctx=None) -> Path | None:
    if ctx and ctx.config.get("state_path"):
        return Path(ctx.config["state_path"])
    raw = os.environ.get("WATCHLIST_STATE_PATH")
    if raw:
        return Path(raw)
    return None


def ingest(ctx=None) -> dict:
    feeds = _feeds(ctx)
    state_path = _state_path(ctx)
    source_state = load_source_state(state_path) if state_path else None
    items = []
    cursors = {}
    cursor_state = {
        "schema_version": "v1",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cursors": {},
    }
    for feed in feeds:
        since_cursor = feed.get("since_cursor")
        if since_cursor is None and source_state and feed["source_id"] in source_state.cursors:
            since_cursor = source_state.cursors[feed["source_id"]].cursor
        adapter = RssFeedAdapter(
            source_id=feed["source_id"],
            source_type=feed.get("source_type", "watchlist_signal"),
            url=feed["url"],
        )
        result = adapter.fetch(since_cursor)
        items.extend(asdict(item) for item in result.items)
        cursors[feed["source_id"]] = result.next_cursor
        cursor_state["cursors"][feed["source_id"]] = {
            "source_id": feed["source_id"],
            "cursor": result.next_cursor,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "metadata": {"url": feed["url"], "source_type": feed.get("source_type", "watchlist_signal"), "since_cursor": since_cursor},
        }
        if source_state:
            source_state.set_cursor(feed["source_id"], result.next_cursor, {"url": feed["url"], "source_type": feed.get("source_type", "watchlist_signal")})
    if state_path and source_state:
        save_source_state(state_path, source_state)
    return {
        "source": "watchlist",
        "new_count": len(items),
        "items": items,
        "cursors": cursors,
        "cursor_state": cursor_state,
        "state_path": str(state_path) if state_path else None,
    }
