#!/usr/bin/env python3
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent.parent
REPO_MONITOR_PATH = ROOT / "packages" / "lobster-runtime" / "lobster_runtime" / "monitor.py"
STANDALONE_MONITOR_PATH = WORKSPACE_ROOT / "lobster-intel" / "packages" / "lobster-runtime" / "lobster_runtime" / "monitor.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync the standalone workspace lobster-intel runtime monitor with the tracked ngi-lobster repo copy.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when the standalone workspace copy differs instead of overwriting it",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not REPO_MONITOR_PATH.exists():
        print(f"repo monitor missing: {REPO_MONITOR_PATH}", file=sys.stderr)
        return 2
    if not STANDALONE_MONITOR_PATH.parent.exists():
        print(f"standalone monitor parent missing: {STANDALONE_MONITOR_PATH.parent}", file=sys.stderr)
        return 2

    differs = not STANDALONE_MONITOR_PATH.exists() or not filecmp.cmp(
        REPO_MONITOR_PATH,
        STANDALONE_MONITOR_PATH,
        shallow=False,
    )

    if args.check:
        if differs:
            print(
                f"standalone runtime monitor differs: {STANDALONE_MONITOR_PATH} != {REPO_MONITOR_PATH}",
                file=sys.stderr,
            )
            return 1
        print(f"standalone runtime monitor already synced: {STANDALONE_MONITOR_PATH}")
        return 0

    shutil.copyfile(REPO_MONITOR_PATH, STANDALONE_MONITOR_PATH)
    print(f"synced standalone runtime monitor: {STANDALONE_MONITOR_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
