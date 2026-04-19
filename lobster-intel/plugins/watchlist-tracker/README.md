# Watchlist Tracker

Curated feed tracker for high-signal analysts, journalists, Substack feeds, or other narrow watchlists.

## Config

Set `WATCHLIST_FEEDS_JSON` to a JSON array like:

```json
[
  {"source_id": "analyst-a", "url": "https://example.com/feed.xml", "source_type": "analyst_feed"},
  {"source_id": "reporter-b", "url": "https://example.com/rss"}
]
```

Keep it curated. This is not a generic news firehose.

Optional persistence path:

```bash
export WATCHLIST_STATE_PATH="$PWD/lobster-intel/data/runtime/sources/watchlist.json"
```

When set, the plugin will load/save per-feed cursors there.
