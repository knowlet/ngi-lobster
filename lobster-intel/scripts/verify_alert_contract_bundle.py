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

from lobster_delivery import build_e2e_contract_bundle_view


def _load_payloads(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"unsupported JSON shape in {path}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: verify_alert_contract_bundle.py <payload.json|bundle.json> [more payloads...]",
            file=sys.stderr,
        )
        return 2

    payloads: list[dict] = []
    for raw_path in argv[1:]:
        path = Path(raw_path)
        payloads.extend(_load_payloads(path))

    result = build_e2e_contract_bundle_view(payloads)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
