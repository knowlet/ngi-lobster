import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in ["lobster-ingest"]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_ingest.adapters.polymarket import PolymarketAdapter, _infer_event_slug


class PolymarketAdapterTest(unittest.TestCase):
    def test_infers_event_slug_from_grouped_deadline_market_slug(self):
        self.assertEqual(
            _infer_event_slug(
                {
                    "slug": "trump-announces-end-of-military-operations-against-iran-by-june-30th-566-326-653-781-167-426-752-225-438",
                    "groupItemTitle": "June 30",
                }
            ),
            "trump-announces-end-of-military-operations-against-iran-by",
        )

    def test_fetch_expands_event_siblings_and_preserves_accepting_orders_false(self):
        calls = []

        def fake_fetch_json(url, *, params=None, headers=None, timeout=20):
            calls.append((url, params))
            if url.endswith("/markets/1517836"):
                return {
                    "id": "1517836",
                    "question": "Trump announces end of military operations against Iran by June 30th?",
                    "slug": "trump-announces-end-of-military-operations-against-iran-by-june-30th-566-326-653-781-167-426-752-225-438",
                    "groupItemTitle": "June 30",
                    "outcomePrices": '["1", "0"]',
                    "active": True,
                    "closed": True,
                    "acceptingOrders": False,
                }
            if url.endswith("/events") and params == {
                "closed": "true",
                "slug": "trump-announces-end-of-military-operations-against-iran-by",
            }:
                return [
                    {
                        "id": "236992",
                        "slug": "trump-announces-end-of-military-operations-against-iran-by",
                        "title": "Trump announces end of military operations against Iran by ...?",
                        "markets": [
                            {
                                "id": "1517836",
                                "question": "Trump announces end of military operations against Iran by June 30th?",
                                "slug": "closed-target",
                                "active": True,
                                "closed": True,
                                "acceptingOrders": False,
                            },
                            {
                                "id": "2000000",
                                "question": "Trump announces end of military operations against Iran by July 31st?",
                                "slug": "open-successor",
                                "outcomePrices": ["0.42", "0.58"],
                                "active": True,
                                "closed": False,
                                "acceptingOrders": True,
                            },
                        ],
                    }
                ]
            raise AssertionError((url, params))

        import lobster_ingest.adapters.polymarket as polymarket_module

        original_fetch_json = polymarket_module.fetch_json
        polymarket_module.fetch_json = fake_fetch_json
        try:
            result = PolymarketAdapter(markets=[{"id": "1517836", "label": "Current target"}]).fetch()
        finally:
            polymarket_module.fetch_json = original_fetch_json

        self.assertEqual([item.external_id for item in result.items], ["1517836", "2000000"])
        closed, successor = result.items
        self.assertIs(closed.metadata["accepting_orders"], False)
        self.assertEqual(closed.metadata["yes_probability"], 1.0)
        self.assertEqual(successor.metadata["relationship"], "event_sibling")
        self.assertEqual(successor.metadata["event_id"], "236992")
        self.assertEqual(successor.metadata["event_slug"], "trump-announces-end-of-military-operations-against-iran-by")
        self.assertIs(successor.metadata["closed"], False)
        self.assertIs(successor.metadata["accepting_orders"], True)
        self.assertEqual(successor.metadata["yes_probability"], 0.42)
        self.assertEqual(result.metadata["event_count"], 1)
        self.assertEqual(calls[1][1]["slug"], "trump-announces-end-of-military-operations-against-iran-by")

    def test_event_discovery_can_be_disabled(self):
        def fake_fetch_json(url, *, params=None, headers=None, timeout=20):
            if url.endswith("/markets/1517836"):
                return {
                    "id": "1517836",
                    "question": "Closed target",
                    "slug": "closed-target-june-30th",
                    "groupItemTitle": "June 30",
                    "closed": True,
                    "acceptingOrders": False,
                }
            raise AssertionError("event endpoint should not be called")

        import lobster_ingest.adapters.polymarket as polymarket_module

        original_fetch_json = polymarket_module.fetch_json
        polymarket_module.fetch_json = fake_fetch_json
        try:
            result = PolymarketAdapter(
                markets=[{"id": "1517836", "discover_event_markets": False}]
            ).fetch()
        finally:
            polymarket_module.fetch_json = original_fetch_json

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.metadata["event_count"], 0)


if __name__ == "__main__":
    unittest.main()
