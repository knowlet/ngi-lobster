import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "process_gooaye_channel.py"
SPEC = importlib.util.spec_from_file_location("process_gooaye_channel", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WriteDigestTests(unittest.TestCase):
    def test_write_digest_marks_truncated_summary_lists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_compiled_dir = MODULE.COMPILED_DIR
            MODULE.COMPILED_DIR = Path(temp_dir)
            try:
                digest_path = MODULE.write_digest(
                    {"channel": "@Gooaye", "new_count": 12},
                    [f"#{index} summary" for index in range(1, 6)],
                )
                digest_text = digest_path.read_text()
            finally:
                MODULE.COMPILED_DIR = original_compiled_dir

        self.assertIn("- New count: 12", digest_text)
        self.assertIn("## New items (showing 5 of 12)", digest_text)


if __name__ == "__main__":
    unittest.main()
