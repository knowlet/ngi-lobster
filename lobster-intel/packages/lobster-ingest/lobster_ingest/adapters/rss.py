from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

from .base import FetchResult, RawItem
from .http import fetch_text


def _text(node, path: str) -> str | None:
    found = node.find(path)
    if found is None or found.text is None:
        return None
    return found.text.strip() or None


def _normalize_published(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
    except Exception:
        return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


@dataclass(slots=True)
class RssFeedAdapter:
    source_id: str
    source_type: str
    url: str

    def fetch(self, since_cursor: str | None = None) -> FetchResult:
        xml_text = fetch_text(self.url)
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        entries = channel.findall("item") if channel is not None else root.findall(".//item")
        items: list[RawItem] = []
        latest = since_cursor
        for entry in entries:
            guid = _text(entry, "guid") or _text(entry, "link") or _text(entry, "title")
            published = _normalize_published(_text(entry, "pubDate"))
            if since_cursor and published and published <= since_cursor:
                continue
            latest = max(filter(None, [latest, published]), default=latest)
            items.append(
                RawItem(
                    source_id=self.source_id,
                    source_type=self.source_type,
                    external_id=guid or f"{self.source_id}:{len(items)}",
                    title=_text(entry, "title"),
                    url=_text(entry, "link"),
                    summary=_text(entry, "description"),
                    content=_text(entry, "description"),
                    collected_at_utc=datetime.now(timezone.utc).isoformat(),
                    published_at_utc=published,
                    metadata={"feed_url": self.url},
                )
            )
        return FetchResult(items=items, next_cursor=latest, metadata={"feed_url": self.url})
