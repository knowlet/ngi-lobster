from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
        return None
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def _parse_runtime_source_payload(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return payload


def _market_item_rank(item: dict[str, Any]) -> tuple[int, int, int, float]:
    metadata = item.get("metadata") or {}
    accepting_orders = _as_bool(metadata.get("accepting_orders"))
    active = _as_bool(metadata.get("active"))
    closed = _as_bool(metadata.get("closed"))
    latest_dt = _parse_ts(item.get("collected_at_utc")) or _parse_ts(item.get("published_at_utc"))
    latest_ts = latest_dt.timestamp() if latest_dt is not None else float("-inf")
    return (
        1 if accepting_orders is True else 0,
        1 if closed is False else 0,
        1 if active is True else 0,
        latest_ts,
    )


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _select_rollover_candidate(
    runtime_source_payload: dict[str, Any] | None,
    *,
    current_market_id: str | None,
) -> dict[str, Any] | None:
    if not runtime_source_payload:
        return None
    evidence = runtime_source_payload.get("evidence") or {}
    items = evidence.get("items") or []
    if not isinstance(items, list):
        return None

    eligible: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") or {}
        market_id = metadata.get("market_id") or item.get("external_id")
        if current_market_id and str(market_id) == str(current_market_id):
            continue
        if _as_bool(metadata.get("closed")) is not False:
            continue
        if _as_bool(metadata.get("accepting_orders")) is not True:
            continue
        eligible.append(item)

    if not eligible:
        return None

    candidate = max(eligible, key=_market_item_rank)
    metadata = candidate.get("metadata") or {}
    source_config = metadata.get("source_config") or {}
    return {
        "market_id": metadata.get("market_id") or candidate.get("external_id"),
        "market_slug": metadata.get("slug") or candidate.get("url"),
        "market_name": source_config.get("label") or candidate.get("title"),
        "market_question": candidate.get("title"),
        "market_yes_probability": metadata.get("yes_probability"),
        "market_closed": _as_bool(metadata.get("closed")),
        "market_active": _as_bool(metadata.get("active")),
        "market_accepting_orders": _as_bool(metadata.get("accepting_orders")),
        "collected_at_utc": candidate.get("collected_at_utc"),
        "published_at_utc": candidate.get("published_at_utc"),
    }


def build_summary(
    state_path: Path,
    db_path: Path,
    latest_ngi_path: Path,
    runtime_source_path: Path | None = None,
) -> dict[str, object]:
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
    runtime_source_payload = _parse_runtime_source_payload(runtime_source_path)
    rollover_candidate = _select_rollover_candidate(
        runtime_source_payload,
        current_market_id=str(market_target.get("market_id") or target_detail.get("market_id") or "") or None,
    )

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
        "rollover_candidate": rollover_candidate,
        "blockers": blockers,
    }


def main(argv: list[str]) -> int:
    if len(argv) not in {4, 5}:
        print(
            "usage: verify_runtime_ops_health.py <state.yaml> <intelligence_store.sqlite> <latest_ngi.json> [runtime_source_polymarket.json]",
            file=sys.stderr,
        )
        return 2

    state_path = Path(argv[1])
    db_path = Path(argv[2])
    latest_ngi_path = Path(argv[3])
    runtime_source_path = Path(argv[4]) if len(argv) == 5 else None

    try:
        summary = build_summary(state_path, db_path, latest_ngi_path, runtime_source_path)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
