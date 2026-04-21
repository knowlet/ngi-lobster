from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[2]


def _prepare_isolated_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "lobster-intel" / "scripts").mkdir(parents=True)

    shutil.copy2(ROOT / "scripts" / "run_default_workflow.sh", repo / "scripts" / "run_default_workflow.sh")
    shutil.copytree(ROOT / "lobster-intel" / "scripts", repo / "lobster-intel" / "scripts", dirs_exist_ok=True)
    shutil.copytree(ROOT / "lobster-intel" / "data" / "runtime", repo / "lobster-intel" / "data" / "runtime", dirs_exist_ok=True)
    shutil.copytree(ROOT / "lobster-intel" / "packages", repo / "lobster-intel" / "packages", dirs_exist_ok=True)
    shutil.copytree(ROOT / "lobster-intel" / "examples", repo / "lobster-intel" / "examples", dirs_exist_ok=True)

    venv_python = repo / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True, exist_ok=True)
    if not venv_python.exists():
        venv_python.symlink_to(Path(sys.executable))

    track_stub = dedent(
        """
        #!/usr/bin/env python3
        from __future__ import annotations

        import argparse
        import json

        ap = argparse.ArgumentParser()
        ap.add_argument("channel")
        ap.add_argument("--state")
        ap.add_argument("--limit", type=int, default=5)
        ap.add_argument("--init", action="store_true")
        ap.parse_args()

        print(
            json.dumps(
                {
                    "status": "updated",
                    "channel": "@Gooaye",
                    "new_count": 0,
                    "items": [],
                },
                ensure_ascii=False,
            )
        )
        """
    ).strip()
    (repo / "lobster-intel" / "scripts" / "track_telegram_channel.py").write_text(track_stub + "\n", encoding="utf-8")

    return repo


def test_default_workflow_runs_thesis_runtime_spine(tmp_path: Path):
    repo = _prepare_isolated_repo(tmp_path)

    result = subprocess.run(
        ["bash", str(repo / "scripts" / "run_default_workflow.sh")],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PATH": os.environ.get("PATH", "")},
    )

    assert result.returncode == 0, result.stderr

    payload = json.loads(result.stdout)
    assert payload["compare_mode"] == "full_compare"
    assert payload["input_contract"]["source_resolution"]["official_statements"]["mode"] == "discovered"
    assert payload["input_contract"]["source_resolution"]["watchlist"]["mode"] == "discovered"
    assert payload["input_contract"]["source_resolution"]["polymarket"]["mode"] == "discovered"
    assert payload["input_contract"]["registry_resolution"]["mode"] == "discovered"
    assert payload["input_contract"]["registry_resolution"]["path"].endswith(
        "lobster-intel/data/runtime/thesis-registry/gooaye.json"
    )
    assert payload["input_contract"]["thesis_pack_resolution"]["mode"] == "discovered"
    assert Path(payload["artifact_paths"]["runtime_latest"]).exists()
    assert Path(payload["artifact_paths"]["delivery_receipt"]).exists()
    assert Path(payload["artifact_paths"]["latest_digest"]).exists()
