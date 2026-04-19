# Official Statements Tracker

Tracks official newsroom / press release feeds via RSS or Atom-compatible XML.

## Config

Set `OFFICIAL_STATEMENTS_FEEDS_JSON` to a JSON array like:

```json
[
  {"source_id": "whitehouse", "url": "https://www.whitehouse.gov/briefing-room/feed/"},
  {"source_id": "state-dept", "url": "https://www.state.gov/press-releases/feed/"}
]
```

Optional persistence path:

```bash
export OFFICIAL_STATEMENTS_STATE_PATH="$PWD/lobster-intel/data/runtime/sources/official-statements.json"
```

When set, the plugin will load/save feed cursors there and use them as `since_cursor` on the next run.

No delivery logic is embedded.
