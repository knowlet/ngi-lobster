from __future__ import annotations

import json


def validate_background_output(output: str) -> str:
    text = output.strip()
    if text == "NO_REPLY":
        return text
    try:
        json.loads(text)
    except Exception as exc:
        raise ValueError("Background output must be NO_REPLY or schema-valid JSON") from exc
    return text

