from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .base import FetchResult, RawItem
from .http import fetch_json


@dataclass(slots=True)
class PolymarketAdapter:
    source_id: str = "polymarket"
    source_type: str = "prediction_market"
    endpoint: str = "https://gamma-api.polymarket.com/markets"
    markets: list[dict] = field(default_factory=list)

    def fetch(self, since_cursor: str | None = None) -> FetchResult:
        collected = datetime.now(timezone.utc).isoformat()
        items: list[RawItem] = []
        for market in self.markets:
            params = {}
            if market.get("id"):
                params["id"] = market["id"]
            elif market.get("slug"):
                params["slug"] = market["slug"]
            payload = fetch_json(self.endpoint, params=params or None)
            records = payload if isinstance(payload, list) else [payload]
            for record in records:
                market_id = str(record.get("id") or market.get("id") or market.get("slug") or len(items))
                question = record.get("question") or record.get("title") or market.get("label") or market_id
                outcome_prices = record.get("outcomePrices") or record.get("outcome_prices") or []
                yes_probability = None
                if isinstance(outcome_prices, list) and outcome_prices:
                    try:
                        yes_probability = float(outcome_prices[0])
                    except Exception:
                        yes_probability = outcome_prices[0]
                items.append(
                    RawItem(
                        source_id=self.source_id,
                        source_type=self.source_type,
                        external_id=market_id,
                        title=question,
                        url=record.get("url") or record.get("slug"),
                        summary=question,
                        collected_at_utc=collected,
                        published_at_utc=record.get("endDate") or record.get("end_date_iso"),
                        metadata={
                            "market_id": market_id,
                            "slug": record.get("slug"),
                            "yes_probability": yes_probability,
                            "active": record.get("active"),
                            "closed": record.get("closed"),
                            "source_config": market,
                        },
                    )
                )
        return FetchResult(items=items, next_cursor=collected, metadata={"endpoint": self.endpoint, "market_count": len(self.markets)})
