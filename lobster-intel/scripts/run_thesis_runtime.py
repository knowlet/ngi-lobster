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

from lobster_runtime import ThesisRuntimeInput, run_thesis_runtime
from lobster_runtime.runtime_spine import load_thesis_runtime_inputs


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the thesis runtime spine against installed source artifacts.")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--thesis-id", required=True)
    ap.add_argument(
        "--official",
        help="Override the official-statements runtime artifact path. Defaults to the installed workspace artifact.",
    )
    ap.add_argument(
        "--watchlist",
        help="Override the watchlist runtime artifact path. Defaults to the installed workspace artifact.",
    )
    ap.add_argument(
        "--polymarket",
        help="Override the polymarket runtime artifact path. Defaults to the installed workspace artifact.",
    )
    ap.add_argument("--registry-file", help="Override the runtime registry file path.")
    ap.add_argument("--semantic-frame", default="generic_thesis_frame")
    ap.add_argument("--probability-direction", default="yes_is_peace")
    ap.add_argument("--state", default="ACTIVE_TRUCE")
    ap.add_argument("--now-utc")
    args = ap.parse_args()

    try:
        runtime_inputs = load_thesis_runtime_inputs(
            args.workspace,
            thesis_id=args.thesis_id,
            official_statements_path=args.official,
            watchlist_path=args.watchlist,
            polymarket_path=args.polymarket,
            registry_file=args.registry_file,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
    result = run_thesis_runtime(
        ThesisRuntimeInput(
            thesis_id=args.thesis_id,
            workspace_dir=args.workspace,
            official_statements=runtime_inputs["official_statements"],
            watchlist=runtime_inputs["watchlist"],
            polymarket=runtime_inputs["polymarket"],
            target_registry=runtime_inputs["target_registry"],
            semantic_frame=args.semantic_frame,
            probability_direction=args.probability_direction,
            state=args.state,
            now_utc=args.now_utc,
        )
    )
    print(
        json.dumps(
            {
                "thesis_id": result.thesis_id,
                "run_id": result.run_id,
                "compare_mode": result.runtime_snapshot.get("compare_mode"),
                "input_contract": {
                    "workspace": str(Path(args.workspace).resolve()),
                    "source_resolution": runtime_inputs["source_resolution"],
                    "registry_resolution": runtime_inputs["registry_resolution"],
                },
                "artifact_paths": result.paths,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
