# Cron Operations

## Purpose

Cron schedules recurring or delayed operations for Lobster Intel.

## Use cases

- recurring channel tracking
- heartbeat execution
- recurring reports
- one-shot reminders
- isolated monitoring jobs

## Rules

- cron schedules execution, not truth
- job logic should live in packages or plugins
- recurring jobs should prefer stable entrypoints over ad hoc shell glue
- noisy jobs must return `NO_REPLY` when there is no user-visible change
- scheduled tasks must never emit execution narration, progress chatter, or setup commentary

## Job design

Each cron-backed task should define:
- schedule
- entrypoint
- required capabilities
- output behavior
- failure behavior
- delivery target if any

## Recommended contract

A cron task should be able to answer:
- what does it check?
- what artifact does it produce?
- when does it alert?
- when does it stay silent?
- where is its state stored?

## Installed thesis workflow entrypoint

The current stable cron entrypoint for the install surface is:

```bash
node scripts/run_installed_thesis_workflow.js --thesis-id regional-escalation
```

This entrypoint:

- runs the bundled installed-workflow orchestration instead of duplicating truth logic in cron
- reuses bundled thesis defaults from `lobster-intel/examples/thesis-profiles/`
- reuses bundled source-pack configs from `lobster-intel/examples/source-packs/`
- reuses source cursor state under `lobster-intel/data/runtime/sources/`
- prints structured JSON on success and a concrete stderr failure on invalid input

Example outside-install cron recipe:

```cron
*/15 * * * * cd /path/to/ngi-lobster && /usr/bin/env node scripts/run_installed_thesis_workflow.js --thesis-id regional-escalation >> lobster-intel/data/runtime/regional-escalation-cron.log 2>&1
```

## Failure policy

Cron failures should be recorded as runtime artifacts.
Repeated failures should escalate via drift or delivery alerts.

## Anti-patterns

- embedding core business logic directly inside the cron payload
- step-by-step narration in scheduled runs
- multiple jobs duplicating the same truth calculation
- letting freeform assistant text pass through delivery when a task should return only `NO_REPLY` or structured results
