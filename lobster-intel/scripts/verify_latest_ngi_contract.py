#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent.parent
DEFAULT_LATEST_NGI_PATH = WORKSPACE_ROOT / "shared-projects" / "intelligence-model" / "latest_ngi.json"
STANDALONE_MONITOR_PATH = WORKSPACE_ROOT / "lobster-intel" / "packages" / "lobster-runtime" / "lobster_runtime" / "monitor.py"
STALE_REASON_CODE = "target_contract_market_slug_mismatch"
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


def resolve_latest_ngi_path(argv: list[str]) -> Path:
    if len(argv) == 2:
        return Path(argv[1])
    if len(argv) == 1:
        return Path(os.environ.get("LOBSTER_LATEST_NGI_PATH", DEFAULT_LATEST_NGI_PATH))
    print("usage: verify_latest_ngi_contract.py [latest_ngi.json]", file=sys.stderr)
    raise SystemExit(2)


def detect_probable_sync_blocker() -> dict[str, object] | None:
    if not STANDALONE_MONITOR_PATH.exists():
        return None

    content = STANDALONE_MONITOR_PATH.read_text(encoding="utf-8")
    stale_reason_present = STALE_REASON_CODE in content
    on_contract_reason_present = "legacy_target_mismatch" in content

    if not stale_reason_present:
        return None

    return {
        "kind": "standalone_workspace_runtime_copy_stale",
        "path": str(STANDALONE_MONITOR_PATH),
        "stale_reason_code": STALE_REASON_CODE,
        "on_contract_reason_present": on_contract_reason_present,
    }


def main(argv: list[str]) -> int:
    path = resolve_latest_ngi_path(argv)
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

    probable_sync_blocker = None
    if issues:
        probable_sync_blocker = detect_probable_sync_blocker()
        if probable_sync_blocker:
            issues.append("probable_blocker:standalone_workspace_runtime_copy_stale")

    status = "ok" if result.get("status") == "ok" and not issues else "contract_violation"
    output = {
        "status": status,
        "path": str(path),
        "issues": issues,
        "alert_contract_view": result,
        "allowed_reason_codes": sorted(P0_ALLOWED_REASON_CODES),
        "probable_sync_blocker": probable_sync_blocker,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
