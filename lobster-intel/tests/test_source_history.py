from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in [
    "lobster-core",
    "lobster-delivery",
    "lobster-ingest",
    "lobster-plugins",
    "lobster-runtime",
]:
    sys.path.insert(0, str(PACKAGES / rel))

import lobster_runtime
import lobster_runtime.source_history as source_history


def _write_run_artifact(workspace: Path, plugin_id: str, run_id: str, ran_at_utc: str, items: list[dict], new_count: int) -> None:
    runtime_dir = workspace / "lobster-intel" / "data" / "runtime" / "sources" / plugin_id
    runs_dir = runtime_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "v1",
        "plugin": plugin_id,
        "version": "0.1.0",
        "run_id": run_id,
        "ran_at_utc": ran_at_utc,
        "evidence": {
            "new_count": new_count,
            "state_path": f"{runtime_dir}/state.json",
            "items": items,
        },
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (runs_dir / f"{run_id}.json").write_text(encoded, encoding="utf-8")
    (runtime_dir / "latest.json").write_text(encoded, encoding="utf-8")


def _install_source_history_fixture(workspace: Path) -> tuple[str, str]:
    plugin_id = "watchlist-tracker"
    _write_run_artifact(
        workspace,
        plugin_id,
        "20260420T010000Z",
        "2026-04-20T01:00:00+00:00",
        [
            {
                "source_id": "watch-a",
                "source_type": "analyst_watchlist",
                "external_id": "stmt-1",
                "title": "First watch item",
                "url": "https://example.com/stmt-1",
                "published_at_utc": "2026-04-20T00:55:00+00:00",
                "collected_at_utc": "2026-04-20T01:00:00+00:00",
            },
            {
                "source_id": "watch-b",
                "source_type": "analyst_watchlist",
                "external_id": "stmt-2",
                "title": "Second watch item",
                "url": "https://example.com/stmt-2",
                "published_at_utc": "2026-04-20T00:57:00+00:00",
                "collected_at_utc": "2026-04-20T01:00:00+00:00",
            },
        ],
        2,
    )
    _write_run_artifact(
        workspace,
        plugin_id,
        "20260420T020000Z",
        "2026-04-20T02:00:00+00:00",
        [
            {
                "source_id": "watch-c",
                "source_type": "analyst_watchlist",
                "external_id": "stmt-3",
                "title": "Third watch item",
                "url": "https://example.com/stmt-3",
                "published_at_utc": "2026-04-20T01:58:00+00:00",
                "collected_at_utc": "2026-04-20T02:00:00+00:00",
            }
        ],
        1,
    )
    return plugin_id, "20260420T010000Z"


class SourceHistoryTests(unittest.TestCase):
    def test_source_history_rejects_unsafe_plugin_ids(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            with self.assertRaises(ValueError):
                source_history.replay_source_run(workspace, "../escape", "20260420T010000Z")

    def test_source_index_path_is_pure_and_does_not_create_directories(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            index_path = source_history._source_index_path(workspace, "watchlist-tracker")
            expected = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "watchlist-tracker" / "index.sqlite"

            self.assertEqual(index_path, expected)
            self.assertFalse(index_path.parent.exists())

    def test_replay_source_run_returns_historical_payload(self):
        replay_source_run = getattr(lobster_runtime, "replay_source_run", None)
        self.assertIsNotNone(replay_source_run, "lobster_runtime.replay_source_run should exist")

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            plugin_id, run_id = _install_source_history_fixture(workspace)
            replay = replay_source_run(workspace, plugin_id, run_id)

        self.assertEqual(replay["plugin"], plugin_id)
        self.assertEqual(replay["run_id"], run_id)
        self.assertEqual(replay["evidence_item_count"], 2)
        self.assertEqual(replay["new_count"], 2)
        self.assertTrue(replay["artifact_path"].endswith(f"{run_id}.json"))
        self.assertTrue(replay["state_path"].endswith(f"{plugin_id}/state.json"))
        self.assertEqual(replay["items"][0]["external_id"], "stmt-1")
        self.assertEqual(replay["items"][1]["title"], "Second watch item")

    def test_rebuild_source_index_recreates_sqlite_rows(self):
        rebuild_source_index = getattr(lobster_runtime, "rebuild_source_index", None)
        self.assertIsNotNone(rebuild_source_index, "lobster_runtime.rebuild_source_index should exist")

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            plugin_id, _ = _install_source_history_fixture(workspace)
            rebuilt = rebuild_source_index(workspace, plugin_id)

        self.assertTrue(rebuilt["index_path"].endswith("index.sqlite"))
        self.assertEqual(rebuilt["plugin"], plugin_id)
        self.assertEqual(rebuilt["run_count"], 2)
        self.assertEqual(rebuilt["item_count"], 3)

    def test_source_history_cli_supports_replay_and_rebuild(self):
        script_path = ROOT / "scripts" / "source_history.py"
        self.assertTrue(script_path.exists(), f"missing CLI script: {script_path}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            plugin_id, run_id = _install_source_history_fixture(workspace)
            replay = json.loads(
                subprocess.check_output(
                    [
                        sys.executable,
                        str(script_path),
                        "replay",
                        "--workspace",
                        str(workspace),
                        "--plugin-id",
                        plugin_id,
                        "--run-id",
                        run_id,
                    ],
                    text=True,
                )
            )
            rebuilt = json.loads(
                subprocess.check_output(
                    [
                        sys.executable,
                        str(script_path),
                        "rebuild-index",
                        "--workspace",
                        str(workspace),
                        "--plugin-id",
                        plugin_id,
                    ],
                    text=True,
                )
            )

        self.assertEqual(replay["run_id"], run_id)
        self.assertEqual(replay["evidence_item_count"], 2)
        self.assertEqual(rebuilt["run_count"], 2)
        self.assertEqual(rebuilt["item_count"], 3)


if __name__ == "__main__":
    unittest.main()
