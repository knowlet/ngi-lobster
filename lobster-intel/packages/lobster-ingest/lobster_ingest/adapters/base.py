from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class RawItem:
    source_id: str
    source_type: str
    external_id: str
    title: str | None = None
    url: str | None = None
    collected_at_utc: str | None = None
    published_at_utc: str | None = None
    summary: str | None = None
    content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchResult:
    items: list[RawItem]
    next_cursor: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    def fetch(self, since_cursor: str | None = None) -> FetchResult: ...
