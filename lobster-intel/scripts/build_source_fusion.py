#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in ["lobster-core", "lobster-delivery", "lobster-plugins", "lobster-runtime", "lobster-ingest"]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_runtime import SourceFusionArtifacts, build_source_fusion_result, load_source_fusion_artifacts, replay_source_run


def _firehose_replay_to_artifact(payload: dict) -> dict:
    return {
        "plugin": payload.get("plugin") or "firehose-tracker",
        "run_id": payload.get("run_id"),
        "ran_at_utc": payload.get("ran_at_utc"),
        "evidence": {
            "items": payload.get("items") or [],
            "new_count": payload.get("new_count"),
            "state_path": payload.get("state_path"),
        },
    }


def _load_firehose_payload(args: argparse.Namespace) -> dict | None:
    if not args.firehose_run_id:
        return None
    return _firehose_replay_to_artifact(replay_source_run(args.workspace, "firehose-tracker", args.firehose_run_id))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--official", default="lobster-intel/data/runtime/sources/official-statements-tracker/latest.json")
    ap.add_argument("--watchlist", default="lobster-intel/data/runtime/sources/watchlist-tracker/latest.json")
    ap.add_argument("--firehose", default="lobster-intel/data/runtime/sources/firehose-tracker/latest.json")
    ap.add_argument("--firehose-run-id")
    ap.add_argument("--polymarket", default="lobster-intel/data/runtime/sources/polymarket-tracker/latest.json")
    ap.add_argument("--output", default="lobster-intel/data/runtime/fusion/latest.json")
    args = ap.parse_args()

    artifacts = SourceFusionArtifacts(
        official_statements_path=Path(args.official),
        watchlist_path=Path(args.watchlist),
        firehose_path=Path(args.firehose),
        polymarket_path=Path(args.polymarket),
    )
    inp = load_source_fusion_artifacts(artifacts)
    historical_firehose = _load_firehose_payload(args)
    if historical_firehose is not None:
        inp.firehose = historical_firehose
    result = build_source_fusion_result(inp)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(out_path),
                "gap_value": result.gap_value,
                "decision": result.data.get("decision"),
                "firehose_events_analyzed": (result.data.get("firehose") or {}).get("events_analyzed"),
                "firehose_peace_score": (result.data.get("firehose") or {}).get("peace_score"),
                "firehose_source_run_id": (result.data.get("firehose") or {}).get("source_run_id"),
                "firehose_latest_event_at_utc": (result.data.get("firehose") or {}).get("latest_event_at_utc"),
                "firehose_latest_collected_at_utc": (result.data.get("firehose") or {}).get("latest_collected_at_utc"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
