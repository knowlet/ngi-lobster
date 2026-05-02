from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "lobster-intel" / "scripts" / "sync_standalone_runtime_monitor.py"
RELATIVE_PATHS = [
    (
        Path("packages/lobster-runtime/lobster_runtime/monitor.py"),
        Path("lobster-intel/packages/lobster-runtime/lobster_runtime/monitor.py"),
        "repo-monitor",
        "standalone-monitor",
    ),
    (
        Path("packages/lobster-runtime/lobster_runtime/runtime_spine.py"),
        Path("lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py"),
        "repo-runtime-spine",
        "standalone-runtime-spine",
    ),
    (
        Path("packages/lobster-delivery/lobster_delivery/dispatcher_artifacts.py"),
        Path("lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_artifacts.py"),
        "repo-dispatcher-artifacts",
        "standalone-dispatcher-artifacts",
    ),
    (
        Path("scripts/verify_runtime_ops_health.py"),
        Path("lobster-intel/scripts/verify_runtime_ops_health.py"),
        "repo-runtime-ops-health",
        "standalone-runtime-ops-health",
    ),
]


def _install_sync_fixture(tmp_path: Path) -> tuple[Path, Path]:
    repo_root = tmp_path / "repo"
    standalone_root = tmp_path / "workspace"
    for repo_rel, standalone_rel, repo_text, standalone_text in RELATIVE_PATHS:
        repo_path = repo_root / repo_rel
        standalone_path = standalone_root / standalone_rel
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        standalone_path.parent.mkdir(parents=True, exist_ok=True)
        repo_path.write_text(repo_text, encoding="utf-8")
        standalone_path.write_text(standalone_text, encoding="utf-8")
    return repo_root, standalone_root


def test_sync_monitor_check_mode_reports_all_drifted_paths(tmp_path: Path):
    repo_root, standalone_root = _install_sync_fixture(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--check",
            "--repo-root",
            str(repo_root),
            "--standalone-root",
            str(standalone_root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "runtime monitor" in result.stderr
    assert "runtime spine" in result.stderr
    assert "dispatcher artifacts" in result.stderr
    assert "runtime ops health verifier" in result.stderr


def test_sync_monitor_copies_repo_versions_into_override_standalone_root(tmp_path: Path):
    repo_root, standalone_root = _install_sync_fixture(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(repo_root),
            "--standalone-root",
            str(standalone_root),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "synced standalone runtime contract paths" in result.stdout
    for repo_rel, standalone_rel, repo_text, _ in RELATIVE_PATHS:
        assert (repo_root / repo_rel).read_text(encoding="utf-8") == repo_text
        assert (standalone_root / standalone_rel).read_text(encoding="utf-8") == repo_text
