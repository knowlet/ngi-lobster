#!/usr/bin/env python3
import argparse
import html
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def clean_text(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_first(pattern: str, text: str):
    m = re.search(pattern, text, re.S)
    return m.group(1) if m else None


def parse_post_block(block: str):
    post = extract_first(r'data-post="([^"]+)"', block)
    href = extract_first(r'<a class="tgme_widget_message_date" href="([^"]+)"', block)
    dt = extract_first(r'<time datetime="([^"]+)"', block)
    text_raw = extract_first(r'<div class="tgme_widget_message_text js-message_text" dir="auto">(.*?)</div>', block) or ""
    text = clean_text(text_raw)

    preview_href = extract_first(r'<a class="tgme_widget_message_link_preview" href="([^"]+)"', block)
    preview_site = clean_text(extract_first(r'<div class="link_preview_site_name accent_color" dir="auto">(.*?)</div>', block) or "")
    preview_title = clean_text(extract_first(r'<div class="link_preview_title" dir="auto">(.*?)</div>', block) or "")
    preview_image = extract_first(r"background-image:url\('([^']+)'\)", block)

    photo_urls = re.findall(r"tgme_widget_message_photo_wrap[^>]*style=\"background-image:url\('([^']+)'\)", block)
    image_urls = list(dict.fromkeys([u for u in [preview_image, *photo_urls] if u]))

    if not post or not href or not dt:
        return None

    post_id = int(post.split("/")[-1])
    return {
        "post": post,
        "post_id": post_id,
        "text": text,
        "url": href,
        "datetime": dt,
        "preview": {
            "url": preview_href,
            "site_name": preview_site or None,
            "title": preview_title or None,
            "image_url": preview_image,
        } if (preview_href or preview_title or preview_site or preview_image) else None,
        "image_urls": image_urls,
        "has_media": bool(image_urls),
    }


def parse_posts(page_html: str):
    posts = []
    marker = '<div class="tgme_widget_message_wrap' 
    chunks = page_html.split(marker)
    for chunk in chunks[1:]:
        block = marker + chunk
        if 'tgme_widget_message_date' not in block:
            continue
        stop = block.find('<div class="tgme_widget_message_wrap' , 1)
        if stop != -1:
            block = block[:stop]
        parsed = parse_post_block(block)
        if parsed:
            posts.append(parsed)
    return posts


def load_state(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_state(path: Path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def summarize(post):
    text = post["text"].replace("\n", " ").strip()
    if not text:
        preview = post.get("preview") or {}
        preview_title = (preview.get("title") or "").strip()
        if preview_title:
            text = f"[link] {preview_title}"
        elif post.get("has_media"):
            text = "[media-only post]"
        else:
            text = "[empty post]"
    if len(text) > 180:
        text = text[:177] + "..."
    return f"#{post['post_id']} {text} ({post['url']})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("channel")
    ap.add_argument("--state", required=True)
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--init", action="store_true")
    args = ap.parse_args()

    url = f"https://t.me/s/{args.channel.lstrip('@')}"
    page = fetch(url)
    posts = parse_posts(page)
    if not posts:
        raise SystemExit("No posts parsed")

    newest_id = max(p["post_id"] for p in posts)
    state_path = Path(args.state)
    state = load_state(state_path)
    last_seen = state.get("last_seen_post_id")

    if args.init or last_seen is None:
        newest = max(posts, key=lambda p: p["post_id"])
        state.update({
            "channel": args.channel,
            "source_url": url,
            "last_seen_post_id": newest_id,
            "last_seen_url": newest["url"],
            "last_checked_posts": len(posts),
        })
        save_state(state_path, state)
        print(json.dumps({
            "status": "initialized",
            "channel": args.channel,
            "last_seen_post_id": newest_id,
            "last_seen_url": newest["url"],
            "sample": summarize(newest),
        }, ensure_ascii=False))
        return

    new_posts = sorted([p for p in posts if p["post_id"] > last_seen], key=lambda p: p["post_id"])
    newest = max(posts, key=lambda p: p["post_id"])
    state.update({
        "channel": args.channel,
        "source_url": url,
        "last_seen_post_id": newest_id,
        "last_seen_url": newest["url"],
        "last_checked_posts": len(posts),
    })
    save_state(state_path, state)

    print(json.dumps({
        "status": "updated",
        "channel": args.channel,
        "new_count": len(new_posts),
        "last_seen_before": last_seen,
        "last_seen_now": newest_id,
        "items": [
            {
                "post_id": p["post_id"],
                "url": p["url"],
                "datetime": p["datetime"],
                "text": p.get("text"),
                "preview": p.get("preview"),
                "image_urls": p.get("image_urls", []),
                "has_media": p.get("has_media", False),
                "summary": summarize(p),
            }
            for p in new_posts[: args.limit]
        ],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
