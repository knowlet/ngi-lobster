#!/usr/bin/env python3
from __future__ import annotations

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

from lobster_delivery import build_active_target_compare_view


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: render_active_target_compare.py <runtime-payload.json>", file=sys.stderr)
        return 2

    payload = json.loads(Path(argv[1]).read_text())
    result = build_active_target_compare_view(payload)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
