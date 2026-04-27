import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "lobster-intel" / "scripts" / "read_state_field.py"


def test_read_state_field_cli_reads_quoted_scalar(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text('dq_status: "pass"\ncompleted_at: 2026-04-27T12:00:00Z\n', encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(state_path), "dq_status"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "pass"


def test_read_state_field_cli_errors_when_field_missing(tmp_path: Path):
    state_path = tmp_path / "STATE.yaml"
    state_path.write_text("report_date: 2026-04-27\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(state_path), "dq_status"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "field not found" in result.stderr
