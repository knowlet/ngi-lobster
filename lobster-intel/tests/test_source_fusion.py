import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in ["lobster-core", "lobster-delivery", "lobster-ingest", "lobster-plugins", "lobster-runtime"]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_runtime import SourceFusionArtifacts, SourceFusionInput, build_source_fusion_result, load_source_fusion_artifacts


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
                firehose={
                    "run_id": "20260415T030500Z",
                    "ran_at_utc": "2026-04-15T03:00:00+00:00",
                    "evidence": {
                        "items": [
                            {
                                "title": "Firehose Event 1",
                                "published_at_utc": "2026-04-15T02:15:00+00:00",
                                "collected_at_utc": "2026-04-15T03:00:00+00:00",
                            },
                            {
                                "title": "Firehose Event 2",
                                "published_at_utc": "2026-04-15T02:45:00+00:00",
                                "collected_at_utc": "2026-04-15T03:05:00+00:00",
                            },
                        ]
                    },
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
        self.assertEqual(result.data["firehose"]["events_analyzed"], 2)
        self.assertEqual(result.data["firehose"]["source_run_id"], "20260415T030500Z")
        self.assertEqual(result.data["firehose"]["latest_event_at_utc"], "2026-04-15T02:45:00+00:00")
        self.assertEqual(result.data["firehose"]["latest_collected_at_utc"], "2026-04-15T03:05:00+00:00")
        self.assertAlmostEqual(result.data["market_escalation_probability"], 0.3)
        self.assertAlmostEqual(result.data["first_principles_escalation_probability"], 0.7)
        self.assertTrue(result.data["gap_triggered"])
        self.assertEqual(result.data["decision"], "review_or_alert")

    def test_load_source_fusion_artifacts_treats_missing_firehose_as_empty_payload(self):
        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            official_path = workspace / "official.json"
            watchlist_path = workspace / "watchlist.json"
            polymarket_path = workspace / "polymarket.json"
            firehose_path = workspace / "missing-firehose.json"

            official_path.write_text(
                json.dumps({"ran_at_utc": "2026-04-15T00:00:00+00:00", "evidence": {"items": [{"title": "Official"}]}}),
                encoding="utf-8",
            )
            watchlist_path.write_text(
                json.dumps({"ran_at_utc": "2026-04-15T01:00:00+00:00", "evidence": {"items": [{"title": "Watchlist"}]}}),
                encoding="utf-8",
            )
            polymarket_path.write_text(
                json.dumps(
                    {
                        "ran_at_utc": "2026-04-15T02:00:00+00:00",
                        "evidence": {
                            "items": [
                                {
                                    "external_id": "1517836",
                                    "title": "Market",
                                    "url": "market-slug",
                                    "metadata": {"market_id": "1517836", "slug": "market-slug", "yes_probability": 0.7},
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )

            loaded = load_source_fusion_artifacts(
                SourceFusionArtifacts(
                    official_statements_path=official_path,
                    watchlist_path=watchlist_path,
                    firehose_path=firehose_path,
                    polymarket_path=polymarket_path,
                )
            )

        self.assertIsNone(loaded.firehose)

    def test_build_source_fusion_cli_writes_output_when_firehose_artifact_is_missing(self):
        script_path = ROOT / "scripts" / "build_source_fusion.py"

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            official_path = workspace / "official.json"
            watchlist_path = workspace / "watchlist.json"
            polymarket_path = workspace / "polymarket.json"
            output_path = workspace / "fusion.json"
            missing_firehose_path = workspace / "firehose-latest.json"

            official_path.write_text(
                json.dumps({"ran_at_utc": "2026-04-15T00:00:00+00:00", "evidence": {"items": [{"title": "Official"}]}}),
                encoding="utf-8",
            )
            watchlist_path.write_text(
                json.dumps({"ran_at_utc": "2026-04-15T01:00:00+00:00", "evidence": {"items": [{"title": "Watchlist"}]}}),
                encoding="utf-8",
            )
            polymarket_path.write_text(
                json.dumps(
                    {
                        "ran_at_utc": "2026-04-15T02:00:00+00:00",
                        "evidence": {
                            "items": [
                                {
                                    "external_id": "1517836",
                                    "title": "Market",
                                    "url": "market-slug",
                                    "metadata": {"market_id": "1517836", "slug": "market-slug", "yes_probability": 0.7},
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--official",
                    str(official_path),
                    "--watchlist",
                    str(watchlist_path),
                    "--firehose",
                    str(missing_firehose_path),
                    "--polymarket",
                    str(polymarket_path),
                    "--output",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            summary = json.loads(completed.stdout)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["firehose_events_analyzed"], 0)
        self.assertIsNone(summary["firehose_source_run_id"])
        self.assertIsNone(summary["firehose_latest_event_at_utc"])
        self.assertIsNone(summary["firehose_latest_collected_at_utc"])
        self.assertEqual(payload["firehose"]["events_analyzed"], 0)
        self.assertIsNone(payload["firehose"]["source_run_id"])
        self.assertIsNone(payload["firehose"]["latest_event_at_utc"])
        self.assertIsNone(payload["firehose"]["latest_collected_at_utc"])


if __name__ == "__main__":
    unittest.main()
