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

No delivery logic is embedded.
