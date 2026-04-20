import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lobster_ingest.linked_content import process_linked_content_queue


def _runtime_payload(linked_url: str | None = "https://example.com/story") -> dict:
    queue = []
    if linked_url is not None:
        queue.append(
            {
                "post_id": "101",
                "url": "https://t.me/gooaye/101",
                "linked_url": linked_url,
                "site_name": "Example News",
                "title": "Example Story",
            }
        )

    return {
        "run_id": "gooaye-20260420T000000Z",
        "linked_content_queue": queue,
    }


class LinkedContentPlatformTests(unittest.TestCase):
    def test_process_linked_content_queue_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            result = process_linked_content_queue(
                workspace_dir=workspace,
                thesis_id="gooaye",
                runtime_payload=_runtime_payload(),
                extractor=lambda url: {
                    "url": url,
                    "title": "Example Story",
                    "content": "Full article body",
                },
                now_utc="2026-04-20T00:00:00+00:00",
            )

            evidence_path = workspace / result["evidence_paths"][0]
            compiled_path = workspace / result["compiled_paths"][0]
            receipt_path = workspace / result["receipt_path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence_exists = evidence_path.exists()
            compiled_exists = compiled_path.exists()
            receipt_exists = receipt_path.exists()

        self.assertEqual(result["processed_count"], 1)
        self.assertEqual(result["status"], "processed")
        self.assertTrue(evidence_exists)
        self.assertTrue(compiled_exists)
        self.assertTrue(receipt_exists)
        self.assertEqual(evidence["linked_item"]["post_id"], "101")
        self.assertEqual(evidence["extracted"]["content"], "Full article body")
        self.assertEqual(receipt["processed_count"], 1)
        self.assertEqual(receipt["source_run_id"], "gooaye-20260420T000000Z")

    def test_process_linked_content_queue_records_empty_receipt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            result = process_linked_content_queue(
                workspace_dir=workspace,
                thesis_id="gooaye",
                runtime_payload=_runtime_payload(linked_url=None),
                extractor=lambda url: {},
                now_utc="2026-04-20T00:00:00+00:00",
            )

            receipt_path = workspace / result["receipt_path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

        self.assertEqual(result["processed_count"], 0)
        self.assertEqual(result["status"], "no_items")
        self.assertEqual(result["evidence_paths"], [])
        self.assertEqual(receipt["processed_count"], 0)
        self.assertEqual(receipt["status"], "no_items")

    def test_process_linked_content_queue_cli_reads_latest_runtime_artifact(self):
        repo = Path(__file__).resolve().parents[2]
        script_path = repo / "lobster-intel" / "scripts" / "process_linked_content_queue.py"
        self.assertTrue(script_path.exists(), f"missing CLI script: {script_path}")

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            article_path = workspace / "article.html"
            article_path.write_text(
                "<html><head><title>CLI Article</title></head><body><article>CLI extracted body</article></body></html>",
                encoding="utf-8",
            )

            runtime_dir = workspace / "lobster-intel" / "data" / "runtime" / "gooaye"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            latest_path = runtime_dir / "latest.json"
            latest_path.write_text(
                json.dumps(_runtime_payload(article_path.resolve().as_uri()), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    "--workspace",
                    str(workspace),
                    "--thesis-id",
                    "gooaye",
                ],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)

            self.assertEqual(payload["processed_count"], 1)
            self.assertEqual(payload["status"], "processed")
            self.assertTrue((workspace / payload["receipt_path"]).exists())


if __name__ == "__main__":
    unittest.main()
