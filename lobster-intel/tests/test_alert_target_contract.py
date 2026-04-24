from lobster_runtime import validate_alert_target_contract


RUNTIME_DATA = {
    "market_target": {
        "market_id": "1517836",
        "market_slug": "trump-announces-end-of-military-operations-against-iran-by-june-30th-566-326-653-781-167-426-752-225",
        "market_name": "Trump announces end of military operations against Iran by June 30th",
    }
}


def test_alert_target_contract_suppresses_legacy_ceasefire_target():
    decision = validate_alert_target_contract(
        RUNTIME_DATA,
        {
            "market_id": "legacy-430",
            "market_slug": "iran-israel-ceasefire-by-april-30",
            "market_name": "Iran-Israel ceasefire by April 30",
        },
    )

    assert decision.should_send is False
    assert decision.reason == "legacy_target_mismatch"


def test_alert_target_contract_allows_current_active_target():
    decision = validate_alert_target_contract(
        RUNTIME_DATA,
        {
            "market_id": "1517836",
            "market_slug": "trump-announces-end-of-military-operations-against-iran-by-june-30th-566-326-653-781-167-426-752-225",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
    )

    assert decision.should_send is True
    assert decision.reason == "active_target_contract_ok"


def test_alert_target_contract_allows_same_market_id_when_slug_drifts():
    decision = validate_alert_target_contract(
        RUNTIME_DATA,
        {
            "market_id": "1517836",
            "market_slug": "trump-announces-end-of-military-operations-against-iran-by-june-30th-566-326-653-781-167-426-752-225-438",
            "market_name": "Trump announces end of military operations against Iran by June 30th?",
        },
    )

    assert decision.should_send is True
    assert decision.reason == "active_target_contract_ok"
