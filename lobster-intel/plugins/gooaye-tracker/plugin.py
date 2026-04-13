from __future__ import annotations

from pathlib import Path
import json
import subprocess

CHANNEL = "@Gooaye"


def _repo_root(ctx=None) -> Path:
    if ctx is not None:
        return Path(ctx.workspace_dir) / "lobster-intel"
    return Path(__file__).resolve().parents[2]


def _state_path(ctx=None) -> Path:
    return _repo_root(ctx) / "data" / "runtime" / "gooaye" / "channel-state.json"


def _script_path(ctx=None) -> Path:
    return _repo_root(ctx) / "scripts" / "track_telegram_channel.py"


def _evidence_dir(ctx=None) -> Path:
    return _repo_root(ctx) / "data" / "evidence" / "gooaye"


def _compiled_dir(ctx=None) -> Path:
    return _repo_root(ctx) / "data" / "compiled" / "gooaye"


def ingest(_ctx=None) -> dict:
    result = subprocess.run(
        [
            "python3",
            str(_script_path(_ctx)),
            CHANNEL,
            "--state",
            str(_state_path(_ctx)),
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
        "evidence_dir": str(_evidence_dir()),
        "compiled_dir": str(_compiled_dir()),
    }


def deliver(summary: dict) -> str:
    if summary.get("new_count", 0) == 0:
        return "NO_REPLY"

    bullets = []
    for item in summary.get("items", [])[:5]:
        bullets.append(f"- {item['summary']}")
    bullet_text = "\n".join(bullets)
    return f"Gooaye 頻道更新，共 {summary['new_count']} 則新貼文\n{bullet_text}"
