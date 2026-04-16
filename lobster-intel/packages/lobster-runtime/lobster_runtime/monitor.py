from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

TARGET_CONTRACT_MISMATCH_REASON = "legacy_target_mismatch"
TARGET_CONTRACT_MISSING_REASON = "suppressed_runtime_target_missing"
TARGET_CONTRACT_OK_REASON = "active_target_contract_ok"


NOVELTY_MIN_NGI_DELTA = 0.10
NOVELTY_COOLDOWN_HOURS = 24


@dataclass(slots=True)
class AlertDecision:
    should_send: bool
    reason: str


def fmt_pct(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v:.1%}"


def iso_to_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def build_signature(data: dict[str, Any], expl: dict[str, Any] | None) -> dict[str, Any]:
    target = data.get("market_target") or {}
    return {
        "state": data.get("state"),
        "logic_summary": data.get("logic_summary"),
        "market_name": target.get("market_name"),
        "market_prob": data.get("market_escalation_probability"),
        "fp_prob": data.get("first_principles_escalation_probability"),
        "ngi": data.get("ngi"),
        "reasons": (expl or {}).get("reasons", []),
        "reason_keys": (expl or {}).get("reason_keys", []),
        "market_misses": (expl or {}).get("market_misses", []),
        "miss_keys": (expl or {}).get("miss_keys", []),
        "watch_next": (expl or {}).get("watch_next", []),
        "watch_keys": (expl or {}).get("watch_keys", []),
        "timestamp_utc": data.get("timestamp_utc"),
    }


def _target_identity(payload: dict[str, Any] | None) -> tuple[str | None, str | None, str | None]:
    target = payload or {}
    return (
        target.get("market_id"),
        target.get("market_slug"),
        target.get("market_name") or target.get("market_question"),
    )


def validate_alert_target_contract(
    runtime_data: dict[str, Any],
    alert_target: dict[str, Any] | None,
) -> AlertDecision:
    runtime_target = runtime_data.get("market_target") or {}
    runtime_identity = _target_identity(runtime_target)
    alert_identity = _target_identity(alert_target)

    if not any(runtime_identity):
        return AlertDecision(False, TARGET_CONTRACT_MISSING_REASON)

    runtime_id, runtime_slug, runtime_name = runtime_identity
    alert_id, alert_slug, alert_name = alert_identity

    matched = False
    if runtime_id and alert_id:
        matched = runtime_id == alert_id
    elif runtime_slug and alert_slug:
        matched = runtime_slug == alert_slug
    elif runtime_name and alert_name:
        matched = runtime_name == alert_name

    if not matched:
        return AlertDecision(False, TARGET_CONTRACT_MISMATCH_REASON)

    return AlertDecision(True, TARGET_CONTRACT_OK_REASON)


def should_send_alert(
    data: dict[str, Any],
    expl: dict[str, Any] | None,
    prior_state: dict[str, Any] | None,
) -> AlertDecision:
    if not prior_state:
        return AlertDecision(True, "first_alert")

    now_dt = iso_to_dt(data.get("timestamp_utc"))
    prev_dt = iso_to_dt(prior_state.get("timestamp_utc"))

    curr_ngi = data.get("ngi")
    prev_ngi = prior_state.get("ngi")
    reasons_changed = (expl or {}).get("reason_keys", []) != prior_state.get("reason_keys", [])
    misses_changed = (expl or {}).get("miss_keys", []) != prior_state.get("miss_keys", [])
    watch_changed = (expl or {}).get("watch_keys", []) != prior_state.get("watch_keys", [])
    state_changed = data.get("state") != prior_state.get("state")
    market_changed = (data.get("market_target") or {}).get("market_name") != prior_state.get("market_name")

    ngi_delta = abs((curr_ngi or 0) - (prev_ngi or 0))

    hours_since = None
    if now_dt and prev_dt:
        hours_since = (now_dt - prev_dt).total_seconds() / 3600.0

    if state_changed or market_changed or reasons_changed or misses_changed or watch_changed:
        return AlertDecision(True, "explanation_or_target_changed")

    if ngi_delta >= NOVELTY_MIN_NGI_DELTA:
        return AlertDecision(True, "ngi_changed_major")

    if hours_since is not None and hours_since < NOVELTY_COOLDOWN_HOURS:
        return AlertDecision(False, f"no_novelty_within_{NOVELTY_COOLDOWN_HOURS}h")

    return AlertDecision(False, "cooldown_elapsed_but_no_new_thesis")


def build_explanation(data: dict[str, Any]) -> dict[str, Any] | None:
    market = data.get("market_escalation_probability")
    fp = data.get("first_principles_escalation_probability")
    adsb = data.get("adsb") or {}
    firehose = data.get("firehose") or {}

    adsb_count = adsb.get("count")
    fh_events = firehose.get("events_analyzed", 0)

    if market is None or fp is None:
        return None

    underpriced_escalation = fp > market
    reasons: list[str] = []
    reason_keys: list[str] = []
    misses: list[str] = []
    miss_keys: list[str] = []
    watch: list[str] = []
    watch_keys: list[str] = []

    if underpriced_escalation:
        if adsb_count is not None and adsb_count >= 25:
            reasons.append(f"ADS-B 顯示區域軍機活動偏高（{adsb_count} 架）")
            reason_keys.append("adsb_high_activity")
        if fh_events >= 2:
            reasons.append(f"Firehose 最近 1h 出現升級訊號（{fh_events} 件）")
            reason_keys.append("firehose_escalation_present")
        reasons.append(f"第一性升級機率 {fmt_pct(fp)} 高於市場/代理 {fmt_pct(market)}")
        reason_keys.append("fp_above_market_proxy")

        misses.extend([
            "市場/宏觀代理可能仍在交易停火慣性敘事",
            "對停火破裂風險的再定價速度偏慢",
        ])
        miss_keys.extend([
            "market_lagging_truce_narrative",
            "repricing_lag",
        ])

        watch.extend([
            "48h 內是否出現新的直接軍事接觸",
            "油價與航運風險代理是否同步跳升",
            "官方措辭是否由維持停火轉向報復",
        ])
        watch_keys.extend([
            "watch_direct_contact",
            "watch_oil_shipping_proxy",
            "watch_official_rhetoric",
        ])
    else:
        reasons.append(f"市場/代理已反映主要風險（FP {fmt_pct(fp)} vs 市場/代理 {fmt_pct(market)}）")
        reason_keys.append("market_reflecting_risk")
        watch.append("維持監控，等待新事件驅動")
        watch_keys.append("watch_wait_for_new_signal")

    return {
        "reasons": reasons[:3],
        "reason_keys": reason_keys[:3],
        "market_misses": misses[:3],
        "miss_keys": miss_keys[:3],
        "watch_next": watch[:3],
        "watch_keys": watch_keys[:3],
    }
