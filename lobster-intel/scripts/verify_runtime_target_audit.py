#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for package_dir in (
    ROOT / "packages" / "lobster-core",
    ROOT / "packages" / "lobster-delivery",
    ROOT / "packages" / "lobster-ingest",
    ROOT / "packages" / "lobster-plugins",
    ROOT / "packages" / "lobster-runtime",
):
    sys.path.insert(0, str(package_dir))

from lobster_delivery import load_runtime_target_audit


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Verify that one runtime run still matches the latest runtime active target contract."
    )
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--thesis-id", required=True)
    ap.add_argument("--run-id", required=True)
    args = ap.parse_args(argv[1:])

    result = load_runtime_target_audit(args.workspace, args.thesis_id, args.run_id)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
