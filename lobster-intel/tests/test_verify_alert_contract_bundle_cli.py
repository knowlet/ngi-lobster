import json
import subprocess
from pathlib import Path


def test_verify_alert_contract_bundle_cli_accepts_canonical_example_bundle():
    repo = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            str(repo / ".venv" / "bin" / "python"),
            "lobster-intel/scripts/verify_alert_contract_bundle.py",
            "lobster-intel/examples/e2e_alert_contract_bundle.json",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["bundle"]["e2e_run_id"] == "bundle-20260417-01"
    assert [fixture["decision"] for fixture in payload["bundle"]["fixtures"]] == [
        "suppressed",
        "would_send",
    ]
