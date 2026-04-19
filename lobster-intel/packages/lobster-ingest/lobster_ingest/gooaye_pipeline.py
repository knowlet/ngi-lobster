from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHANNEL = "@Gooaye"


def repo_root(ctx=None) -> Path:
    if ctx is not None:
        return Path(ctx.workspace_dir) / "lobster-intel"
    return Path(__file__).resolve().parents[3]


def state_path(ctx=None) -> Path:
    return repo_root(ctx) / "data" / "runtime" / "gooaye" / "channel-state.json"


def tracker_path(ctx=None) -> Path:
    return repo_root(ctx) / "scripts" / "track_telegram_channel.py"


def base_dir(ctx=None) -> Path:
    return repo_root(ctx) / "data"


def _paths(ctx=None) -> dict[str, Path]:
    root = base_dir(ctx)
    compiled = root / "compiled" / "gooaye"
    return {
        "base": root,
        "evidence": root / "evidence" / "gooaye",
        "compiled": compiled,
        "compiled_runs": compiled / "runs",
        "delivery": root / "delivery" / "gooaye",
        "runtime": root / "runtime" / "gooaye",
    }


def ensure_dirs(ctx=None) -> dict[str, Path]:
    paths = _paths(ctx)
    for path in paths.values():
        if path.suffix:
            continue
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _python_executable() -> str:
    return sys.executable or "python3"


def fetch_gooaye_payload(ctx=None, *, state: str | Path | None = None) -> dict[str, Any]:
    result = subprocess.run(
        [
            _python_executable(),
            str(tracker_path(ctx)),
            CHANNEL,
            "--state",
            str(Path(state) if state else state_path(ctx)),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip())


def compact_text(text: str | None, limit: int = 120) -> str:
    s = (text or "").replace("\n", " ").strip()
    s = " ".join(s.split())
    if len(s) <= limit:
        return s
    return s[: limit - 3].rstrip() + "..."


def summarize_item(item: dict[str, Any]) -> str:
    text = compact_text(item.get("text"))
    if text and not text.startswith(("http://", "https://")):
        return f"#{item['post_id']} {text}"

    preview = item.get("preview") or {}
    title = compact_text(preview.get("title"), limit=100)
    site_name = preview.get("site_name")
    if title and site_name:
        return f"#{item['post_id']} [{site_name}] {title}"
    if title:
        return f"#{item['post_id']} {title}"
    if item.get("has_media"):
        return f"#{item['post_id']} 媒體貼文（待 OCR / 圖像理解）"
    return f"#{item['post_id']} 無文字貼文"


def classify_item(item: dict[str, Any]) -> str:
    text = (item.get("text") or "").strip()
    if text.startswith("EP"):
        return "episode"
    if item.get("has_media") and not text:
        return "media_only"
    if (item.get("preview") or {}).get("site_name"):
        return "link_post"
    return "text_post"


def needs_image_analysis(item: dict[str, Any]) -> bool:
    return bool(item.get("image_urls"))


def needs_link_extraction(item: dict[str, Any]) -> bool:
    return bool(((item.get("preview") or {}).get("url") or "").strip())


def build_evidence_record(item: dict[str, Any], *, recorded_at_utc: str) -> dict[str, Any]:
    image_needed = needs_image_analysis(item)
    link_needed = needs_link_extraction(item)
    return {
        "schema": "lobster.evidence.telegram_post.v1",
        "recorded_at_utc": recorded_at_utc,
        "channel": CHANNEL,
        "post_id": item["post_id"],
        "url": item["url"],
        "datetime": item.get("datetime"),
        "text": item.get("text"),
        "preview": item.get("preview"),
        "image_urls": item.get("image_urls", []),
        "has_media": item.get("has_media", False),
        "classification": classify_item(item),
        "needs_image_analysis": image_needed,
        "needs_link_extraction": link_needed,
        "analysis_status": "pending" if image_needed else "not_needed",
        "link_extraction_status": "pending" if link_needed else "not_needed",
        "summary_zh": summarize_item(item),
    }


def build_compiled_markdown(item: dict[str, Any]) -> str:
    preview = item.get("preview") or {}
    image_needed = needs_image_analysis(item)
    link_needed = needs_link_extraction(item)
    lines = [
        f"# Gooaye #{item['post_id']}",
        "",
        f"- URL: {item['url']}",
        f"- Datetime: {item.get('datetime')}",
        f"- Type: {classify_item(item)}",
        f"- Image analysis: {'pending' if image_needed else 'not_needed'}",
        f"- Link extraction: {'pending' if link_needed else 'not_needed'}",
        f"- Summary: {summarize_item(item)}",
    ]
    if item.get("text"):
        lines += ["", "## Text", "", item["text"]]
    if preview:
        lines += [
            "",
            "## Preview",
            "",
            f"- Site: {preview.get('site_name')}",
            f"- Title: {preview.get('title')}",
            f"- URL: {preview.get('url')}",
            f"- Image: {preview.get('image_url')}",
        ]
    if item.get("image_urls"):
        lines += ["", "## Images", ""] + [f"- {url}" for url in item["image_urls"]]
    if image_needed:
        lines += ["", "## Follow-up", "", "- Needs OCR / image understanding pipeline"]
    if link_needed:
        lines += ["", "## Link Follow-up", "", "- Needs linked content extraction / transcript or正文抓取"]
    return "\n".join(lines) + "\n"


def write_digest(payload: dict[str, Any], summaries: list[str], *, paths: dict[str, Path], recorded_at_utc: str) -> tuple[Path, Path, str]:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = paths["compiled_runs"] / f"{run_id}.md"
    latest_path = paths["compiled"] / "latest_digest.md"
    total_count = payload.get("new_count", 0)
    shown_count = len(summaries)
    lines = [
        "# Gooaye Digest",
        "",
        f"- Run id: {run_id}",
        f"- Recorded at: {recorded_at_utc}",
        f"- Channel: {payload.get('channel', CHANNEL)}",
        f"- New count: {total_count}",
    ]
    section_title = "## New items"
    if shown_count and shown_count < total_count:
        section_title = f"## New items (showing {shown_count} of {total_count})"
    if summaries:
        lines += ["", section_title, ""] + [f"- {summary}" for summary in summaries]
    else:
        lines += ["", section_title, "", "- No new items"]
    content = "\n".join(lines) + "\n"
    run_path.write_text(content)
    shutil.copyfile(run_path, latest_path)
    return run_path, latest_path, run_id


def build_runtime_payload(payload: dict[str, Any], *, summaries: list[str], digest_run_path: Path, digest_latest_path: Path, run_id: str, recorded_at_utc: str) -> dict[str, Any]:
    items = payload.get("items", [])
    return {
        "recorded_at_utc": recorded_at_utc,
        "run_id": run_id,
        "channel": payload.get("channel", CHANNEL),
        "new_count": payload.get("new_count", 0),
        "items": items,
        "summaries": summaries,
        "digest_path": str(digest_run_path),
        "latest_digest_path": str(digest_latest_path),
        "image_analysis_queue": [
            {
                "post_id": item.get("post_id"),
                "url": item.get("url"),
                "image_url": (item.get("image_urls") or [None])[0],
            }
            for item in items
            if needs_image_analysis(item)
        ],
        "linked_content_queue": [
            {
                "post_id": item.get("post_id"),
                "url": item.get("url"),
                "linked_url": ((item.get("preview") or {}).get("url")),
                "site_name": ((item.get("preview") or {}).get("site_name")),
                "title": ((item.get("preview") or {}).get("title")),
            }
            for item in items
            if needs_link_extraction(item)
        ],
    }


def process_gooaye_payload(payload: dict[str, Any], ctx=None) -> dict[str, Any]:
    paths = ensure_dirs(ctx)
    recorded_at_utc = datetime.now(timezone.utc).isoformat()
    items = payload.get("items", [])
    summaries: list[str] = []

    for item in items:
        evidence = build_evidence_record(item, recorded_at_utc=recorded_at_utc)
        (paths["evidence"] / f"{item['post_id']}.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
        (paths["compiled"] / f"{item['post_id']}.md").write_text(build_compiled_markdown(item))
        summaries.append(evidence["summary_zh"])

    digest_run_path, digest_latest_path, run_id = write_digest(
        payload,
        summaries,
        paths=paths,
        recorded_at_utc=recorded_at_utc,
    )
    runtime = build_runtime_payload(
        payload,
        summaries=summaries,
        digest_run_path=digest_run_path,
        digest_latest_path=digest_latest_path,
        run_id=run_id,
        recorded_at_utc=recorded_at_utc,
    )
    runtime_path = paths["runtime"] / "latest.json"
    runtime_path.write_text(json.dumps(runtime, ensure_ascii=False, indent=2))

    message = "NO_REPLY"
    if payload.get("new_count", 0):
        lines = [f"Gooaye 有 {payload['new_count']} 則新貼文", ""]
        for item, summary in zip(items[:5], summaries[:5]):
            lines.append(f"• {summary}")
            lines.append(f"  {item['url']}")
        message = "\n".join(lines)
        delivery_path = paths["delivery"] / "latest.json"
        delivery_path.write_text(
            json.dumps(
                {
                    "recorded_at_utc": recorded_at_utc,
                    "channel": payload.get("channel", CHANNEL),
                    "new_count": payload.get("new_count", 0),
                    "message": message,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    return {
        "message": message,
        "runtime": runtime,
        "runtime_path": str(runtime_path),
        "digest_path": str(digest_run_path),
        "latest_digest_path": str(digest_latest_path),
    }


def build_demo_result(runtime: dict[str, Any]) -> dict[str, Any]:
    return {
        "plugin": "gooaye-tracker",
        "version": "0.1.0",
        "new_count": runtime.get("new_count", 0),
        "channel": runtime.get("channel", CHANNEL),
        "run_id": runtime.get("run_id"),
        "digest_path": runtime.get("digest_path"),
    }
