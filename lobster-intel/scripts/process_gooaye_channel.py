#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CHANNEL = "@Gooaye"
LOBSTER_DIR = Path(__file__).resolve().parents[1]
STATE_PATH = LOBSTER_DIR / "data" / "runtime" / "gooaye" / "channel-state.json"
TRACKER_PATH = LOBSTER_DIR / "scripts" / "track_telegram_channel.py"
BASE_DIR = LOBSTER_DIR / "data"
EVIDENCE_DIR = BASE_DIR / "evidence" / "gooaye"
COMPILED_DIR = BASE_DIR / "compiled" / "gooaye"
DELIVERY_DIR = BASE_DIR / "delivery" / "gooaye"
RUNTIME_DIR = BASE_DIR / "runtime" / "gooaye"


def write_digest(payload: dict, summaries: list[str]) -> Path:
    path = COMPILED_DIR / "latest_digest.md"
    lines = [
        "# Gooaye Digest",
        "",
        f"- Recorded at: {datetime.now(timezone.utc).isoformat()}",
        f"- Channel: {payload.get('channel', CHANNEL)}",
        f"- New count: {payload.get('new_count', 0)}",
    ]
    if summaries:
        lines += ["", "## New items", ""] + [f"- {summary}" for summary in summaries]
    else:
        lines += ["", "## New items", "", "- No new items"]
    path.write_text("\n".join(lines) + "\n")
    return path


def run_tracker(state_path: Path) -> dict:
    result = subprocess.run(
        ["python3", str(TRACKER_PATH), CHANNEL, "--state", str(state_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip())


def ensure_dirs() -> None:
    for path in [EVIDENCE_DIR, COMPILED_DIR, DELIVERY_DIR, RUNTIME_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def compact_text(text: str | None, limit: int = 120) -> str:
    s = (text or "").replace("\n", " ").strip()
    s = " ".join(s.split())
    if len(s) <= limit:
        return s
    return s[: limit - 3].rstrip() + "..."


def summarize_item(item: dict) -> str:
    text = compact_text(item.get("text"))
    if text and not text.startswith("http://") and not text.startswith("https://"):
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


def classify_item(item: dict) -> str:
    text = (item.get("text") or "").strip()
    if text.startswith("EP"):
        return "episode"
    if item.get("has_media") and not text:
        return "media_only"
    if (item.get("preview") or {}).get("site_name"):
        return "link_post"
    return "text_post"


def needs_image_analysis(item: dict) -> bool:
    return bool(item.get("image_urls"))


def needs_link_extraction(item: dict) -> bool:
    preview = item.get("preview") or {}
    url = (preview.get("url") or "").strip()
    return bool(url)


def write_evidence(item: dict) -> Path:
    image_needed = needs_image_analysis(item)
    link_needed = needs_link_extraction(item)
    payload = {
        "schema": "lobster.evidence.telegram_post.v1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
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
    path = EVIDENCE_DIR / f"{item['post_id']}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return path


def write_compiled(item: dict) -> Path:
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
    path = COMPILED_DIR / f"{item['post_id']}.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def write_runtime(payload: dict, summaries: list[str]) -> Path:
    items = payload.get("items", [])
    digest_path = write_digest(payload, summaries)
    data = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "channel": payload.get("channel", CHANNEL),
        "new_count": payload.get("new_count", 0),
        "items": items,
        "summaries": summaries,
        "digest_path": str(digest_path),
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
    path = RUNTIME_DIR / "latest.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return path


def write_delivery(payload: dict, message: str) -> Path:
    data = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "channel": payload.get("channel", CHANNEL),
        "new_count": payload.get("new_count", 0),
        "message": message,
    }
    path = DELIVERY_DIR / "latest.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=str(STATE_PATH))
    ap.add_argument("extras", nargs="*")
    args = ap.parse_args()

    ensure_dirs()
    payload = run_tracker(Path(args.state))
    items = payload.get("items", [])
    if payload.get("new_count", 0) == 0:
        write_runtime(payload, [])
        print("NO_REPLY")
        return

    summaries = []
    for item in items:
        write_evidence(item)
        write_compiled(item)
        summaries.append(summarize_item(item))

    lines = [f"Gooaye 有 {payload['new_count']} 則新貼文", ""]
    for item, summary in zip(items[:5], summaries[:5]):
        lines.append(f"• {summary}")
        lines.append(f"  {item['url']}")
    message = "\n".join(lines)
    write_runtime(payload, summaries)
    write_delivery(payload, message)
    print(message)


if __name__ == "__main__":
    main()
