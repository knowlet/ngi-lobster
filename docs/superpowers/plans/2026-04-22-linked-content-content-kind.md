# Linked-Content Content-Kind Plan

> **For agentic workers:** Keep this change scoped to Gooaye runtime queue shaping, linked-content artifact writing, focused tests, and short operator docs. Do not move extraction decisions into delivery code.

**Goal:** Preserve linked-content intent as runtime truth by tagging queue items and replayable artifacts with whether the follow-up is an `article` or a `video_transcript`.

**Architecture:** Infer a minimal `content_kind` from the Gooaye preview URL when the runtime queue is built, then carry that same field through linked-content evidence and compiled markdown so downstream workers and operators can audit what kind of extractor path the runtime expected before richer transcript/article support lands.

**Tech Stack:** Python 3.11, stdlib `urllib.parse`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-22.

---

### Task 1: Prove Queue Intent Is Preserved

**Files:**
- Modify: `lobster-intel/tests/test_linked_content_platform.py`

- [x] Add a focused test that Gooaye runtime queue entries distinguish `article` vs `video_transcript`.
- [x] Add a focused test that linked-content evidence and compiled markdown preserve `content_kind`.

### Task 2: Keep Content Kind In Runtime Truth

**Files:**
- Modify: `lobster-intel/packages/lobster-ingest/lobster_ingest/gooaye_pipeline.py`
- Modify: `lobster-intel/packages/lobster-ingest/lobster_ingest/linked_content.py`

- [x] Infer `content_kind` from preview host when building `linked_content_queue`.
- [x] Persist `content_kind` in linked-content evidence artifacts and compiled markdown.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `README.md`
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/plugins/gooaye-tracker/README.md`

- [x] Document that linked-content runtime artifacts now distinguish article vs video-transcript follow-up intent.
