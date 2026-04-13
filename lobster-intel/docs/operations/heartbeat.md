# Heartbeat Operations

## Purpose

Heartbeat is the recurring operational check loop for Lobster Intel.

It exists to:
- detect stale or broken runtime state
- surface urgent intelligence changes
- avoid useless chatter when nothing changed

## Inputs

Heartbeat may read from:
- runtime snapshots
- DQ status
- freshness status
- alert state
- drift reports
- selected live evidence when needed for verification

## Output rule

Heartbeat must do one of two things only:
1. emit a meaningful alert or status summary
2. emit nothing useful -> `NO_REPLY`

No execution narration.
No tool-step chatter.
No fake progress messages.
No preamble like "checking", "tracking", or "I am monitoring".

## Required checks

Minimum heartbeat checks:
- DQ status
- freshness status
- active runtime state
- current target health
- drift severity
- delivery failures if any

## Alert thresholds

Heartbeat should notify when any of the following are true:
- stale data exceeds defined threshold
- DQ is failing
- runtime drift is severe
- state transition occurred
- alert-worthy target movement occurred
- a delivery path failed

## Silence rule

Heartbeat should stay silent when:
- no meaningful change occurred
- all checks remain within expected bounds
- output would only repeat prior information

Silence means no user-visible filler text, not an explanation of silence.

## Separation of concerns

Heartbeat renders runtime truth.
It must not own the monitoring logic itself.

Monitoring logic belongs in `lobster-runtime`.
Formatting belongs in `lobster-delivery`.
