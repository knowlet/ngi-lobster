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

from lobster_delivery import write_dispatcher_e2e_bundle


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--thesis-id", required=True)
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument("--run-id", action="append", dest="run_ids", required=True)
    args = parser.parse_args(argv[1:])

    result = write_dispatcher_e2e_bundle(
        workspace_dir=args.workspace,
        thesis_id=args.thesis_id,
        run_ids=args.run_ids,
        bundle_id=args.bundle_id,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
