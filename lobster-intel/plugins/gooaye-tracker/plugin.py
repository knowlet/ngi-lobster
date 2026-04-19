from __future__ import annotations

from lobster_ingest.gooaye_pipeline import build_demo_result, fetch_gooaye_payload, process_gooaye_payload


def ingest(_ctx=None) -> dict:
    payload = fetch_gooaye_payload(_ctx)
    result = process_gooaye_payload(payload, _ctx)
    return build_demo_result(result["runtime"])
