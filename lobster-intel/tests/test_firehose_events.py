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

from lobster_runtime import replay_source_run


class FirehoseEventNormalizationTests(unittest.TestCase):
    def test_normalize_firehose_events_writes_replayable_source_run(self):
        from lobster_ingest import normalize_firehose_events

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            events_path = workspace / "events.jsonl"
            events_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "id": "fh-1",
                                "received_at_utc": "2026-04-22T00:00:00+00:00",
                                "title": "Airspace closed near border",
                                "url": "https://example.com/airspace",
                                "tags": ["middle-east", "airspace"],
                                "priority": "high",
                                "text": "Regional airspace restrictions expanded overnight.",
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "headline": "Negotiators return to talks",
                                "received_at_utc": "2026-04-22T00:05:00+00:00",
                                "tag": "ceasefire",
                                "summary": "Fresh talks resumed after overnight pressure.",
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = normalize_firehose_events(
                workspace_dir=workspace,
                input_file=events_path,
                run_id="20260422T000500Z",
                now_utc="2026-04-22T00:05:00+00:00",
            )

            artifact_path = workspace / result["artifact_path"]
            latest_path = (
                workspace
                / "lobster-intel"
                / "data"
                / "runtime"
                / "sources"
                / "firehose-tracker"
                / "latest.json"
            )
            state_path = (
                workspace
                / "lobster-intel"
                / "data"
                / "runtime"
                / "sources"
                / "firehose-tracker"
                / "state.json"
            )
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            artifact_exists = artifact_path.exists()
            latest_exists = latest_path.exists()
            state_exists = state_path.exists()

            replay = replay_source_run(workspace, "firehose-tracker", "20260422T000500Z")

        self.assertTrue(artifact_exists)
        self.assertTrue(latest_exists)
        self.assertTrue(state_exists)
        self.assertEqual(payload["plugin"], "firehose-tracker")
        self.assertEqual(payload["evidence"]["new_count"], 2)
        self.assertEqual(payload["normalization"]["line_count"], 2)
        self.assertEqual(payload["evidence"]["items"][0]["source_type"], "firehose_event")
        self.assertEqual(payload["evidence"]["items"][0]["tag"], "middle-east")
        self.assertEqual(payload["evidence"]["items"][1]["title"], "Negotiators return to talks")
        self.assertEqual(payload["evidence"]["items"][1]["tags"], ["ceasefire"])
        self.assertTrue(payload["evidence"]["items"][1]["external_id"])
        self.assertEqual(replay["plugin"], "firehose-tracker")
        self.assertEqual(replay["evidence_item_count"], 2)
        self.assertEqual(replay["items"][0]["external_id"], "fh-1")

    def test_normalize_firehose_events_cli_prints_summary(self):
        script_path = ROOT / "scripts" / "normalize_firehose_events.py"
        self.assertTrue(script_path.exists(), f"missing CLI script: {script_path}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            events_path = workspace / "events.jsonl"
            events_path.write_text(
                json.dumps(
                    {
                        "id": "fh-1",
                        "received_at_utc": "2026-04-22T00:00:00+00:00",
                        "title": "Airspace closed near border",
                        "tag": "middle-east",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--workspace",
                    str(workspace),
                    "--input-file",
                    str(events_path),
                    "--run-id",
                    "20260422T000000Z",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        summary = json.loads(completed.stdout)
        self.assertEqual(summary["plugin"], "firehose-tracker")
        self.assertEqual(summary["new_count"], 1)
        self.assertTrue(summary["artifact_path"].endswith("20260422T000000Z.json"))


if __name__ == "__main__":
    unittest.main()
