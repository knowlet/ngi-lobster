import tempfile
import unittest
from pathlib import Path

from lobster_ingest.gooaye_pipeline import write_digest


class WriteDigestTests(unittest.TestCase):
    def test_write_digest_marks_truncated_summary_lists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            compiled_dir = Path(temp_dir) / "compiled"
            compiled_runs_dir = compiled_dir / "runs"
            compiled_runs_dir.mkdir(parents=True, exist_ok=True)

            _, digest_path, _ = write_digest(
                {"channel": "@Gooaye", "new_count": 12},
                [f"#{index} summary" for index in range(1, 6)],
                paths={"compiled": compiled_dir, "compiled_runs": compiled_runs_dir},
                recorded_at_utc="2026-04-19T14:00:00+00:00",
            )
            digest_text = digest_path.read_text()

        self.assertIn("- New count: 12", digest_text)
        self.assertIn("## New items (showing 5 of 12)", digest_text)


if __name__ == "__main__":
    unittest.main()
