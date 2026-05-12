from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from .base import FetchResult, RawItem
from .http import fetch_json


_DATE_TOKEN_RE = re.compile(
    r"-(?:january|february|march|april|may|june|july|august|september|october|november|december)-\d{1,2}(?:st|nd|rd|th)?(?:-\d{4})?(?:-(?:\d+))*$"
)


def _decode_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def _slugify(text: object) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or None


def _infer_event_slug(record: dict[str, Any]) -> str | None:
    """Infer a Gamma event slug from grouped market metadata.

    Polymarket's market detail API does not currently expose the parent event,
    but grouped range markets include `groupItemTitle` (for example "June 30")
    and the market page redirects to `/event/<event-slug>/<market-slug>`.  For
    these range markets the event slug is the stable market slug prefix before
    the date/group item segment.  If that structure is not present, return None
    rather than guessing.
    """
    slug = record.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        return None
    slug = slug.strip()

    group_slug = _slugify(record.get("groupItemTitle"))
    if group_slug:
        match = re.search(rf"-{re.escape(group_slug)}(?:st|nd|rd|th)?(?:-(?:\d+))*$", slug)
        if match:
            event_slug = slug[: match.start()]
            return event_slug or None

    match = _DATE_TOKEN_RE.search(slug)
    if match:
        event_slug = slug[: match.start()]
        return event_slug or None
    return None


def _extract_yes_probability(record: dict[str, Any]) -> Any:
    outcome_prices = _decode_json_list(record.get("outcomePrices") or record.get("outcome_prices"))
    if not outcome_prices:
        return None
    try:
        return float(outcome_prices[0])
    except Exception:
        return outcome_prices[0]


def _records(payload: Any) -> list[dict[str, Any]]:
    raw_records = payload if isinstance(payload, list) else [payload]
    return [record for record in raw_records if isinstance(record, dict)]


@dataclass(slots=True)
class PolymarketAdapter:
    source_id: str = "polymarket"
    source_type: str = "prediction_market"
    endpoint: str = "https://gamma-api.polymarket.com/markets"
    event_endpoint: str = "https://gamma-api.polymarket.com/events"
    markets: list[dict] = field(default_factory=list)

    def _fetch_market_records(self, market: dict) -> list[dict[str, Any]]:
        if market.get("id"):
            try:
                payload = fetch_json(f"{self.endpoint.rstrip('/')}/{quote(str(market['id']))}")
            except Exception:
                payload = fetch_json(self.endpoint, params={"closed": "true", "id": market["id"]})
            return _records(payload)
        if market.get("slug"):
            payload = fetch_json(self.endpoint, params={"closed": "true", "slug": market["slug"]})
            records = _records(payload)
            if records:
                return records
            payload = fetch_json(self.endpoint, params={"slug": market["slug"]})
            return _records(payload)
        payload = fetch_json(self.endpoint)
        return _records(payload)

    def _fetch_event_market_records(
        self,
        market: dict,
        seed_records: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        if market.get("discover_event_markets") is False:
            return [], None
        event_slug = market.get("event_slug")
        if not isinstance(event_slug, str) or not event_slug.strip():
            for record in seed_records:
                event_slug = _infer_event_slug(record)
                if event_slug:
                    break
        if not isinstance(event_slug, str) or not event_slug.strip():
            return [], None

        event_payload = fetch_json(self.event_endpoint, params={"closed": "true", "slug": event_slug.strip()})
        events = _records(event_payload)
        if not events:
            return [], None
        event = events[0]
        event_markets = event.get("markets")
        if not isinstance(event_markets, list):
            return [], event
        return [record for record in event_markets if isinstance(record, dict)], event

    def _raw_item(
        self,
        record: dict[str, Any],
        market: dict,
        *,
        collected: str,
        event: dict[str, Any] | None = None,
        relationship: str = "configured_market",
    ) -> RawItem:
        market_id = str(record.get("id") or market.get("id") or market.get("slug"))
        question = record.get("question") or record.get("title") or market.get("label") or market_id
        accepting_orders = (
            record["acceptingOrders"] if "acceptingOrders" in record else record.get("accepting_orders")
        )
        metadata: dict[str, Any] = {
            "market_id": market_id,
            "slug": record.get("slug"),
            "yes_probability": _extract_yes_probability(record),
            "active": record.get("active"),
            "closed": record.get("closed"),
            "accepting_orders": accepting_orders,
            "source_config": market,
            "relationship": relationship,
        }
        if event is not None:
            metadata["event_id"] = event.get("id")
            metadata["event_slug"] = event.get("slug")
            metadata["event_title"] = event.get("title")
        return RawItem(
            source_id=self.source_id,
            source_type=self.source_type,
            external_id=market_id,
            title=question,
            url=record.get("url") or record.get("slug"),
            summary=question,
            collected_at_utc=collected,
            published_at_utc=record.get("endDate") or record.get("end_date_iso"),
            metadata=metadata,
        )

    def fetch(self, since_cursor: str | None = None) -> FetchResult:
        collected = datetime.now(timezone.utc).isoformat()
        items: list[RawItem] = []
        seen_market_ids: set[str] = set()
        event_count = 0
        for market in self.markets:
            seed_records = self._fetch_market_records(market)
            event_records, event = self._fetch_event_market_records(market, seed_records)
            records_with_relationship = [
                (record, "configured_market", None) for record in seed_records
            ] + [
                (record, "event_sibling", event) for record in event_records
            ]
            if event_records:
                event_count += 1
            for record, relationship, record_event in records_with_relationship:
                market_id = str(record.get("id") or market.get("id") or market.get("slug") or len(items))
                if market_id in seen_market_ids:
                    continue
                seen_market_ids.add(market_id)
                items.append(
                    self._raw_item(
                        record,
                        market,
                        collected=collected,
                        event=record_event,
                        relationship=relationship,
                    )
                )
        return FetchResult(
            items=items,
            next_cursor=collected,
            metadata={
                "endpoint": self.endpoint,
                "event_endpoint": self.event_endpoint,
                "market_count": len(self.markets),
                "event_count": event_count,
            },
        )
