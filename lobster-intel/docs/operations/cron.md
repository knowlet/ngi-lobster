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

## Failure policy

Cron failures should be recorded as runtime artifacts.
Repeated failures should escalate via drift or delivery alerts.

## Anti-patterns

- embedding core business logic directly inside the cron payload
- step-by-step narration in scheduled runs
- multiple jobs duplicating the same truth calculation
- letting freeform assistant text pass through delivery when a task should return only `NO_REPLY` or structured results
