import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in ["lobster-core", "lobster-plugins", "lobster-runtime", "lobster-ingest"]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_runtime import SourceFusionInput, build_source_fusion_result


class SourceFusionTest(unittest.TestCase):
    def test_source_fusion_combines_polymarket_official_and_watchlist_signals(self):
        result = build_source_fusion_result(
            SourceFusionInput(
                official_statements={
                    "ran_at_utc": "2026-04-15T00:00:00+00:00",
                    "evidence": {"items": [{"title": "Official Statement"}]},
                },
                watchlist={
                    "ran_at_utc": "2026-04-15T01:00:00+00:00",
                    "evidence": {"items": [{"title": "Watchlist Signal"}]},
                },
                polymarket={
                    "ran_at_utc": "2026-04-15T02:00:00+00:00",
                    "evidence": {
                        "items": [
                            {
                                "external_id": "1517836",
                                "title": "Trump announces end of military operations against Iran by June 30th?",
                                "url": "market-slug",
                                "metadata": {
                                    "market_id": "1517836",
                                    "slug": "market-slug",
                                    "yes_probability": 0.7,
                                    "active": True,
                                    "closed": False,
                                    "source_config": {"label": "Trump announces end of military operations against Iran by June 30th"},
                                },
                            }
                        ]
                    },
                },
            )
        )

        self.assertEqual(result.data["market_target"]["market_id"], "1517836")
        self.assertAlmostEqual(result.data["market_escalation_probability"], 0.3)
        self.assertAlmostEqual(result.data["first_principles_escalation_probability"], 0.7)
        self.assertTrue(result.data["gap_triggered"])
        self.assertEqual(result.data["decision"], "review_or_alert")


if __name__ == "__main__":
    unittest.main()
