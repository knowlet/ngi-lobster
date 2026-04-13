# Polymarket Tracker

Silent ingest plugin for prediction market snapshots.

## Config

Pass `POLYMARKET_MARKETS_JSON` as a JSON array, for example:

```json
[
  {"slug": "trump-announces-end-of-military-operations-against-iran-by-june-30th"},
  {"id": "1517836"}
]
```

The plugin returns normalized market snapshot evidence. No delivery logic is included.
