from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


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
    runtime = root / "runtime" / thesis_id / "visual-evidence"
    return {
        "evidence": root / "evidence" / thesis_id / "visual-evidence",
        "compiled": root / "compiled" / thesis_id / "visual-evidence",
        "runtime": runtime,
        "runtime_runs": runtime / "runs",
    }


def _ensure_dirs(workspace_dir: str | Path, thesis_id: str) -> dict[str, Path]:
    paths = _artifact_paths(workspace_dir, thesis_id)
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _relative_path(path: Path, workspace_dir: str | Path) -> str:
    return str(path.relative_to(Path(workspace_dir)))


def _item_stem(source_run_id: str, item: dict[str, Any], index: int) -> str:
    post_id = _safe_name(str(item.get("post_id") or f"item-{index}"), fallback=f"item-{index}")
    run_id = _safe_name(source_run_id, fallback="visual-evidence")
    return f"{run_id}--post-{post_id}"


def ocr_image(item: dict[str, Any]) -> dict[str, Any]:
    image_url = str(item.get("image_url") or "").strip()
    return {
        "image_url": image_url or None,
        "ocr_text": "",
        "summary": None,
        "error": "ocr_adapter_not_configured",
    }


def _run_ocr(item: dict[str, Any], *, ocr_adapter: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    image_url = str(item.get("image_url") or "").strip()
    if not image_url:
        return {
            "image_url": None,
            "ocr_text": "",
            "summary": None,
            "error": "missing image_url",
        }

    try:
        result = dict(ocr_adapter(item) or {})
    except Exception as exc:  # pragma: no cover - defensive audit path
        return {
            "image_url": image_url,
            "ocr_text": "",
            "summary": None,
            "error": str(exc),
        }

    result.setdefault("image_url", image_url)
    result.setdefault("ocr_text", "")
    result.setdefault("summary", None)
    return result


def _compiled_markdown(
    *,
    thesis_id: str,
    source_run_id: str,
    image_item: dict[str, Any],
    ocr_result: dict[str, Any],
    recorded_at_utc: str,
) -> str:
    lines = [
        f"# Visual Evidence {image_item.get('post_id') or 'manual'}",
        "",
        f"- Thesis: {thesis_id}",
        f"- Source run id: {source_run_id}",
        f"- Recorded at: {recorded_at_utc}",
        f"- Queue URL: {image_item.get('url')}",
        f"- Image URL: {ocr_result.get('image_url') or image_item.get('image_url')}",
        f"- OCR summary: {ocr_result.get('summary')}",
    ]
    ocr_text = (ocr_result.get("ocr_text") or "").strip()
    if ocr_text:
        lines += ["", "## OCR Text", "", ocr_text]
    if ocr_result.get("error"):
        lines += ["", "## OCR Error", "", str(ocr_result["error"])]
    return "\n".join(lines) + "\n"


def _write_receipt(
    *,
    workspace_dir: str | Path,
    thesis_id: str,
    source_run_id: str,
    recorded_at_utc: str,
    status: str,
    processed_count: int,
    success_count: int,
    error_count: int,
    evidence_paths: list[str],
    compiled_paths: list[str],
) -> str:
    paths = _ensure_dirs(workspace_dir, thesis_id)
    receipt_payload = {
        "schema": "lobster.runtime.visual_evidence_receipt.v1",
        "recorded_at_utc": recorded_at_utc,
        "thesis_id": thesis_id,
        "source_run_id": source_run_id,
        "status": status,
        "processed_count": processed_count,
        "success_count": success_count,
        "error_count": error_count,
        "evidence_paths": evidence_paths,
        "compiled_paths": compiled_paths,
    }
    run_name = _safe_name(source_run_id, fallback="visual-evidence")
    run_path = paths["runtime_runs"] / f"{run_name}.json"
    latest_path = paths["runtime"] / "latest.json"
    payload = json.dumps(receipt_payload, ensure_ascii=False, indent=2)
    run_path.write_text(payload, encoding="utf-8")
    latest_path.write_text(payload, encoding="utf-8")
    return _relative_path(run_path, workspace_dir)


def process_visual_evidence_queue(
    *,
    workspace_dir: str | Path,
    thesis_id: str,
    runtime_payload: dict[str, Any],
    ocr_adapter: Callable[[dict[str, Any]], dict[str, Any]],
    now_utc: str | None = None,
) -> dict[str, Any]:
    queue = list(runtime_payload.get("image_analysis_queue") or [])
    source_run_id = str(runtime_payload.get("run_id") or "visual-evidence")
    recorded_at_utc = _now_utc(now_utc)

    if not queue:
        receipt_path = _write_receipt(
            workspace_dir=workspace_dir,
            thesis_id=thesis_id,
            source_run_id=source_run_id,
            recorded_at_utc=recorded_at_utc,
            status="no_items",
            processed_count=0,
            success_count=0,
            error_count=0,
            evidence_paths=[],
            compiled_paths=[],
        )
        return {
            "status": "no_items",
            "processed_count": 0,
            "success_count": 0,
            "error_count": 0,
            "evidence_paths": [],
            "compiled_paths": [],
            "receipt_path": receipt_path,
        }

    paths = _ensure_dirs(workspace_dir, thesis_id)
    evidence_paths: list[str] = []
    compiled_paths: list[str] = []
    max_workers = min(4, len(queue))

    def run_item(item: dict[str, Any]) -> dict[str, Any]:
        return _run_ocr(item, ocr_adapter=ocr_adapter)

    if max_workers == 1:
        ocr_results = [run_item(item) for item in queue]
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            ocr_results = list(executor.map(run_item, queue))

    error_count = sum(1 for result in ocr_results if result.get("error"))
    success_count = len(ocr_results) - error_count

    for index, (item, ocr_result) in enumerate(zip(queue, ocr_results)):
        stem = _item_stem(source_run_id, item, index)
        evidence_path = paths["evidence"] / f"{stem}.json"
        compiled_path = paths["compiled"] / f"{stem}.md"
        evidence_payload = {
            "schema": "lobster.evidence.visual_evidence.v1",
            "recorded_at_utc": recorded_at_utc,
            "thesis_id": thesis_id,
            "source_run_id": source_run_id,
            "image_item": item,
            "ocr": ocr_result,
        }
        evidence_path.write_text(json.dumps(evidence_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        compiled_path.write_text(
            _compiled_markdown(
                thesis_id=thesis_id,
                source_run_id=source_run_id,
                image_item=item,
                ocr_result=ocr_result,
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
        success_count=success_count,
        error_count=error_count,
        evidence_paths=evidence_paths,
        compiled_paths=compiled_paths,
    )
    return {
        "status": "processed",
        "processed_count": len(queue),
        "success_count": success_count,
        "error_count": error_count,
        "evidence_paths": evidence_paths,
        "compiled_paths": compiled_paths,
        "receipt_path": receipt_path,
    }
