#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in ["lobster-core", "lobster-plugins", "lobster-runtime", "lobster-ingest"]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_runtime import SourceFusionArtifacts, build_source_fusion_result, load_source_fusion_artifacts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--official", default="lobster-intel/data/runtime/sources/official-statements-tracker/latest.json")
    ap.add_argument("--watchlist", default="lobster-intel/data/runtime/sources/watchlist-tracker/latest.json")
    ap.add_argument("--polymarket", default="lobster-intel/data/runtime/sources/polymarket-tracker/latest.json")
    ap.add_argument("--output", default="lobster-intel/data/runtime/fusion/latest.json")
    args = ap.parse_args()

    artifacts = SourceFusionArtifacts(
        official_statements_path=Path(args.official),
        watchlist_path=Path(args.watchlist),
        polymarket_path=Path(args.polymarket),
    )
    inp = load_source_fusion_artifacts(artifacts)
    result = build_source_fusion_result(inp)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out_path), "gap_value": result.gap_value, "decision": result.data.get("decision")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
