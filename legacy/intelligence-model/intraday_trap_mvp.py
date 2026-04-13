#!/usr/bin/env python3
"""
MVP: US intraday bull trap / late selloff prototype with CSV backtest support.

Required input features (column names can use aliases, see COL_ALIASES):
- 10Y yield intraday slope
- DXY intraday slope
- WTI/Brent change
- PPI shock
- Fed hawkish score
- Polymarket sentiment

Outputs per row:
- open_bias
- bull_trap_prob
- close_bias
- late_selloff_prob
- bull_trap_candidate (rule-gate boolean)

Usage:
  python3 intraday_trap_mvp.py --csv data.csv --out preds.csv --report
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Dict, List, Tuple

# Flexible input aliases -> canonical feature key
COL_ALIASES = {
    "teny_slope": ["teny_slope", "10y_slope", "10y_yield_slope", "us10y_slope", "yield_slope"],
    "dxy_slope": ["dxy_slope", "dollar_index_slope", "usd_slope"],
    "wti_change": ["wti_change", "wti_pct", "wti_change_pct", "wti_return"],
    "brent_change": ["brent_change", "brent_pct", "brent_change_pct", "brent_return"],
    "ppi_shock": ["ppi_shock", "ppi_surprise", "ppi_zscore"],
    "fed_hawkish": ["fed_hawkish", "fed_hawkish_score", "hawkish_score", "fed_score"],
    "polymarket_sent": ["polymarket_sent", "polymarket_sentiment", "poly_sentiment", "market_sentiment"],
}


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def find_col(row: Dict[str, str], aliases: List[str]) -> str | None:
    lower_map = {k.lower().strip(): k for k in row.keys()}
    for a in aliases:
        if a.lower() in lower_map:
            return lower_map[a.lower()]
    return None


def to_float(v: str, col: str) -> float:
    try:
        return float(v)
    except Exception as e:
        raise ValueError(f"Column '{col}' has non-numeric value: {v!r}") from e


def normalize_fields(row: Dict[str, str], mapping: Dict[str, str]) -> Dict[str, float]:
    vals = {}
    for k, col in mapping.items():
        vals[k] = to_float(row[col], col)
    return vals


def infer_mapping(header_row: Dict[str, str]) -> Dict[str, str]:
    mapping = {}
    for canonical, aliases in COL_ALIASES.items():
        col = find_col(header_row, aliases)
        if not col:
            raise ValueError(
                f"Missing required feature '{canonical}'. Accepted names: {aliases}"
            )
        mapping[canonical] = col
    return mapping


def predict(features: Dict[str, float]) -> Dict[str, object]:
    teny = features["teny_slope"]
    dxy = features["dxy_slope"]
    wti = features["wti_change"]
    brent = features["brent_change"]
    ppi = features["ppi_shock"]
    fed = features["fed_hawkish"]
    poly = features["polymarket_sent"]

    oil_strength = 0.5 * (wti + brent)

    # Rule gate required by spec:
    # IF (yield slope up) AND (oil/PPI strong) AND (Fed hawkish) => bull trap candidate
    yield_up = teny > 0
    oil_ppi_strong = (oil_strength > 0.4) or (ppi > 0.3)
    fed_hawkish = fed > 0.6
    bull_trap_candidate = yield_up and oil_ppi_strong and fed_hawkish

    # Lightweight scoring model (MVP, intentionally simple + interpretable)
    bull_trap_logit = (
        1.2 * teny
        + 1.0 * dxy
        + 0.9 * oil_strength
        + 0.8 * ppi
        + 1.4 * (fed - 0.5)
        - 0.7 * (poly - 0.5)
        + (0.9 if bull_trap_candidate else 0.0)
    )
    bull_trap_prob = clamp(sigmoid(bull_trap_logit))

    late_selloff_logit = (
        0.9 * bull_trap_prob
        + 0.8 * dxy
        + 0.6 * teny
        + 0.7 * (fed - 0.5)
        + 0.5 * ppi
        - 0.6 * (poly - 0.5)
    )
    late_selloff_prob = clamp(sigmoid(late_selloff_logit))

    # Open bias: sentiment vs macro squeeze
    open_score = 1.2 * (poly - 0.5) - 0.8 * dxy - 0.4 * (fed - 0.5)
    if open_score > 0.15:
        open_bias = "BULLISH_OPEN"
    elif open_score < -0.15:
        open_bias = "BEARISH_OPEN"
    else:
        open_bias = "NEUTRAL_OPEN"

    # Close bias: bull trap / late-day unwind pressure
    close_score = 0.7 * bull_trap_prob + 0.9 * late_selloff_prob + 0.3 * dxy
    close_bias = "BEARISH_CLOSE" if close_score >= 1.0 else "MIXED_TO_FLAT_CLOSE"

    return {
        "open_bias": open_bias,
        "bull_trap_prob": round(bull_trap_prob, 4),
        "close_bias": close_bias,
        "late_selloff_prob": round(late_selloff_prob, 4),
        "bull_trap_candidate": int(bull_trap_candidate),
    }


def brier_score(probs: List[float], labels: List[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(probs, labels)) / max(1, len(probs))


def run_backtest(rows: List[Dict[str, str]], preds: List[Dict[str, object]]) -> Dict[str, object]:
    report: Dict[str, object] = {"rows": len(rows)}

    # Optional labels in CSV:
    # bull_trap_realized, late_selloff_realized in {0,1}
    for label_col, prob_col in [
        ("bull_trap_realized", "bull_trap_prob"),
        ("late_selloff_realized", "late_selloff_prob"),
    ]:
        if all(label_col in r for r in rows):
            labels = [int(float(r[label_col])) for r in rows]
            probs = [float(p[prob_col]) for p in preds]
            pred_cls = [1 if x >= 0.5 else 0 for x in probs]
            acc = sum(int(a == b) for a, b in zip(pred_cls, labels)) / max(1, len(labels))
            report[label_col] = {
                "accuracy@0.5": round(acc, 4),
                "brier": round(brier_score(probs, labels), 4),
                "base_rate": round(sum(labels) / max(1, len(labels)), 4),
            }

    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Intraday bull trap / late selloff MVP backtester")
    ap.add_argument("--csv", required=True, help="Input CSV path")
    ap.add_argument("--out", default="", help="Output CSV path (default: <input>_pred.csv)")
    ap.add_argument("--report", action="store_true", help="Print backtest report if labels exist")
    args = ap.parse_args()

    in_path = Path(args.csv)
    out_path = Path(args.out) if args.out else in_path.with_name(in_path.stem + "_pred.csv")

    with in_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise ValueError("Input CSV is empty.")

    mapping = infer_mapping(rows[0])

    preds: List[Dict[str, object]] = []
    merged_rows: List[Dict[str, object]] = []
    for row in rows:
        features = normalize_fields(row, mapping)
        pred = predict(features)
        preds.append(pred)
        merged_rows.append({**row, **pred})

    fieldnames = list(merged_rows[0].keys())
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged_rows)

    print(f"[OK] Predictions written: {out_path}")
    print("[INFO] Output columns added: open_bias, bull_trap_prob, close_bias, late_selloff_prob, bull_trap_candidate")

    if args.report:
        report = run_backtest(rows, preds)
        print("[REPORT]", report)


if __name__ == "__main__":
    main()
