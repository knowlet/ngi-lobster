import json
import io
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

from lobster_ingest.linked_content import extract_linked_content, process_linked_content_queue


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


def _mock_response(body: bytes, *, content_type: str = "text/html; charset=utf-8") -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    response.read.return_value = body
    response.headers.get_content_type.return_value = content_type
    return response


class LinkedContentPlatformTests(unittest.TestCase):
    def test_extract_linked_content_rejects_file_urls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article_path = Path(temp_dir) / "article.html"
            article_path.write_text("<html><body>not allowed</body></html>", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unsupported URL scheme"):
                extract_linked_content(article_path.resolve().as_uri())

    def test_extract_linked_content_strips_script_and_style_content(self):
        response = _mock_response(
            b"""
            <html>
              <head>
                <title>Example Article</title>
                <style>body { color: red; }</style>
              </head>
              <body>
                <script>window.alert('noise');</script>
                <article>Signal <b>text</b></article>
              </body>
            </html>
            """
        )
        with patch("lobster_ingest.linked_content.urllib.request.urlopen", return_value=response):
            extracted = extract_linked_content("https://example.com/story")

        self.assertEqual(extracted["title"], "Example Article")
        self.assertIn("Signal text", extracted["content"])
        self.assertNotIn("window.alert", extracted["content"])
        self.assertNotIn("color: red", extracted["content"])

    def test_extract_linked_content_sets_user_agent_and_read_limit(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = b"plain text body"
        response.headers.get_content_type.return_value = "text/plain"

        with patch("lobster_ingest.linked_content.urllib.request.urlopen", return_value=response) as mock_urlopen:
            extracted = extract_linked_content("https://example.com/story")

        request = mock_urlopen.call_args.args[0]
        timeout = mock_urlopen.call_args.kwargs["timeout"]

        self.assertIsInstance(request, urllib.request.Request)
        self.assertIn("Mozilla/5.0", request.get_header("User-agent"))
        self.assertEqual(timeout, 15)
        response.read.assert_called_once_with(10_000_001)
        self.assertEqual(extracted["content"], "plain text body")

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

    def test_process_linked_content_queue_extracts_multiple_items_in_parallel(self):
        runtime_payload = {
            "run_id": "gooaye-20260420T000000Z",
            "linked_content_queue": [
                {
                    "post_id": str(index),
                    "url": f"https://t.me/gooaye/{index}",
                    "linked_url": f"https://example.com/story-{index}",
                    "site_name": "Example News",
                    "title": f"Story {index}",
                }
                for index in range(3)
            ],
        }
        barrier = threading.Barrier(3)
        thread_ids: list[int] = []

        def extractor(url: str) -> dict:
            thread_ids.append(threading.get_ident())
            barrier.wait(timeout=0.5)
            return {
                "url": url,
                "title": f"Title for {url}",
                "content": f"Body for {url}",
                "content_type": "text/plain",
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            result = process_linked_content_queue(
                workspace_dir=workspace,
                thesis_id="gooaye",
                runtime_payload=runtime_payload,
                extractor=extractor,
                now_utc="2026-04-20T00:00:00+00:00",
            )

            first_evidence = json.loads((workspace / result["evidence_paths"][0]).read_text(encoding="utf-8"))

        self.assertEqual(result["processed_count"], 3)
        self.assertNotIn("error", first_evidence["extracted"])
        self.assertGreater(len(set(thread_ids)), 1)

    def test_process_linked_content_queue_cli_reads_latest_runtime_artifact(self):
        repo = Path(__file__).resolve().parents[2]
        script_path = repo / "lobster-intel" / "scripts" / "process_linked_content_queue.py"
        self.assertTrue(script_path.exists(), f"missing CLI script: {script_path}")

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            runtime_dir = workspace / "lobster-intel" / "data" / "runtime" / "gooaye"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            latest_path = runtime_dir / "latest.json"
            latest_path.write_text(
                json.dumps(_runtime_payload("https://example.com/story"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            response = _mock_response(
                b"<html><head><title>CLI Article</title></head><body><article>CLI extracted body</article></body></html>"
            )
            old_argv = sys.argv
            try:
                sys.argv = [
                    str(script_path),
                    "--workspace",
                    str(workspace),
                    "--thesis-id",
                    "gooaye",
                ]
                with patch("urllib.request.urlopen", return_value=response):
                    with patch("sys.stdout", stdout):
                        namespace: dict[str, object] = {
                            "__name__": "__main__",
                            "__file__": str(script_path),
                        }
                        exec(script_path.read_text(encoding="utf-8"), namespace)
            finally:
                sys.argv = old_argv

            payload = json.loads(stdout.getvalue())

            self.assertEqual(payload["processed_count"], 1)
            self.assertEqual(payload["status"], "processed")
            self.assertTrue((workspace / payload["receipt_path"]).exists())


if __name__ == "__main__":
    unittest.main()
