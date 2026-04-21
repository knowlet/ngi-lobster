from lobster_delivery import build_active_target_compare_view


def test_active_target_compare_view_builds_escalation_compare_from_yes_is_peace_market():
    payload = {
        "timestamp_utc": "2026-04-21T03:31:37.899406+00:00",
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {
            "market_question": "Trump announces end of military operations against Iran by June 30th?",
            "market_yes_probability": 0.83,
            "probability_mode": "yes_is_peace",
        },
        "first_principles_probability": 0.1443305676,
        "alert_explain_contract": {
            "evidence_basis": {
                "logistics": "ADS-B 區域軍機活動 28 架",
                "energy": "能源/航運風險代理仍未跟上第一性升級定價",
                "key_statement": "第一性升級機率高於市場/代理",
            }
        },
    }

    result = build_active_target_compare_view(payload)

    assert result["status"] == "ok"
    assert result["view"]["market_implied_probability"] == 0.17
    assert result["view"]["divergence_pp"] == -2.57
    assert result["view"]["runtime_timestamp_utc"] == "2026-04-21T03:31:37.899406+00:00"
    assert result["view"]["logistics"] == "ADS-B 區域軍機活動 28 架"


def test_active_target_compare_view_requires_evidence_basis_for_user_facing_compare():
    payload = {
        "timestamp_utc": "2026-04-21T03:31:37.899406+00:00",
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {
            "market_question": "Trump announces end of military operations against Iran by June 30th?",
            "market_yes_probability": 0.83,
            "probability_mode": "yes_is_peace",
        },
        "first_principles_probability": 0.1443305676,
        "alert_explain_contract": {},
    }

    result = build_active_target_compare_view(payload)

    assert result["status"] == "contract_incomplete"
    assert result["missing_fields"] == ["logistics", "energy", "key_statement"]


def test_active_target_compare_view_requires_runtime_timestamp_for_staleness_audit():
    payload = {
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {
            "market_question": "Trump announces end of military operations against Iran by June 30th?",
            "market_yes_probability": 0.83,
            "probability_mode": "yes_is_peace",
        },
        "first_principles_probability": 0.1443305676,
        "alert_explain_contract": {
            "evidence_basis": {
                "logistics": "ADS-B 區域軍機活動 28 架",
                "energy": "能源/航運風險代理仍未跟上第一性升級定價",
                "key_statement": "第一性升級機率高於市場/代理",
            }
        },
    }

    result = build_active_target_compare_view(payload)

    assert result["status"] == "contract_incomplete"
    assert result["missing_fields"] == ["runtime_timestamp_utc"]
