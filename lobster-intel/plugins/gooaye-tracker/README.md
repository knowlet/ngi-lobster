# Gooaye Tracker Plugin

## Purpose

Track public Telegram channel updates from `@Gooaye` and emit structured artifacts.

## Planned outputs

- raw evidence record for each detected post
- OCR text when media contains readable text
- compiled short summary for human review
- delivery notification when new posts appear

## Current contract

- every new post is written to `lobster-intel/data/evidence/gooaye/<post_id>.json`
- every new post gets a compiled markdown file under `lobster-intel/data/compiled/gooaye/<post_id>.md`
- runtime state is written to `lobster-intel/data/runtime/gooaye/latest.json`
- plugin boundary is **ingest only**; delivery stays downstream
- posts with image URLs are marked with:
  - `needs_image_analysis: true`
  - `analysis_status: pending`
- posts with linked previews are marked with:
  - `needs_link_extraction: true`
  - `link_extraction_status: pending`
- runtime state also exposes `image_analysis_queue` so cron / delivery layers can explicitly finish OCR or image understanding before final human alerting
- runtime state also exposes `linked_content_queue` so transcript / article extraction can happen downstream without hiding this gap
- `lobster-intel/scripts/process_linked_content_queue.py` consumes that queue and writes auditable evidence, compiled markdown, and runtime receipt artifacts under `lobster-intel/data/`

## Notes

This plugin is the first reference plugin for Lobster Intel.
It should become the template for future channel, market, and report plugins.
