from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


_HTML_TAG = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_TAG = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_SPACE = re.compile(r"\s+")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_SUPPORTED_URL_SCHEMES = {"http", "https"}
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
_MAX_RESPONSE_BYTES = 10_000_000


def _now_utc(value: str | None = None) -> str:
    if value:
        return value
    return datetime.now(timezone.utc).isoformat()


def _safe_name(value: str | None, *, fallback: str) -> str:
    cleaned = _SAFE_NAME.sub("-", (value or "").strip()).strip("-._")
    return cleaned or fallback


def _workspace_root(workspace_dir: str | Path) -> Path:
    return Path(workspace_dir) / "lobster-intel" / "data"


def _artifact_paths(workspace_dir: str | Path, thesis_id: str) -> dict[str, Path]:
    root = _workspace_root(workspace_dir)
    runtime = root / "runtime" / thesis_id / "linked-content"
    return {
        "evidence": root / "evidence" / thesis_id / "linked-content",
        "compiled": root / "compiled" / thesis_id / "linked-content",
        "runtime": runtime,
        "runtime_runs": runtime / "runs",
        "source_runtime_runs": root / "runtime" / thesis_id / "runs",
    }


def _ensure_dirs(workspace_dir: str | Path, thesis_id: str) -> dict[str, Path]:
    paths = _artifact_paths(workspace_dir, thesis_id)
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _relative_path(path: Path, workspace_dir: str | Path) -> str:
    return str(path.relative_to(Path(workspace_dir)))


def _runtime_payload_path(workspace_dir: str | Path, thesis_id: str) -> Path:
    return _workspace_root(workspace_dir) / "runtime" / thesis_id / "latest.json"


def load_runtime_payload(
    workspace_dir: str | Path,
    thesis_id: str,
    *,
    runtime_file: str | Path | None = None,
) -> dict[str, Any]:
    payload_path = Path(runtime_file) if runtime_file else _runtime_payload_path(workspace_dir, thesis_id)
    return json.loads(payload_path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_title(html: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return _SPACE.sub(" ", match.group(1)).strip() or None


def _plain_text(value: str) -> str:
    value = _SCRIPT_STYLE_TAG.sub(" ", value)
    without_tags = _HTML_TAG.sub(" ", value)
    return _SPACE.sub(" ", without_tags).strip()


def extract_linked_content(url: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in _SUPPORTED_URL_SCHEMES:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme or '<missing>'}")

    req = urllib.request.Request(url, headers={"User-Agent": _DEFAULT_USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as response:
        raw_bytes = response.read(_MAX_RESPONSE_BYTES + 1)
        if len(raw_bytes) > _MAX_RESPONSE_BYTES:
            raise ValueError(f"Response exceeds max size of {_MAX_RESPONSE_BYTES} bytes")
        content_type = response.headers.get_content_type()
    raw = raw_bytes.decode("utf-8", errors="replace")
    is_html = "html" in content_type.lower() or "<html" in raw.lower()
    text_content = _plain_text(raw) if is_html else raw.strip()
    return {
        "url": url,
        "content_type": content_type,
        "title": _extract_title(raw) if is_html else None,
        "content": text_content,
    }


def _item_stem(source_run_id: str, item: dict[str, Any], index: int) -> str:
    post_id = _safe_name(str(item.get("post_id") or f"item-{index}"), fallback=f"item-{index}")
    run_id = _safe_name(source_run_id, fallback="linked-content")
    return f"{run_id}--post-{post_id}"


def _compiled_markdown(
    *,
    thesis_id: str,
    source_run_id: str,
    linked_item: dict[str, Any],
    extracted: dict[str, Any],
    recorded_at_utc: str,
) -> str:
    lines = [
        f"# Linked Content {linked_item.get('post_id') or 'manual'}",
        "",
        f"- Thesis: {thesis_id}",
        f"- Source run id: {source_run_id}",
        f"- Recorded at: {recorded_at_utc}",
        f"- Queue URL: {linked_item.get('url')}",
        f"- Linked URL: {linked_item.get('linked_url')}",
        f"- Site: {linked_item.get('site_name')}",
        f"- Queue title: {linked_item.get('title')}",
        f"- Extracted title: {extracted.get('title')}",
        f"- Content type: {extracted.get('content_type')}",
    ]
    content = (extracted.get("content") or "").strip()
    if content:
        lines += ["", "## Extracted Content", "", content]
    if extracted.get("error"):
        lines += ["", "## Extraction Error", "", str(extracted["error"])]
    return "\n".join(lines) + "\n"


def _write_receipt(
    *,
    workspace_dir: str | Path,
    thesis_id: str,
    source_run_id: str,
    recorded_at_utc: str,
    status: str,
    processed_count: int,
    evidence_paths: list[str],
    compiled_paths: list[str],
) -> str:
    paths = _ensure_dirs(workspace_dir, thesis_id)
    receipt_payload = {
        "schema": "lobster.runtime.linked_content_receipt.v1",
        "recorded_at_utc": recorded_at_utc,
        "thesis_id": thesis_id,
        "source_run_id": source_run_id,
        "status": status,
        "processed_count": processed_count,
        "evidence_paths": evidence_paths,
        "compiled_paths": compiled_paths,
    }
    run_name = _safe_name(source_run_id, fallback="linked-content")
    run_path = paths["runtime_runs"] / f"{run_name}.json"
    latest_path = paths["runtime"] / "latest.json"
    payload = json.dumps(receipt_payload, ensure_ascii=False, indent=2)
    run_path.write_text(payload, encoding="utf-8")
    latest_path.write_text(payload, encoding="utf-8")
    return _relative_path(run_path, workspace_dir)


def _extract_queue_item(
    item: dict[str, Any],
    *,
    extractor: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    linked_url = str(item.get("linked_url") or item.get("url") or "").strip()
    if not linked_url:
        return {
            "url": None,
            "title": None,
            "content": "",
            "content_type": None,
            "error": "missing linked_url",
        }

    try:
        return extractor(linked_url)
    except Exception as exc:  # pragma: no cover - defensive audit path
        return {
            "url": linked_url,
            "title": None,
            "content": "",
            "content_type": None,
            "error": str(exc),
        }


def process_linked_content_queue(
    *,
    workspace_dir: str | Path,
    thesis_id: str,
    runtime_payload: dict[str, Any],
    extractor: Callable[[str], dict[str, Any]],
    now_utc: str | None = None,
) -> dict[str, Any]:
    queue = list(runtime_payload.get("linked_content_queue") or [])
    source_run_id = str(runtime_payload.get("run_id") or "linked-content")
    recorded_at_utc = _now_utc(now_utc)

    if not queue:
        receipt_path = _write_receipt(
            workspace_dir=workspace_dir,
            thesis_id=thesis_id,
            source_run_id=source_run_id,
            recorded_at_utc=recorded_at_utc,
            status="no_items",
            processed_count=0,
            evidence_paths=[],
            compiled_paths=[],
        )
        return {
            "status": "no_items",
            "processed_count": 0,
            "evidence_paths": [],
            "compiled_paths": [],
            "receipt_path": receipt_path,
        }

    paths = _ensure_dirs(workspace_dir, thesis_id)
    evidence_paths: list[str] = []
    compiled_paths: list[str] = []
    max_workers = min(4, len(queue))

    def extract_item(item: dict[str, Any]) -> dict[str, Any]:
        return _extract_queue_item(item, extractor=extractor)

    if max_workers == 1:
        extracted_items = [extract_item(item) for item in queue]
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            extracted_items = list(executor.map(extract_item, queue))

    for index, (item, extracted) in enumerate(zip(queue, extracted_items)):
        stem = _item_stem(source_run_id, item, index)
        evidence_path = paths["evidence"] / f"{stem}.json"
        compiled_path = paths["compiled"] / f"{stem}.md"
        evidence_payload = {
            "schema": "lobster.evidence.linked_content.v1",
            "recorded_at_utc": recorded_at_utc,
            "thesis_id": thesis_id,
            "source_run_id": source_run_id,
            "linked_item": item,
            "extracted": extracted,
        }
        evidence_path.write_text(json.dumps(evidence_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        compiled_path.write_text(
            _compiled_markdown(
                thesis_id=thesis_id,
                source_run_id=source_run_id,
                linked_item=item,
                extracted=extracted,
                recorded_at_utc=recorded_at_utc,
            ),
            encoding="utf-8",
        )
        evidence_paths.append(_relative_path(evidence_path, workspace_dir))
        compiled_paths.append(_relative_path(compiled_path, workspace_dir))

    receipt_path = _write_receipt(
        workspace_dir=workspace_dir,
        thesis_id=thesis_id,
        source_run_id=source_run_id,
        recorded_at_utc=recorded_at_utc,
        status="processed",
        processed_count=len(queue),
        evidence_paths=evidence_paths,
        compiled_paths=compiled_paths,
    )
    return {
        "status": "processed",
        "processed_count": len(queue),
        "evidence_paths": evidence_paths,
        "compiled_paths": compiled_paths,
        "receipt_path": receipt_path,
    }


def backfill_linked_content_runs(
    *,
    workspace_dir: str | Path,
    thesis_id: str,
    extractor: Callable[[str], dict[str, Any]],
    now_utc: str | None = None,
) -> dict[str, Any]:
    paths = _ensure_dirs(workspace_dir, thesis_id)
    runtime_runs_dir = paths["source_runtime_runs"]
    processed_runs: list[dict[str, Any]] = []
    skipped_runs: list[dict[str, str]] = []

    if not runtime_runs_dir.exists():
        return {
            "status": "ok",
            "processed_count": 0,
            "skipped_existing_count": 0,
            "skipped_no_items_count": 0,
            "processed_runs": [],
            "skipped_runs": [],
        }

    for runtime_path in sorted(runtime_runs_dir.glob("*.json")):
        runtime_payload = _load_json(runtime_path)
        source_run_id = str(runtime_payload.get("run_id") or runtime_path.stem)
        receipt_name = f"{_safe_name(source_run_id, fallback='linked-content')}.json"
        receipt_path = paths["runtime_runs"] / receipt_name
        queue = list(runtime_payload.get("linked_content_queue") or [])

        if receipt_path.exists():
            skipped_runs.append({"run_id": source_run_id, "reason": "existing_receipt"})
            continue
        if not queue:
            skipped_runs.append({"run_id": source_run_id, "reason": "no_items"})
            continue

        result = process_linked_content_queue(
            workspace_dir=workspace_dir,
            thesis_id=thesis_id,
            runtime_payload=runtime_payload,
            extractor=extractor,
            now_utc=now_utc,
        )
        processed_runs.append({"run_id": source_run_id, **result})

    return {
        "status": "ok",
        "processed_count": len(processed_runs),
        "skipped_existing_count": sum(1 for item in skipped_runs if item["reason"] == "existing_receipt"),
        "skipped_no_items_count": sum(1 for item in skipped_runs if item["reason"] == "no_items"),
        "processed_runs": processed_runs,
        "skipped_runs": skipped_runs,
    }
