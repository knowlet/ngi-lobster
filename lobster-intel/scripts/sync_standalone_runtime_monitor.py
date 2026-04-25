#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent.parent
SYNC_PATHS = (
    (
        ROOT / "packages" / "lobster-runtime" / "lobster_runtime" / "monitor.py",
        WORKSPACE_ROOT / "lobster-intel" / "packages" / "lobster-runtime" / "lobster_runtime" / "monitor.py",
        "runtime monitor",
    ),
    (
        ROOT / "packages" / "lobster-runtime" / "lobster_runtime" / "runtime_spine.py",
        WORKSPACE_ROOT / "lobster-intel" / "packages" / "lobster-runtime" / "lobster_runtime" / "runtime_spine.py",
        "runtime spine",
    ),
    (
        ROOT / "packages" / "lobster-delivery" / "lobster_delivery" / "dispatcher_artifacts.py",
        WORKSPACE_ROOT / "lobster-intel" / "packages" / "lobster-delivery" / "lobster_delivery" / "dispatcher_artifacts.py",
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
    return parser.parse_args()


def diff_label(repo_path: Path, standalone_path: Path, label: str) -> str:
    return f"{label}: {standalone_path} != {repo_path}"


def main() -> int:
    args = parse_args()
    diff_messages: list[str] = []

    for repo_path, standalone_path, label in SYNC_PATHS:
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
