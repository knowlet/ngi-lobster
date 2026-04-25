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

from lobster_delivery import build_alert_contract_view

P0_ALLOWED_REASON_CODES = {
    "legacy_target_mismatch",
    "suppressed_runtime_target_missing",
    "active_target_contract_ok",
    "explanation_or_target_changed",
    "ngi_changed_major",
}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: verify_latest_ngi_contract.py <latest_ngi.json>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    payload = json.loads(path.read_text())
    result = build_alert_contract_view(payload)

    issues: list[str] = []
    disposition_reason = ((payload.get("alert_disposition") or {}).get("reason_code"))
    explain_reason = ((payload.get("alert_explain_contract") or {}).get("reason_code"))

    if disposition_reason != explain_reason:
        issues.append("reason_code_mismatch:alert_disposition_vs_alert_explain_contract")
    if disposition_reason not in P0_ALLOWED_REASON_CODES:
        issues.append(f"reason_code_off_contract:{disposition_reason}")
    if explain_reason not in P0_ALLOWED_REASON_CODES:
        issues.append(f"explain_reason_code_off_contract:{explain_reason}")

    status = "ok" if result.get("status") == "ok" and not issues else "contract_violation"
    output = {
        "status": status,
        "path": str(path),
        "issues": issues,
        "alert_contract_view": result,
        "allowed_reason_codes": sorted(P0_ALLOWED_REASON_CODES),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
