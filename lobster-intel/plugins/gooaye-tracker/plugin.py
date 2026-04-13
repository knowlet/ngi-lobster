from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
import subprocess

STATE_PATH = Path("/Users/knowlet/.openclaw/workspace/memory/gooaye-channel-state.json")
SCRIPT_PATH = Path("/Users/knowlet/.openclaw/workspace/scripts/track_telegram_channel.py")
CHANNEL = "@Gooaye"
EVIDENCE_DIR = Path("/Users/knowlet/.openclaw/workspace/lobster-intel/data/evidence/gooaye")
COMPILED_DIR = Path("/Users/knowlet/.openclaw/workspace/lobster-intel/data/compiled/gooaye")


def ingest(_ctx=None) -> dict:
    result = subprocess.run(
        [
            "python3",
            str(SCRIPT_PATH),
            CHANNEL,
            "--state",
            str(STATE_PATH),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    stdout = result.stdout.strip()
    return json.loads(stdout)


def summarize(payload: dict) -> dict:
    new_count = payload.get("new_count", 0)
    items = payload.get("items", [])
    return {
        "channel": payload.get("channel", CHANNEL),
        "new_count": new_count,
        "items": [
            {
                "post_id": item.get("post_id"),
                "summary": item.get("summary"),
                "url": item.get("url"),
                "text": item.get("text"),
                "preview": item.get("preview"),
                "image_urls": item.get("image_urls", []),
                "has_media": item.get("has_media", False),
            }
            for item in items
        ],
        "evidence_dir": str(EVIDENCE_DIR),
        "compiled_dir": str(COMPILED_DIR),
    }


def deliver(summary: dict) -> str:
    if summary.get("new_count", 0) == 0:
        return "NO_REPLY"

    bullets = []
    for item in summary.get("items", [])[:5]:
        bullets.append(f"- {item['summary']}")
    bullet_text = "\n".join(bullets)
    return f"Gooaye 頻道更新，共 {summary['new_count']} 則新貼文\n{bullet_text}"
