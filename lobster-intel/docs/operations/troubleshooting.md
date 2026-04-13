# Troubleshooting

## Common failure classes

### 1. Evidence drift
Symptoms:
- raw source says one thing, summaries say another
- old market framing remains after a target change

Action:
- compare evidence, compiled page, runtime snapshot
- generate drift report
- repair the derived layer, not the source

### 2. Runtime drift
Symptoms:
- state config disagrees with monitor output
- latest runtime artifact disagrees with delivery text

Action:
- inspect runtime snapshot
- inspect target config
- inspect transition log
- regenerate affected runtime artifacts

### 3. Delivery drift
Symptoms:
- PM2 or job says ok, user-facing content is wrong
- internal narration leaks into user messages

Action:
- inspect delivery renderer
- inspect cron output rules
- verify silence behavior

### 4. Freshness or DQ failures
Symptoms:
- stale snapshots
- missing tables
- invalid market or report artifacts

Action:
- verify ingest pipeline
- verify raw evidence path
- verify DQ contract
- avoid declaring recovery before end-to-end verification

## Repair principle

Repair the highest broken derived layer first, but verify against lower layers.
Truth priority remains:
1. evidence
2. runtime
3. compiled knowledge
4. delivery text
