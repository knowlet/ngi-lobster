# Reporting Operations

## Purpose

Reports turn runtime and compiled knowledge into scheduled human-facing summaries.

## Report types

- morning report
- evening report
- incident report
- ad hoc analysis report

## Inputs

Reports should combine:
- runtime snapshots
- compiled knowledge
- cited evidence where needed
- alert history

## Rules

- reports summarize, they do not redefine runtime truth
- every material claim should remain traceable
- repeated boilerplate should be minimized
- if nothing matters, the report should say little

## Recommended pipeline

1. gather runtime state
2. gather compiled summaries
3. pull supporting evidence only where needed
4. render concise narrative
5. deliver through the delivery layer

## Output quality

A report should answer:
- what changed?
- why does it matter?
- what evidence supports it?
- what should be watched next?
