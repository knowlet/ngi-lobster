# Product Cut v0

## Product principle

NGI Lobster must be:

- **usable by default**
- **extensible by design**

## Default workflow (must work after install)

After plugin install, the default system path should be:

```text
scheduled ingest -> normalized evidence -> local artifact store -> readable markdown digest
```

### Required default behavior

1. plugin runs on a declared schedule
2. source data is normalized into evidence artifacts
3. evidence is written to local storage
4. a simple markdown digest is generated automatically
5. no chat delivery is required for the workflow to be considered usable

### Success condition

A fresh install should let a user see:

- evidence files being created
- runtime state being updated
- a readable digest being produced

without needing custom fusion logic, custom thresholds, or custom delivery setup.

## Extension seam (must stay out of core v0)

These stay outside the default product cut:

1. **Fusion / synthesis**
   - cross-source reasoning
   - LLM-based signal fusion
   - advanced NGI filtering

2. **State / alerts**
   - custom thresholds
   - anomaly definitions
   - black swan logic

3. **Active delivery**
   - Telegram / Discord / chat push
   - channel formatting
   - notification policy

## Immediate implementation implication

Next build target is not “more features”.
It is one complete default path:

```text
gooaye-tracker -> evidence -> compiled markdown digest -> runtime snapshot
```

Once this path is solid, other trackers should plug into the same artifact flow.

