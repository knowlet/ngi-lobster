#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE_ROOT = ROOT.parent.parent
RELATIVE_SYNC_PATHS = (
    (
        Path("packages/lobster-runtime/lobster_runtime/monitor.py"),
        Path("lobster-intel/packages/lobster-runtime/lobster_runtime/monitor.py"),
        "runtime monitor",
    ),
    (
        Path("packages/lobster-runtime/lobster_runtime/runtime_spine.py"),
        Path("lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py"),
        "runtime spine",
    ),
    (
        Path("packages/lobster-delivery/lobster_delivery/dispatcher_artifacts.py"),
        Path("lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_artifacts.py"),
        "dispatcher artifacts",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sync the standalone workspace lobster-intel runtime/dispatcher contract paths "
            "with the tracked ngi-lobster repo copies."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when any standalone workspace copy differs instead of overwriting it",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=ROOT,
        help="override the tracked ngi-lobster repo root (defaults to this script's repo)",
    )
    parser.add_argument(
        "--standalone-root",
        type=Path,
        default=DEFAULT_WORKSPACE_ROOT,
        help="override the standalone workspace root that contains lobster-intel/",
    )
    return parser.parse_args()


def build_sync_paths(repo_root: Path, standalone_root: Path) -> tuple[tuple[Path, Path, str], ...]:
    return tuple(
        (
            repo_root / repo_rel,
            standalone_root / standalone_rel,
            label,
        )
        for repo_rel, standalone_rel, label in RELATIVE_SYNC_PATHS
    )


def diff_label(repo_path: Path, standalone_path: Path, label: str) -> str:
    return f"{label}: {standalone_path} != {repo_path}"


def main() -> int:
    args = parse_args()
    diff_messages: list[str] = []
    sync_paths = build_sync_paths(
        repo_root=args.repo_root.resolve(),
        standalone_root=args.standalone_root.resolve(),
    )

    for repo_path, standalone_path, label in sync_paths:
        if not repo_path.exists():
            print(f"repo path missing for {label}: {repo_path}", file=sys.stderr)
            return 2
        if not standalone_path.parent.exists():
            print(f"standalone path parent missing for {label}: {standalone_path.parent}", file=sys.stderr)
            return 2

        differs = not standalone_path.exists() or not filecmp.cmp(
            repo_path,
            standalone_path,
            shallow=False,
        )
        if differs:
            diff_messages.append(diff_label(repo_path, standalone_path, label))
            if not args.check:
                shutil.copyfile(repo_path, standalone_path)

    if args.check:
        if diff_messages:
            print("standalone runtime contract paths differ:", file=sys.stderr)
            for message in diff_messages:
                print(f"- {message}", file=sys.stderr)
            return 1
        print("standalone runtime contract paths already synced")
        return 0

    if diff_messages:
        print("synced standalone runtime contract paths:")
        for message in diff_messages:
            print(f"- {message}")
        return 0

    print("standalone runtime contract paths already synced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
