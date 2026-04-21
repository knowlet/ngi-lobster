import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in ["lobster-ingest"]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_ingest.gooaye_pipeline import process_gooaye_payload


class GooayePipelineTests(unittest.TestCase):
    def test_process_gooaye_payload_removes_stale_delivery_artifact_when_no_new_items(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            delivery_path = workspace / "lobster-intel" / "data" / "delivery" / "gooaye" / "latest.json"
            delivery_path.parent.mkdir(parents=True, exist_ok=True)
            delivery_path.write_text(
                json.dumps({"message": "stale delivery"}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            result = process_gooaye_payload(
                {
                    "channel": "@Gooaye",
                    "new_count": 0,
                    "items": [],
                },
                ctx=SimpleNamespace(workspace_dir=workspace),
            )

            self.assertEqual(result["message"], "NO_REPLY")
            self.assertFalse(delivery_path.exists())


if __name__ == "__main__":
    unittest.main()
