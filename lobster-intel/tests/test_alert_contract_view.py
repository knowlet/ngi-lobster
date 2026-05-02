from lobster_delivery import build_alert_contract_view, build_e2e_contract_bundle_view


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
            "target_contract_match": False,
            "runtime_target_id": "1517836",
            "alert_target_id": "legacy-430",
            "contract_version": "v1",
            "e2e_run_id": "e2e-20260417-01",
        },
    }

    result = build_alert_contract_view(payload)

    assert result["status"] == "ok"
    assert result["view"]["target_contract_match"] is False
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


def test_alert_contract_view_requires_delivery_proof_boundary_for_positive_control():
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
                "sink_message_id": "msg-123",
            },
        },
    }

    result = build_alert_contract_view(payload)

    assert result["status"] == "contract_incomplete"
    assert "delivery_proof.boundary" in result["missing_fields"]


def test_alert_contract_view_requires_delivery_proof_id_for_positive_control():
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
            },
        },
    }

    result = build_alert_contract_view(payload)

    assert result["status"] == "contract_incomplete"
    assert "delivery_proof.proof_id" in result["missing_fields"]


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
            "target_contract_match": True,
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
    assert result["view"]["target_contract_match"] is True
    assert result["view"]["delivery_proof"]["sink_message_id"] == "msg-123"
    assert result["view"]["delivery_proof"]["proof_id"] == "msg-123"


def test_alert_contract_view_preserves_explicit_delivery_proof_id():
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
                "proof_id": "proof-123",
                "sink_message_id": "msg-123",
            },
        },
    }

    result = build_alert_contract_view(payload)

    assert result["status"] == "ok"
    assert result["view"]["delivery_proof"]["proof_id"] == "proof-123"


def test_e2e_contract_bundle_view_requires_shared_run_record_for_both_controls():
    suppressed_payload = {
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
            "e2e_run_id": "bundle-20260417-01",
        },
    }
    delivered_payload = {
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
            "e2e_run_id": "bundle-20260417-02",
            "delivery_proof": {
                "boundary": "dispatcher_sink",
                "sink_message_id": "msg-123",
            },
        },
    }

    result = build_e2e_contract_bundle_view([suppressed_payload, delivered_payload])

    assert result["status"] == "bundle_incomplete"
    assert "shared_field_mismatch:e2e_run_id" in result["issues"]


def test_e2e_contract_bundle_view_accepts_complete_shared_bundle():
    suppressed_payload = {
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
            "e2e_run_id": "bundle-20260417-01",
        },
    }
    delivered_payload = {
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
            "e2e_run_id": "bundle-20260417-01",
            "delivery_proof": {
                "boundary": "dispatcher_sink",
                "sink_message_id": "msg-123",
            },
        },
    }

    result = build_e2e_contract_bundle_view([suppressed_payload, delivered_payload])

    assert result["status"] == "ok"
    assert result["bundle"]["e2e_run_id"] == "bundle-20260417-01"
    assert [fixture["decision"] for fixture in result["bundle"]["fixtures"]] == [
        "suppressed",
        "would_send",
    ]


def test_alert_contract_view_falls_back_to_legacy_p_ai_field():
    payload = {
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {"market_yes_probability": 0.42},
        "P_AI": 0.61,
        "alert_disposition": {
            "should_send": False,
            "decision": "suppressed",
            "reason_code": "legacy_target_mismatch",
            "runtime_target_id": "1517836",
            "alert_target_id": "legacy-430",
            "contract_version": "v1",
            "e2e_run_id": "e2e-20260430-01",
        },
    }

    result = build_alert_contract_view(payload)

    assert result["status"] == "ok"
    assert result["view"]["p_ai"] == 0.61


def test_alert_contract_view_projects_signed_divergence_fields_for_downstream_ops():
    payload = {
        "market_target": {
            "market_id": "1517836",
            "market_name": "Trump announces end of military operations against Iran by June 30th",
        },
        "target_detail": {"market_yes_probability": 0.54},
        "first_principles_probability": 0.11563298545602181,
        "alert_disposition": {
            "should_send": False,
            "decision": "suppressed",
            "reason_code": "divergence_gate_blocked",
            "runtime_target_id": "1517836",
            "alert_target_id": "1517836",
            "contract_version": "v1",
            "e2e_run_id": "e2e-20260430-02",
        },
    }

    result = build_alert_contract_view(payload)

    assert result["status"] == "ok"
    assert result["view"]["divergence_pp"] == 42.4367
    assert result["view"]["first_principles_minus_market_pp"] == -42.4367
    assert result["view"]["direction"] == "first_principles_below_market"
