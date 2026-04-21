import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class SourceRunnerE2E(unittest.TestCase):
    def test_watchlist_source_pack_runs_and_writes_runtime_artifact(self):
        repo = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            feed_path = workspace / "tmp-test-watch-feed.xml"
            config_path = workspace / "tmp-test-watch-pack.json"
            runtime_path = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "watchlist-tracker" / "latest.json"
            runtime_runs_dir = workspace / "lobster-intel" / "data" / "runtime" / "sources" / "watchlist-tracker" / "runs"

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
                    str(repo / ".venv" / "bin" / "python"),
                    "lobster-intel/scripts/run_source_plugin.py",
                    "lobster-intel/plugins/watchlist-tracker",
                    "--workspace",
                    str(workspace),
                    "--config-file",
                    str(config_path),
                ],
                cwd=repo,
                text=True,
            )
            payload = json.loads(output)
            self.assertEqual(payload["plugin"], "watchlist-tracker")
            self.assertEqual(payload["new_count"], 1)
            self.assertIn("feeds", payload["normalized_config"])
            self.assertTrue(runtime_path.exists())
            self.assertTrue(runtime_runs_dir.exists())
            self.assertTrue(payload["run_id"])
            self.assertTrue((workspace / Path(payload["runtime_artifact_path"])).exists())
            self.assertEqual((workspace / Path(payload["latest_runtime_artifact_path"])).resolve(), runtime_path.resolve())


if __name__ == "__main__":
    unittest.main()
