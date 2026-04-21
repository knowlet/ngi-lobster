# Visual Evidence OCR Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `image_analysis_queue` into a replayable OCR backfill workflow that writes auditable evidence, compiled markdown, and runtime receipts without mutating source ingest artifacts in place.

**Architecture:** Keep `gooaye_pipeline` responsible only for declaring image-analysis follow-up work in runtime payloads. Add a new `lobster_ingest.visual_evidence` helper plus a thin CLI that reads `lobster-intel/data/runtime/<thesis-id>/latest.json` or an explicit runtime file, runs an injectable OCR adapter per queued item, and writes downstream artifacts under `lobster-intel/data/evidence/<thesis-id>/visual-evidence/`, `compiled/<thesis-id>/visual-evidence/`, and `runtime/<thesis-id>/visual-evidence/`.

**Tech Stack:** Python 3.11+, stdlib `json`/`pathlib`/`argparse`, existing `lobster-ingest` package, pytest

**Status:** Implemented in the writable workspace on 2026-04-21 and re-verified with `./.venv/bin/python -m pytest lobster-intel/tests/test_visual_evidence_platform.py lobster-intel/tests/test_gooaye_pipeline.py lobster-intel/tests/test_linked_content_platform.py -q` (`12 passed`). Post-review hardening on 2026-04-21 parallelized OCR queue execution while preserving artifact write order. Committed in the repo-backed workspace during the 2026-04-21 automation run; push remains blocked by network access in this environment.

---

### Task 1: Lock The OCR Backfill Contract With Tests

**Files:**
- Create: `lobster-intel/tests/test_visual_evidence_platform.py`

- [x] **Step 1: Write the failing happy-path test for one queued image**

```python
def test_process_visual_evidence_queue_writes_artifacts(tmp_path: Path):
    runtime_payload = {
        "run_id": "gooaye-20260421T000000Z",
        "image_analysis_queue": [
            {
                "post_id": "6059",
                "url": "https://t.me/gooaye/6059",
                "image_url": "https://example.com/chart.png",
            }
        ],
    }

    result = process_visual_evidence_queue(
        workspace_dir=tmp_path,
        thesis_id="gooaye",
        runtime_payload=runtime_payload,
        ocr_adapter=lambda item: {
            "image_url": item["image_url"],
            "ocr_text": "Feature FSD US FSD Europe Netherlands",
            "summary": "Comparison chart between US and EU FSD features",
        },
        now_utc="2026-04-21T00:00:00+00:00",
    )

    assert result["processed_count"] == 1
    assert (tmp_path / result["evidence_paths"][0]).exists()
    assert (tmp_path / result["compiled_paths"][0]).exists()
    assert (tmp_path / result["receipt_path"]).exists()
```

- [x] **Step 2: Write the failing empty-queue receipt test**

```python
def test_process_visual_evidence_queue_records_empty_receipt(tmp_path: Path):
    result = process_visual_evidence_queue(
        workspace_dir=tmp_path,
        thesis_id="gooaye",
        runtime_payload={"run_id": "gooaye-20260421T000000Z", "image_analysis_queue": []},
        ocr_adapter=lambda item: {},
        now_utc="2026-04-21T00:00:00+00:00",
    )

    assert result["status"] == "no_items"
    assert result["processed_count"] == 0
    assert result["evidence_paths"] == []
```

- [x] **Step 3: Write the failing CLI coverage test**

```python
payload = json.loads(
    subprocess.check_output(
        [
            sys.executable,
            "lobster-intel/scripts/process_visual_evidence_queue.py",
            "--workspace",
            str(tmp_path),
            "--thesis-id",
            "gooaye",
        ],
        text=True,
    )
)
assert payload["status"] == "processed"
assert payload["processed_count"] == 1
```

- [x] **Step 4: Run focused tests and verify RED**

Run: `./.venv/bin/python -m pytest lobster-intel/tests/test_visual_evidence_platform.py -q`
Expected: FAIL because `lobster_ingest.visual_evidence` and the CLI do not exist yet

### Task 2: Implement Replayable OCR Backfill Helpers And CLI

**Files:**
- Create: `lobster-intel/packages/lobster-ingest/lobster_ingest/visual_evidence.py`
- Modify: `lobster-intel/packages/lobster-ingest/lobster_ingest/__init__.py`
- Create: `lobster-intel/scripts/process_visual_evidence_queue.py`

- [x] **Step 1: Implement runtime loading and queue processing**

```python
def process_visual_evidence_queue(
    *,
    workspace_dir: str | Path,
    thesis_id: str,
    runtime_payload: dict[str, Any],
    ocr_adapter: Callable[[dict[str, Any]], dict[str, Any]],
    now_utc: str | None = None,
) -> dict[str, Any]:
    queue = list(runtime_payload.get("image_analysis_queue") or [])
    if not queue:
        return _write_empty_receipt(
            workspace_dir=workspace_dir,
            thesis_id=thesis_id,
            source_run_id=str(runtime_payload.get("run_id") or "visual-evidence"),
            now_utc=now_utc,
        )
```

- [x] **Step 2: Write evidence, compiled markdown, and receipt artifacts**

```python
evidence_payload = {
    "schema": "lobster.evidence.visual_evidence.v1",
    "recorded_at_utc": recorded_at_utc,
    "thesis_id": thesis_id,
    "source_run_id": source_run_id,
    "image_item": item,
    "ocr": ocr_result,
}
receipt_payload = {
    "schema": "lobster.runtime.visual_evidence_receipt.v1",
    "recorded_at_utc": recorded_at_utc,
    "thesis_id": thesis_id,
    "source_run_id": source_run_id,
    "status": "processed",
    "processed_count": len(queue),
    "evidence_paths": evidence_paths,
    "compiled_paths": compiled_paths,
}
```

- [x] **Step 3: Fail closed on missing image URLs or adapter errors**

```python
def _run_ocr(item: dict[str, Any], *, ocr_adapter: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    image_url = str(item.get("image_url") or "").strip()
    if not image_url:
        return {"image_url": None, "ocr_text": "", "summary": None, "error": "missing image_url"}
    try:
        return ocr_adapter(item)
    except Exception as exc:
        return {"image_url": image_url, "ocr_text": "", "summary": None, "error": str(exc)}
```

- [x] **Step 4: Add the CLI entrypoint**

```python
parser = argparse.ArgumentParser()
parser.add_argument("--workspace", default=".")
parser.add_argument("--thesis-id", required=True)
parser.add_argument("--runtime-file")
```

- [x] **Step 5: Run focused tests and verify GREEN**

Run: `./.venv/bin/python -m pytest lobster-intel/tests/test_visual_evidence_platform.py -q`
Expected: PASS

### Task 3: Wire Operator Docs To The New OCR Backfill Path

**Files:**
- Modify: `lobster-intel/plugins/gooaye-tracker/README.md`
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] **Step 1: Document that `image_analysis_queue` is consumed downstream**

```md
`image_analysis_queue` is consumed by a dedicated OCR backfill worker that writes evidence, compiled, and runtime receipt artifacts.
The source ingest step still only declares pending image analysis work; it does not silently rewrite the source evidence record.
```

- [x] **Step 2: Document the operator replay path**

```md
./.venv/bin/python lobster-intel/scripts/process_visual_evidence_queue.py \
  --workspace . \
  --thesis-id gooaye
```

- [x] **Step 3: Run final verification across the Gooaye slice**

Run: `./.venv/bin/python -m pytest lobster-intel/tests/test_visual_evidence_platform.py lobster-intel/tests/test_gooaye_pipeline.py lobster-intel/tests/test_linked_content_platform.py -q`
Expected: PASS

- [x] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-21-visual-evidence-ocr-backfill.md lobster-intel/tests/test_visual_evidence_platform.py lobster-intel/packages/lobster-ingest/lobster_ingest/visual_evidence.py lobster-intel/packages/lobster-ingest/lobster_ingest/__init__.py lobster-intel/scripts/process_visual_evidence_queue.py lobster-intel/plugins/gooaye-tracker/README.md lobster-intel/README.md docs/INSTALL_OPENCLAW.md
git commit -m "feat: add visual evidence OCR backfill"
```
