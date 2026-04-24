from lobster_runtime import validate_alert_target_contract


def test_validate_alert_target_contract_uses_runtime_target_missing_reason_verbatim():
    decision = validate_alert_target_contract({}, {"market_id": "1517836"})

    assert decision.should_send is False
    assert decision.reason == "runtime_target_missing"
