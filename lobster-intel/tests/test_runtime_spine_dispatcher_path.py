from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in [
    "lobster-core",
    "lobster-delivery",
    "lobster-ingest",
    "lobster-plugins",
    "lobster-runtime",
]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_delivery import write_dispatcher_e2e_bundle
from lobster_runtime import ThesisRuntimeInput, run_thesis_runtime
from lobster_runtime.runtime_spine import _decide_alert, compare_targets


def _source_payload(*, plugin: str, source_id: str, source_type: str, title: str, now_utc: str) -> dict:
    return {
        "plugin": plugin,
        "run_id": f"{plugin}-{now_utc}",
        "ran_at_utc": now_utc,
        "evidence": {
            "state_path": f"lobster-intel/data/runtime/sources/{plugin}/state.json",
            "items": [
                {
                    "source_id": source_id,
                    "source_type": source_type,
                    "external_id": f"{source_id}-1",
                    "title": title,
                    "collected_at_utc": now_utc,
                    "published_at_utc": now_utc,
                }
            ],
        },
    }


def _polymarket_payload(
    *,
    market_id: str,
    market_slug: str,
    market_question: str,
    yes_probability: float,
    now_utc: str,
) -> dict:
    return {
        "plugin": "polymarket-tracker",
        "run_id": f"polymarket-{now_utc}",
        "ran_at_utc": now_utc,
        "evidence": {
            "state_path": "lobster-intel/data/runtime/sources/polymarket-tracker/state.json",
            "items": [
                {
                    "source_id": "polymarket-feed",
                    "source_type": "prediction_market",
                    "external_id": market_id,
                    "title": market_question,
                    "url": f"https://polymarket.com/event/{market_slug}",
                    "collected_at_utc": now_utc,
                    "published_at_utc": now_utc,
                    "metadata": {
                        "market_id": market_id,
                        "market_slug": market_slug,
                        "market_question": market_question,
                        "semantic_frame": "truce_outcome",
                        "probability_direction": "yes_is_peace",
                        "yes_probability": yes_probability,
                        "active": True,
                        "closed": False,
                    },
                }
            ],
        },
    }


def test_runtime_spine_uses_dispatcher_contract_reason_code_for_legacy_target_mismatch(tmp_path: Path):
    thesis_id = "gooaye"
    workspace = tmp_path
    runtime_kwargs = {
        "thesis_id": thesis_id,
        "workspace_dir": workspace,
        "official_statements": _source_payload(
            plugin="official-statements-tracker",
            source_id="official-1",
            source_type="official_statement",
            title="Official statement",
            now_utc="2026-04-21T00:00:00+00:00",
        ),
        "watchlist": _source_payload(
            plugin="watchlist-tracker",
            source_id="watch-1",
            source_type="analyst_watchlist",
            title="Analyst warning",
            now_utc="2026-04-21T00:00:00+00:00",
        ),
        "semantic_frame": "truce_outcome",
        "probability_direction": "yes_is_peace",
        "state": "ACTIVE_TRUCE",
    }

    suppressed = run_thesis_runtime(
        ThesisRuntimeInput(
            target_registry=[
                {
                    "market_id": "1517836",
                    "market_slug": "trump-end-ops-june-30",
                    "market_question": "Trump announces end of military operations against Iran by June 30th?",
                    "semantic_frame": "truce_outcome",
                    "probability_direction": "yes_is_peace",
                    "aliases": ["iran-israel-ceasefire-by-april-30"],
                }
            ],
            polymarket=_polymarket_payload(
                market_id="legacy-430",
                market_slug="iran-israel-ceasefire-by-april-30",
                market_question="Iran-Israel ceasefire by April 30?",
                yes_probability=0.83,
                now_utc="2026-04-21T00:00:00+00:00",
            ),
            now_utc="2026-04-21T00:00:00+00:00",
            **runtime_kwargs,
        )
    )

    positive = run_thesis_runtime(
        ThesisRuntimeInput(
            target_registry=[
                {
                    "market_id": "1517836",
                    "market_slug": "trump-end-ops-june-30",
                    "market_question": "Trump announces end of military operations against Iran by June 30th?",
                    "semantic_frame": "truce_outcome",
                    "probability_direction": "yes_is_peace",
                }
            ],
            polymarket=_polymarket_payload(
                market_id="1517836",
                market_slug="trump-end-ops-june-30",
                market_question="Trump announces end of military operations against Iran by June 30th?",
                yes_probability=0.83,
                now_utc="2026-04-21T00:05:00+00:00",
            ),
            now_utc="2026-04-21T00:05:00+00:00",
            **runtime_kwargs,
        )
    )

    bundle = write_dispatcher_e2e_bundle(
        workspace_dir=workspace,
        thesis_id=thesis_id,
        run_ids=[suppressed.run_id, positive.run_id],
        bundle_id="bundle-20260421-runtime-spine",
        now_utc="2026-04-21T00:06:00+00:00",
    )

    assert suppressed.alert_artifact["should_send"] is False
    assert suppressed.alert_artifact["reason_code"] == "legacy_target_mismatch"
    assert suppressed.runtime_snapshot["alert_disposition"] == {
        "should_send": False,
        "decision": "suppressed",
        "reason_code": "legacy_target_mismatch",
        "runtime_target_id": "1517836",
        "runtime_target_name": "Trump announces end of military operations against Iran by June 30th?",
        "alert_target_id": "legacy-430",
        "target_contract_match": False,
        "contract_version": suppressed.runtime_snapshot["contract_version"],
    }
    assert positive.alert_artifact["should_send"] is True
    assert positive.runtime_snapshot["alert_disposition"]["target_contract_match"] is True
    assert positive.runtime_snapshot["alert_disposition"]["delivery_proof"]["proof_id"] == f"heartbeat:{positive.run_id}"
    assert positive.delivery_receipt["delivery_proof"]["boundary"] == "openclaw_heartbeat"
    assert bundle["bundle"]["fixtures"][0]["reason_code"] == "legacy_target_mismatch"
    assert bundle["bundle"]["fixtures"][1]["delivery_proof"]["proof_id"] == f"heartbeat:{positive.run_id}"


def test_runtime_spine_prefers_contract_reason_code_when_mismatch_is_not_first_fallback(tmp_path: Path):
    compare_artifact = compare_targets(
        active_target={
            "market_id": "1517836",
            "market_slug": "trump-end-ops-june-30",
            "semantic_frame": "truce_outcome",
            "probability_direction": "yes_is_peace",
            "fallback_used": True,
        },
        market_candidate={
            "market_id": "legacy-430",
            "market_slug": "iran-israel-ceasefire-by-april-30",
            "semantic_frame": "truce_outcome",
            "probability_direction": "yes_is_peace",
        },
    )
    runtime_snapshot = {
        "confidence": 0.9,
        "freshness": "fresh",
        "dq_status": "pass",
        "compare_mode": "suppressed",
        "ngi_gap": 0.2,
    }
    inp = ThesisRuntimeInput(thesis_id="gooaye", workspace_dir=tmp_path)

    alert_artifact = _decide_alert(
        inp=inp,
        run_id="run-1",
        created_at_utc="2026-04-21T00:00:00+00:00",
        runtime_snapshot=runtime_snapshot,
        compare_artifact={**compare_artifact, "artifact_id": "compare:gooaye:run-1"},
        prior_runtime_snapshot=None,
    )

    assert compare_artifact["fallback_reason_codes"] == [
        "live_search_fallback",
        "legacy_target_mismatch",
    ]
    assert alert_artifact["reason_code"] == "legacy_target_mismatch"
