import json
import subprocess
import sys
import unittest
from pathlib import Path


class SourceRunnerE2E(unittest.TestCase):
    def test_watchlist_source_pack_runs_and_writes_runtime_artifact(self):
        repo = Path(__file__).resolve().parents[2]
        feed_path = repo / "tmp-test-watch-feed.xml"
        config_path = repo / "tmp-test-watch-pack.json"
        state_path = repo / "tmp-test-watch-state.json"
        runtime_path = repo / "lobster-intel" / "data" / "runtime" / "sources" / "watchlist-tracker" / "latest.json"
        runtime_runs_dir = repo / "lobster-intel" / "data" / "runtime" / "sources" / "watchlist-tracker" / "runs"
        prior_latest = runtime_path.read_text(encoding="utf-8") if runtime_path.exists() else None
        prior_run_paths = set(runtime_runs_dir.glob("*.json")) if runtime_runs_dir.exists() else set()
        prior_state = state_path.read_text(encoding="utf-8") if state_path.exists() else None
        try:
            feed_path.write_text(
                """<rss version=\"2.0\"><channel>
  <title>Watch Feed</title>
  <item>
    <title>Watch Test</title>
    <link>https://example.com/test</link>
    <description>Delta</description>
    <pubDate>Tue, 14 Apr 2026 09:00:00 GMT</pubDate>
    <guid>watch-test</guid>
  </item>
</channel></rss>
"""
            )
            config_path.write_text(
                json.dumps(
                    [
                        {
                            "source_id": "watch-test",
                            "url": f"file://{feed_path}",
                            "source_type": "analyst_feed",
                        }
                    ]
                )
            )
            output = subprocess.check_output(
                [
                    sys.executable,
                    "lobster-intel/scripts/run_source_plugin.py",
                    "lobster-intel/plugins/watchlist-tracker",
                    "--workspace",
                    ".",
                    "--config-file",
                    str(config_path),
                    "--state-path",
                    str(state_path),
                ],
                cwd=repo,
                text=True,
            )
            payload = json.loads(output)
            self.assertEqual(payload["plugin"], "watchlist-tracker")
            self.assertEqual(payload["new_count"], 1)
            self.assertIn("feeds", payload["normalized_config"])
            self.assertEqual(payload["normalized_config"]["state_path"], str(state_path))
            self.assertEqual(payload["state_path"], str(state_path))
            self.assertTrue(runtime_path.exists())
            self.assertTrue(runtime_runs_dir.exists())
            self.assertTrue(state_path.exists())
            self.assertTrue(payload["run_id"])
            self.assertTrue((repo / Path(payload["runtime_artifact_path"])).exists())
            self.assertEqual((repo / Path(payload["latest_runtime_artifact_path"])).resolve(), runtime_path.resolve())
            saved_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertIn("watch-test", saved_state["cursors"])
        finally:
            if feed_path.exists():
                feed_path.unlink()
            if config_path.exists():
                config_path.unlink()
            if prior_state is not None:
                state_path.write_text(prior_state, encoding="utf-8")
            elif state_path.exists():
                state_path.unlink()
            if prior_latest is not None:
                runtime_path.write_text(prior_latest, encoding="utf-8")
            elif runtime_path.exists():
                runtime_path.unlink()
            if runtime_runs_dir.exists():
                for run_path in runtime_runs_dir.glob("*.json"):
                    if run_path not in prior_run_paths:
                        run_path.unlink()


if __name__ == "__main__":
    unittest.main()
