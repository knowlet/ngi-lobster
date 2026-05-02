from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from read_state_field import read_top_level_scalar


FRESHNESS_THRESHOLD_HOURS = 4.0
DIVERGENCE_THRESHOLD_PP = 15.0


def parse_utc_timestamp(raw: str) -> datetime:
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def compute_freshness_hours(snapshot_at_utc: str, now: datetime | None = None) -> float:
    reference = now or datetime.now(timezone.utc)
    return (reference - parse_utc_timestamp(snapshot_at_utc)).total_seconds() / 3600.0


def load_latest_snapshot_at_utc(db_path: Path) -> str:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT snapshot_at_utc FROM market_snapshots ORDER BY snapshot_at_utc DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    if not row or not row[0]:
        raise RuntimeError("missing market_snapshots row")
    return str(row[0])


def read_probability(payload: dict[str, object], key: str, *, context: str) -> float:
    value = payload.get(key)
    if value is None:
        raise RuntimeError(f"missing {context}.{key}")
    return float(value)


def load_latest_ngi_timestamp_utc(latest_ngi: dict[str, object]) -> str:
    for key in ("timestamp_utc", "generated_at_utc", "created_at_utc", "updated_at_utc", "snapshot_at_utc"):
        value = latest_ngi.get(key)
        if value:
            return str(value)
    raise RuntimeError(
        "missing latest_ngi timestamp (expected one of: timestamp_utc, generated_at_utc, created_at_utc, updated_at_utc, snapshot_at_utc)"
    )


def compute_signed_divergence_direction(first_principles_minus_market_pp: float) -> str:
    if first_principles_minus_market_pp > 0:
        return "first_principles_above_market"
    if first_principles_minus_market_pp < 0:
        return "first_principles_below_market"
    return "aligned"


def _as_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    return bool(value)


def build_summary(state_path: Path, db_path: Path, latest_ngi_path: Path) -> dict[str, object]:
    dq_status = read_top_level_scalar(state_path, "dq_status")
    latest_snapshot_at_utc = load_latest_snapshot_at_utc(db_path)
    freshness_hours = compute_freshness_hours(latest_snapshot_at_utc)

    latest_ngi = json.loads(latest_ngi_path.read_text(encoding="utf-8"))
    latest_ngi_timestamp_utc = load_latest_ngi_timestamp_utc(latest_ngi)
    latest_ngi_age_hours = compute_freshness_hours(latest_ngi_timestamp_utc)
    market_target = latest_ngi.get("market_target") or {}
    target_detail = latest_ngi.get("target_detail") or {}
    first_principles_probability = read_probability(
        latest_ngi, "first_principles_probability", context="latest_ngi"
    )
    market_yes_probability = read_probability(
        target_detail, "market_yes_probability", context="target_detail"
    )
    divergence_pp = abs(first_principles_probability - market_yes_probability) * 100.0
    first_principles_minus_market_pp = (first_principles_probability - market_yes_probability) * 100.0
    stale_data = freshness_hours > FRESHNESS_THRESHOLD_HOURS
    latest_ngi_stale = latest_ngi_age_hours > FRESHNESS_THRESHOLD_HOURS
    divergence_blocking = divergence_pp > DIVERGENCE_THRESHOLD_PP
    market_closed = _as_bool(target_detail.get("market_closed"))
    market_accepting_orders = _as_bool(target_detail.get("market_accepting_orders"))
    closed_target_blocking = market_closed is True or market_accepting_orders is False
    reselection_required = closed_target_blocking

    status = "pass"
    blockers: list[str] = []
    if dq_status != "pass":
        status = "fail"
        blockers.append(f"dq_status={dq_status}")
    if stale_data:
        status = "fail"
        blockers.append(f"stale_data={freshness_hours:.2f}h")
    if latest_ngi_stale:
        status = "fail"
        blockers.append(f"latest_ngi_stale={latest_ngi_age_hours:.2f}h")
    if closed_target_blocking:
        status = "fail"
        if market_closed is True:
            blockers.append("market_closed=true")
        if market_accepting_orders is False:
            blockers.append("market_accepting_orders=false")
    if divergence_blocking:
        status = "fail"
        blockers.append(f"divergence_pp={divergence_pp:.2f}")

    return {
        "status": status,
        "dq_status": dq_status,
        "latest_snapshot_at_utc": latest_snapshot_at_utc,
        "freshness_hours": round(freshness_hours, 4),
        "freshness_threshold_hours": FRESHNESS_THRESHOLD_HOURS,
        "stale_data": stale_data,
        "latest_ngi_timestamp_utc": latest_ngi_timestamp_utc,
        "latest_ngi_age_hours": round(latest_ngi_age_hours, 4),
        "latest_ngi_threshold_hours": FRESHNESS_THRESHOLD_HOURS,
        "latest_ngi_stale": latest_ngi_stale,
        "divergence_pp": round(divergence_pp, 4),
        "divergence_threshold_pp": DIVERGENCE_THRESHOLD_PP,
        "divergence_blocking": divergence_blocking,
        "first_principles_probability": first_principles_probability,
        "market_yes_probability": market_yes_probability,
        "first_principles_minus_market_pp": round(first_principles_minus_market_pp, 4),
        "direction": compute_signed_divergence_direction(first_principles_minus_market_pp),
        "probability_mode": target_detail.get("probability_mode") or latest_ngi.get("probability_mode") or "unknown",
        "market_target_id": market_target.get("market_id") or target_detail.get("market_id"),
        "market_target_name": market_target.get("market_name") or target_detail.get("market_question"),
        "market_closed": market_closed,
        "market_accepting_orders": market_accepting_orders,
        "closed_target_blocking": closed_target_blocking,
        "reselection_required": reselection_required,
        "next_contract_action": "reselect_active_target" if reselection_required else "keep_active_target",
        "blockers": blockers,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "usage: verify_runtime_ops_health.py <state.yaml> <intelligence_store.sqlite> <latest_ngi.json>",
            file=sys.stderr,
        )
        return 2

    state_path = Path(argv[1])
    db_path = Path(argv[2])
    latest_ngi_path = Path(argv[3])

    try:
        summary = build_summary(state_path, db_path, latest_ngi_path)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
