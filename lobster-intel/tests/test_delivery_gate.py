import pytest

from lobster_delivery import validate_background_output


def test_delivery_gate_allows_no_reply():
    assert validate_background_output("NO_REPLY") == "NO_REPLY"


def test_delivery_gate_allows_json():
    text = '{"status":"ok"}'
    assert validate_background_output(text) == text


def test_delivery_gate_rejects_commentary():
    with pytest.raises(ValueError):
        validate_background_output("Checking Telegram updates...")
