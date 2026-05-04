import json
import os
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

    def test_source_fusion_prefers_open_accepting_market_candidate(self):
        result = build_source_fusion_result(
            SourceFusionInput(
                official_statements={"ran_at_utc": "2026-04-15T00:00:00+00:00", "evidence": {"items": []}},
                watchlist={"ran_at_utc": "2026-04-15T01:00:00+00:00", "evidence": {"items": []}},
                firehose=None,
                polymarket={
                    "ran_at_utc": "2026-04-15T02:00:00+00:00",
                    "evidence": {
                        "items": [
                            {
                                "external_id": "closed-legacy",
                                "title": "Closed market",
                                "url": "closed-market",
                                "collected_at_utc": "2026-04-15T02:00:00+00:00",
                                "metadata": {
                                    "market_id": "closed-legacy",
                                    "slug": "closed-market",
                                    "yes_probability": 1.0,
                                    "active": True,
                                    "closed": True,
                                    "accepting_orders": False,
                                    "source_config": {"label": "Closed market"},
                                },
                            },
                            {
                                "external_id": "open-successor",
                                "title": "Open successor market",
                                "url": "open-successor",
                                "collected_at_utc": "2026-04-15T02:01:00+00:00",
                                "metadata": {
                                    "market_id": "open-successor",
                                    "slug": "open-successor",
                                    "yes_probability": 0.42,
                                    "active": True,
                                    "closed": False,
                                    "accepting_orders": True,
                                    "source_config": {"label": "Open successor market"},
                                },
                            },
                        ]
                    },
                },
            )
        )

        self.assertEqual(result.data["market_target"]["market_id"], "open-successor")
        self.assertEqual(result.data["market_target"]["market_name"], "Open successor market")
        self.assertFalse(result.data["target_detail"]["market_closed"])
        self.assertTrue(result.data["target_detail"]["market_accepting_orders"])
        self.assertAlmostEqual(result.data["market_escalation_probability"], 0.58)

    def test_source_fusion_does_not_rank_ambiguous_accepting_orders_as_true(self):
        result = build_source_fusion_result(
            SourceFusionInput(
                official_statements={"ran_at_utc": "2026-04-15T00:00:00+00:00", "evidence": {"items": []}},
                watchlist={"ran_at_utc": "2026-04-15T01:00:00+00:00", "evidence": {"items": []}},
                firehose=None,
                polymarket={
                    "ran_at_utc": "2026-04-15T02:00:00+00:00",
                    "evidence": {
                        "items": [
                            {
                                "external_id": "ambiguous-successor",
                                "title": "Ambiguous successor market",
                                "url": "ambiguous-successor",
                                "collected_at_utc": "2026-04-15T02:05:00+00:00",
                                "metadata": {
                                    "market_id": "ambiguous-successor",
                                    "slug": "ambiguous-successor",
                                    "yes_probability": 0.39,
                                    "active": True,
                                    "closed": False,
                                    "accepting_orders": "unknown",
                                    "source_config": {"label": "Ambiguous successor market"},
                                },
                            },
                            {
                                "external_id": "open-successor",
                                "title": "Open successor market",
                                "url": "open-successor",
                                "collected_at_utc": "2026-04-15T02:01:00+00:00",
                                "metadata": {
                                    "market_id": "open-successor",
                                    "slug": "open-successor",
                                    "yes_probability": 0.42,
                                    "active": True,
                                    "closed": False,
                                    "accepting_orders": True,
                                    "source_config": {"label": "Open successor market"},
                                },
                            },
                        ]
                    },
                },
            )
        )

        self.assertEqual(result.data["market_target"]["market_id"], "open-successor")
        self.assertTrue(result.data["target_detail"]["market_accepting_orders"])

    def test_source_fusion_preserves_market_accepting_orders_flag(self):
        result = build_source_fusion_result(
            SourceFusionInput(
                official_statements={"ran_at_utc": "2026-04-15T00:00:00+00:00", "evidence": {"items": []}},
                watchlist={"ran_at_utc": "2026-04-15T01:00:00+00:00", "evidence": {"items": []}},
                firehose=None,
                polymarket={
                    "ran_at_utc": "2026-04-15T02:00:00+00:00",
                    "evidence": {
                        "items": [
                            {
                                "external_id": "1517836",
                                "title": "Market",
                                "url": "market-slug",
                                "metadata": {
                                    "market_id": "1517836",
                                    "slug": "market-slug",
                                    "yes_probability": 0.7,
                                    "active": True,
                                    "closed": False,
                                    "accepting_orders": False,
                                },
                            }
                        ]
                    },
                },
            )
        )

        self.assertIs(result.data["target_detail"]["market_accepting_orders"], False)


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

    def test_build_source_fusion_cli_resolves_tilde_paths_with_workspace_default(self):
        script_path = ROOT / "scripts" / "build_source_fusion.py"

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "workspace"
            runner_dir = Path(tmpdir) / "runner"
            home = Path(tmpdir) / "home"
            official_path = home / "official.json"
            watchlist_path = home / "watchlist.json"
            firehose_path = home / "firehose.json"
            polymarket_path = home / "polymarket.json"
            output_path = home / "fusion.json"

            workspace.mkdir()
            runner_dir.mkdir()
            home.mkdir()

            official_path.write_text(
                json.dumps({"ran_at_utc": "2026-04-15T00:00:00+00:00", "evidence": {"items": [{"title": "Official"}]}}),
                encoding="utf-8",
            )
            watchlist_path.write_text(
                json.dumps({"ran_at_utc": "2026-04-15T01:00:00+00:00", "evidence": {"items": [{"title": "Watchlist"}]}}),
                encoding="utf-8",
            )
            firehose_path.write_text(
                json.dumps(
                    {
                        "run_id": "20260423T010203Z",
                        "ran_at_utc": "2026-04-15T03:00:00+00:00",
                        "evidence": {"items": [{"title": "Firehose Event", "published_at_utc": "2026-04-15T02:45:00+00:00"}]},
                    }
                ),
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
                    "--workspace",
                    str(workspace),
                    "--official",
                    "~/official.json",
                    "--watchlist",
                    "~/watchlist.json",
                    "--firehose",
                    "~/firehose.json",
                    "--polymarket",
                    "~/polymarket.json",
                    "--output",
                    "~/fusion.json",
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=runner_dir,
                env={**os.environ, "HOME": str(home)},
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            summary = json.loads(completed.stdout)

        self.assertEqual(summary["output"], str(output_path))
        self.assertEqual(summary["firehose_source_run_id"], "20260423T010203Z")
        self.assertEqual(summary["firehose_events_analyzed"], 1)

    def test_build_source_fusion_cli_can_replay_historical_firehose_run(self):
        script_path = ROOT / "scripts" / "build_source_fusion.py"

        with TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            official_path = workspace / "official.json"
            watchlist_path = workspace / "watchlist.json"
            polymarket_path = workspace / "polymarket.json"
            output_path = workspace / "fusion.json"
            firehose_runs_dir = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "firehose-tracker" / "runs"
            firehose_runs_dir.mkdir(parents=True, exist_ok=True)
            firehose_run_id = "20260423T030500Z"
            firehose_run_path = firehose_runs_dir / f"{firehose_run_id}.json"

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
            firehose_run_path.write_text(
                json.dumps(
                    {
                        "plugin": "firehose-tracker",
                        "run_id": firehose_run_id,
                        "ran_at_utc": "2026-04-15T03:05:00+00:00",
                        "evidence": {
                            "items": [
                                {
                                    "source_id": "firehose",
                                    "source_type": "firehose_event",
                                    "external_id": "fh-1",
                                    "title": "Historical Firehose Event",
                                    "url": "https://example.test/firehose/1",
                                    "published_at_utc": "2026-04-15T02:55:00+00:00",
                                    "collected_at_utc": "2026-04-15T03:04:00+00:00",
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
                    "--workspace",
                    str(workspace),
                    "--official",
                    str(official_path),
                    "--watchlist",
                    str(watchlist_path),
                    "--firehose-run-id",
                    firehose_run_id,
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

        self.assertEqual(summary["firehose_events_analyzed"], 1)
        self.assertEqual(summary["firehose_source_run_id"], firehose_run_id)
        self.assertEqual(summary["firehose_latest_event_at_utc"], "2026-04-15T02:55:00+00:00")
        self.assertEqual(summary["firehose_latest_collected_at_utc"], "2026-04-15T03:04:00+00:00")
        self.assertEqual(payload["firehose"]["events_analyzed"], 1)
        self.assertEqual(payload["firehose"]["source_run_id"], firehose_run_id)
        self.assertEqual(payload["firehose"]["latest_event_at_utc"], "2026-04-15T02:55:00+00:00")
        self.assertEqual(payload["firehose"]["latest_collected_at_utc"], "2026-04-15T03:04:00+00:00")

    def test_build_source_fusion_cli_resolves_default_relative_paths_from_workspace(self):
        script_path = ROOT / "scripts" / "build_source_fusion.py"

        with TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            workspace = temp_root / "workspace"
            runner_dir = temp_root / "runner"
            official_path = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "official-statements-tracker" / "latest.json"
            watchlist_path = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "watchlist-tracker" / "latest.json"
            firehose_path = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "firehose-tracker" / "latest.json"
            polymarket_path = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "polymarket-tracker" / "latest.json"
            output_path = workspace / "lobster-intel" / "data" / "runtime" / "fusion" / "latest.json"

            official_path.parent.mkdir(parents=True, exist_ok=True)
            watchlist_path.parent.mkdir(parents=True, exist_ok=True)
            firehose_path.parent.mkdir(parents=True, exist_ok=True)
            polymarket_path.parent.mkdir(parents=True, exist_ok=True)
            runner_dir.mkdir(parents=True, exist_ok=True)

            official_path.write_text(
                json.dumps({"ran_at_utc": "2026-04-15T00:00:00+00:00", "evidence": {"items": [{"title": "Official"}]}}),
                encoding="utf-8",
            )
            watchlist_path.write_text(
                json.dumps({"ran_at_utc": "2026-04-15T01:00:00+00:00", "evidence": {"items": [{"title": "Watchlist"}]}}),
                encoding="utf-8",
            )
            firehose_path.write_text(
                json.dumps(
                    {
                        "run_id": "20260423T010203Z",
                        "ran_at_utc": "2026-04-15T03:00:00+00:00",
                        "evidence": {"items": [{"title": "Firehose Event", "published_at_utc": "2026-04-15T02:45:00+00:00"}]},
                    }
                ),
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
                    "--workspace",
                    str(workspace),
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=runner_dir,
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            summary = json.loads(completed.stdout)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["output"], str(output_path))
        self.assertEqual(summary["firehose_events_analyzed"], 1)
        self.assertEqual(summary["firehose_source_run_id"], "20260423T010203Z")
        self.assertEqual(payload["firehose"]["events_analyzed"], 1)
        self.assertEqual(payload["firehose"]["source_run_id"], "20260423T010203Z")

    def test_build_source_fusion_cli_resolves_workspace_with_tilde_home(self):
        script_path = ROOT / "scripts" / "build_source_fusion.py"

        with TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            home = temp_root / "home"
            workspace = home / "workspace"
            runner_dir = temp_root / "runner"
            official_path = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "official-statements-tracker" / "latest.json"
            watchlist_path = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "watchlist-tracker" / "latest.json"
            firehose_path = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "firehose-tracker" / "latest.json"
            polymarket_path = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "polymarket-tracker" / "latest.json"
            output_path = workspace / "lobster-intel" / "data" / "runtime" / "fusion" / "latest.json"

            official_path.parent.mkdir(parents=True, exist_ok=True)
            watchlist_path.parent.mkdir(parents=True, exist_ok=True)
            firehose_path.parent.mkdir(parents=True, exist_ok=True)
            polymarket_path.parent.mkdir(parents=True, exist_ok=True)
            runner_dir.mkdir(parents=True, exist_ok=True)

            official_path.write_text(
                json.dumps({"ran_at_utc": "2026-04-15T00:00:00+00:00", "evidence": {"items": [{"title": "Official"}]}}),
                encoding="utf-8",
            )
            watchlist_path.write_text(
                json.dumps({"ran_at_utc": "2026-04-15T01:00:00+00:00", "evidence": {"items": [{"title": "Watchlist"}]}}),
                encoding="utf-8",
            )
            firehose_path.write_text(
                json.dumps(
                    {
                        "run_id": "20260423T010203Z",
                        "ran_at_utc": "2026-04-15T03:00:00+00:00",
                        "evidence": {"items": [{"title": "Firehose Event", "published_at_utc": "2026-04-15T02:45:00+00:00"}]},
                    }
                ),
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
                    "--workspace",
                    "~/workspace",
                ],
                capture_output=True,
                text=True,
                check=False,
                cwd=runner_dir,
                env={**os.environ, "HOME": str(home)},
            )

            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            summary = json.loads(completed.stdout)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["output"], str(output_path))
        self.assertEqual(summary["firehose_events_analyzed"], 1)
        self.assertEqual(summary["firehose_source_run_id"], "20260423T010203Z")
        self.assertEqual(payload["firehose"]["events_analyzed"], 1)
        self.assertEqual(payload["firehose"]["source_run_id"], "20260423T010203Z")


if __name__ == "__main__":
    unittest.main()
