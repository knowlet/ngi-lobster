# Linked-Content Extraction Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `linked_content_queue` into a replayable extraction workflow that writes auditable artifacts for articles, previews, and transcripts without letting source plugins or delivery code silently own downstream truth.

**Architecture:** Keep the source tracker responsible only for emitting queue intents in runtime artifacts. A separate linked-content worker should read queue entries, fetch or extract content through an injectable adapter, and write evidence, compiled, and runtime receipt artifacts under `lobster-intel/data/` so the extraction path is replayable and does not mutate the originating source artifact in place.

**Tech Stack:** Python 3.11, stdlib `json`/`pathlib`, existing Gooaye ingest pipeline, pytest, CLI script under `lobster-intel/scripts/`

**Status:** Implemented on 2026-04-20. Verified again on 2026-04-21 with `./.venv/bin/python -m pytest lobster-intel/tests/test_linked_content_platform.py -q` (`7 passed`). Post-review hardening on 2026-04-20 tightened extraction to `http`/`https`, capped response size before decode, removed `script`/`style` noise from HTML text output, and parallelized queue fetches while preserving artifact write order.

---

### Task 1: Lock The Queue-Processing Contract In Tests

**Files:**
- Create: `lobster-intel/tests/test_linked_content_platform.py`
- Test: `lobster-intel/tests/test_linked_content_platform.py`

- [x] **Step 1: Add a failing unit test for processing one queued linked item**

```python
def test_process_linked_content_queue_writes_artifacts(tmp_path: Path):
    runtime_payload = {
        "run_id": "gooaye-20260420T000000Z",
        "linked_content_queue": [
            {
                "post_id": "101",
                "url": "https://t.me/gooaye/101",
                "linked_url": "https://example.com/story",
                "site_name": "Example News",
                "title": "Example Story",
            }
        ],
    }

    result = process_linked_content_queue(
        workspace_dir=tmp_path,
        thesis_id="gooaye",
        runtime_payload=runtime_payload,
        extractor=lambda url: {"url": url, "title": "Example Story", "content": "Full article body"},
        now_utc="2026-04-20T00:00:00+00:00",
    )

    assert result["processed_count"] == 1
    assert (tmp_path / result["evidence_paths"][0]).exists()
    assert (tmp_path / result["receipt_path"]).exists()
```

- [x] **Step 2: Add a failing test that empty queues remain explicit**

```python
def test_process_linked_content_queue_records_empty_receipt(tmp_path: Path):
    result = process_linked_content_queue(
        workspace_dir=tmp_path,
        thesis_id="gooaye",
        runtime_payload={"run_id": "gooaye-20260420T000000Z", "linked_content_queue": []},
        extractor=lambda url: {},
        now_utc="2026-04-20T00:00:00+00:00",
    )

    assert result["processed_count"] == 0
    assert result["status"] == "no_items"
```

- [x] **Step 3: Run focused linked-content tests and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_linked_content_platform.py -q`
Expected: FAIL because no linked-content processing module exists yet

### Task 2: Implement Replayable Linked-Content Processing

**Files:**
- Create: `lobster-intel/packages/lobster-ingest/lobster_ingest/linked_content.py`
- Modify: `lobster-intel/packages/lobster-ingest/lobster_ingest/__init__.py`
- Create: `lobster-intel/scripts/process_linked_content_queue.py`
- Test: `lobster-intel/tests/test_linked_content_platform.py`

- [x] **Step 1: Implement the queue processor with injectable extraction**

```python
def process_linked_content_queue(
    *,
    workspace_dir: str | Path,
    thesis_id: str,
    runtime_payload: dict[str, Any],
    extractor: Callable[[str], dict[str, Any]],
    now_utc: str | None = None,
) -> dict[str, Any]:
    queue = list(runtime_payload.get("linked_content_queue") or [])
    if not queue:
        return _write_empty_receipt(workspace_dir, thesis_id, runtime_payload, now_utc=now_utc)
```

- [x] **Step 2: Write evidence, compiled, and receipt artifacts instead of mutating source runtime**

```python
evidence_payload = {
    "schema": "lobster.evidence.linked_content.v1",
    "recorded_at_utc": recorded_at_utc,
    "thesis_id": thesis_id,
    "source_run_id": runtime_payload.get("run_id"),
    "linked_item": item,
    "extracted": extracted,
}
receipt_payload = {
    "schema": "lobster.runtime.linked_content_receipt.v1",
    "recorded_at_utc": recorded_at_utc,
    "thesis_id": thesis_id,
    "source_run_id": runtime_payload.get("run_id"),
    "processed_count": len(queue),
    "evidence_paths": evidence_paths,
    "compiled_paths": compiled_paths,
}
```

- [x] **Step 3: Add a CLI entrypoint that processes `latest.json` or an explicit runtime artifact**

```python
parser.add_argument("--workspace", default=".")
parser.add_argument("--thesis-id", required=True)
parser.add_argument("--runtime-file")
parser.add_argument("--linked-url")
```

- [x] **Step 4: Run focused linked-content tests and verify GREEN**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_linked_content_platform.py -q`
Expected: PASS

### Task 3: Document The Platform Slice And Operator Path

**Files:**
- Modify: `lobster-intel/plugins/gooaye-tracker/README.md`
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] **Step 1: Document that linked-content extraction is downstream but artifact-backed**

```md
`linked_content_queue` is now consumed by a dedicated worker that writes evidence and receipt artifacts.
The originating tracker still only declares the queue; it does not fetch or summarize linked content inline.
```

- [x] **Step 2: Document the replay path**

```md
Operators can rerun `lobster-intel/scripts/process_linked_content_queue.py --workspace . --thesis-id gooaye`
against the current queue artifact or point it at a prior runtime JSON for backfill.
```

- [x] **Step 3: Run final verification**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_linked_content_platform.py lobster-intel/tests/test_process_gooaye_channel_digest.py lobster-intel/tests/test_source_runner_e2e.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-linked-content-extraction-platform.md lobster-intel/tests/test_linked_content_platform.py lobster-intel/packages/lobster-ingest/lobster_ingest/linked_content.py lobster-intel/packages/lobster-ingest/lobster_ingest/__init__.py lobster-intel/scripts/process_linked_content_queue.py lobster-intel/plugins/gooaye-tracker/README.md lobster-intel/README.md docs/INSTALL_OPENCLAW.md
git commit -m "feat: add linked content extraction platform"
```
