from __future__ import annotations

import json
from typing import Any


def validate_background_output(output: str) -> str:
    text = output.strip()
    if text == "NO_REPLY":
        return text
    try:
        json.loads(text)
    except Exception as exc:
        raise ValueError("Background output must be NO_REPLY or schema-valid JSON") from exc
    return text


def deliver_heartbeat_payload(payload: dict[str, Any], *, send: bool) -> dict[str, Any]:
    output = json.dumps(payload, ensure_ascii=False, sort_keys=True) if send else "NO_REPLY"
    validated_output = validate_background_output(output)
    proof_id = f"heartbeat:{payload.get('run_id', 'unknown')}"
    delivery_proof = {
        "boundary": "openclaw_heartbeat",
        "proof_id": proof_id,
        "output": validated_output,
    }
    if send:
        delivery_proof["sink_message_id"] = proof_id
    return delivery_proof
