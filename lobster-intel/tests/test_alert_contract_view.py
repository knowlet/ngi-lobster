from lobster_delivery import build_alert_contract_view


def test_alert_contract_view_accepts_suppressed_fixture_with_shared_bundle_fields():
    payload = {
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {"market_yes_probability": 0.42},
        "first_principles_probability": 0.61,
        "alert_disposition": {
            "should_send": False,
            "decision": "suppressed",
            "reason_code": "legacy_target_mismatch",
            "runtime_target_id": "1517836",
            "alert_target_id": "legacy-430",
            "contract_version": "v1",
            "e2e_run_id": "e2e-20260417-01",
        },
    }

    result = build_alert_contract_view(payload)

    assert result["status"] == "ok"
    assert result["view"]["runtime_target_id"] == "1517836"
    assert result["view"]["alert_target_id"] == "legacy-430"
    assert result["view"]["e2e_run_id"] == "e2e-20260417-01"


def test_alert_contract_view_accepts_e2e_bundle_id_alias_for_shared_run_record():
    payload = {
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {"market_yes_probability": 0.42},
        "first_principles_probability": 0.61,
        "alert_disposition": {
            "should_send": False,
            "decision": "suppressed",
            "reason_code": "legacy_target_mismatch",
            "runtime_target_id": "1517836",
            "alert_target_id": "legacy-430",
            "contract_version": "v1",
            "e2e_bundle_id": "bundle-20260417-01",
        },
    }

    result = build_alert_contract_view(payload)

    assert result["status"] == "ok"
    assert result["view"]["e2e_run_id"] == "bundle-20260417-01"


def test_alert_contract_view_requires_delivery_proof_for_positive_control():
    payload = {
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {"market_yes_probability": 0.42},
        "first_principles_probability": 0.61,
        "alert_disposition": {
            "should_send": True,
            "decision": "would_send",
            "reason_code": "active_target_contract_ok",
            "runtime_target_id": "1517836",
            "alert_target_id": "1517836",
            "contract_version": "v1",
            "e2e_run_id": "e2e-20260417-01",
        },
    }

    result = build_alert_contract_view(payload)

    assert result["status"] == "contract_incomplete"
    assert "delivery_proof" in result["missing_fields"]


def test_alert_contract_view_accepts_positive_control_with_delivery_proof():
    payload = {
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {"market_yes_probability": 0.42},
        "first_principles_probability": 0.61,
        "alert_disposition": {
            "should_send": True,
            "decision": "would_send",
            "reason_code": "active_target_contract_ok",
            "runtime_target_id": "1517836",
            "alert_target_id": "1517836",
            "contract_version": "v1",
            "e2e_run_id": "e2e-20260417-01",
            "delivery_proof": {
                "boundary": "dispatcher_sink",
                "sink_message_id": "msg-123",
            },
        },
    }

    result = build_alert_contract_view(payload)

    assert result["status"] == "ok"
    assert result["view"]["delivery_proof"]["sink_message_id"] == "msg-123"
