import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in ["lobster-ingest"]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_ingest.visual_evidence import process_visual_evidence_queue


def _runtime_payload(image_url: str | None = "https://example.com/chart.png") -> dict:
    queue = []
    if image_url is not None:
        queue.append(
            {
                "post_id": "6059",
                "url": "https://t.me/gooaye/6059",
                "image_url": image_url,
            }
        )

    return {
        "run_id": "gooaye-20260421T000000Z",
        "image_analysis_queue": queue,
    }


class VisualEvidencePlatformTests(unittest.TestCase):
    def test_process_visual_evidence_queue_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            result = process_visual_evidence_queue(
                workspace_dir=workspace,
                thesis_id="gooaye",
                runtime_payload=_runtime_payload(),
                ocr_adapter=lambda item: {
                    "image_url": item["image_url"],
                    "ocr_text": "Feature FSD US FSD Europe Netherlands",
                    "summary": "Comparison chart between US and EU FSD features",
                },
                now_utc="2026-04-21T00:00:00+00:00",
            )

            evidence_path = workspace / result["evidence_paths"][0]
            compiled_path = workspace / result["compiled_paths"][0]
            receipt_path = workspace / result["receipt_path"]
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            evidence_exists = evidence_path.exists()
            compiled_exists = compiled_path.exists()
            receipt_exists = receipt_path.exists()

        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["processed_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["error_count"], 0)
        self.assertTrue(evidence_exists)
        self.assertTrue(compiled_exists)
        self.assertTrue(receipt_exists)
        self.assertEqual(evidence["image_item"]["post_id"], "6059")
        self.assertEqual(evidence["ocr"]["summary"], "Comparison chart between US and EU FSD features")
        self.assertEqual(receipt["source_run_id"], "gooaye-20260421T000000Z")
        self.assertEqual(receipt["success_count"], 1)
        self.assertEqual(receipt["error_count"], 0)

    def test_process_visual_evidence_queue_records_empty_receipt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            result = process_visual_evidence_queue(
                workspace_dir=workspace,
                thesis_id="gooaye",
                runtime_payload=_runtime_payload(image_url=None),
                ocr_adapter=lambda item: {},
                now_utc="2026-04-21T00:00:00+00:00",
            )

            receipt_path = workspace / result["receipt_path"]
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "no_items")
        self.assertEqual(result["processed_count"], 0)
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(result["evidence_paths"], [])
        self.assertEqual(receipt["status"], "no_items")
        self.assertEqual(receipt["processed_count"], 0)
        self.assertEqual(receipt["success_count"], 0)
        self.assertEqual(receipt["error_count"], 0)

    def test_process_visual_evidence_queue_fails_closed_when_image_url_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            result = process_visual_evidence_queue(
                workspace_dir=workspace,
                thesis_id="gooaye",
                runtime_payload={
                    "run_id": "gooaye-20260421T000000Z",
                    "image_analysis_queue": [
                        {
                            "post_id": "6060",
                            "url": "https://t.me/gooaye/6060",
                            "image_url": "",
                        }
                    ],
                },
                ocr_adapter=lambda item: {"summary": "should not be used"},
                now_utc="2026-04-21T00:00:00+00:00",
            )

            evidence = json.loads((workspace / result["evidence_paths"][0]).read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["processed_count"], 1)
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["error_count"], 1)
        self.assertEqual(evidence["ocr"]["error"], "missing image_url")
        self.assertEqual(evidence["ocr"]["ocr_text"], "")

    def test_process_visual_evidence_queue_processes_multiple_items_in_parallel(self):
        runtime_payload = {
            "run_id": "gooaye-20260421T000000Z",
            "image_analysis_queue": [
                {
                    "post_id": str(index),
                    "url": f"https://t.me/gooaye/{index}",
                    "image_url": f"https://example.com/chart-{index}.png",
                }
                for index in range(3)
            ],
        }
        barrier = threading.Barrier(3)
        thread_ids: list[int] = []

        def ocr_adapter(item: dict[str, object]) -> dict[str, object]:
            thread_ids.append(threading.get_ident())
            barrier.wait(timeout=0.5)
            return {
                "image_url": item["image_url"],
                "ocr_text": f"OCR for {item['image_url']}",
                "summary": f"Summary for {item['post_id']}",
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            result = process_visual_evidence_queue(
                workspace_dir=workspace,
                thesis_id="gooaye",
                runtime_payload=runtime_payload,
                ocr_adapter=ocr_adapter,
                now_utc="2026-04-21T00:00:00+00:00",
            )

            first_evidence = json.loads((workspace / result["evidence_paths"][0]).read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "processed")
        self.assertEqual(result["processed_count"], 3)
        self.assertEqual(result["success_count"], 3)
        self.assertEqual(result["error_count"], 0)
        self.assertEqual(first_evidence["image_item"]["post_id"], "0")
        self.assertGreater(len(set(thread_ids)), 1)

    def test_process_visual_evidence_queue_cli_reads_latest_runtime_artifact(self):
        repo = Path(__file__).resolve().parents[2]
        script_path = repo / "lobster-intel" / "scripts" / "process_visual_evidence_queue.py"
        self.assertTrue(script_path.exists(), f"missing CLI script: {script_path}")

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            runtime_dir = workspace / "lobster-intel" / "data" / "runtime" / "gooaye"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            latest_path = runtime_dir / "latest.json"
            latest_path.write_text(
                json.dumps(_runtime_payload("https://example.com/chart.png"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            old_argv = sys.argv
            try:
                sys.argv = [
                    str(script_path),
                    "--workspace",
                    str(workspace),
                    "--thesis-id",
                    "gooaye",
                ]
                with patch("lobster_ingest.visual_evidence.ocr_image", return_value={
                    "image_url": "https://example.com/chart.png",
                    "ocr_text": "CLI OCR body",
                    "summary": "CLI OCR summary",
                }):
                    with patch("sys.stdout", stdout):
                        namespace: dict[str, object] = {
                            "__name__": "__main__",
                            "__file__": str(script_path),
                        }
                        exec(script_path.read_text(encoding="utf-8"), namespace)
            finally:
                sys.argv = old_argv

            payload = json.loads(stdout.getvalue())
            receipt_exists = (workspace / payload["receipt_path"]).exists()

        self.assertEqual(payload["status"], "processed")
        self.assertEqual(payload["processed_count"], 1)
        self.assertEqual(payload["success_count"], 1)
        self.assertEqual(payload["error_count"], 0)
        self.assertTrue(receipt_exists)


if __name__ == "__main__":
    unittest.main()
