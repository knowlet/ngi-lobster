#!/usr/bin/env python3
import argparse
from pathlib import Path

from lobster_ingest.gooaye_pipeline import fetch_gooaye_payload, process_gooaye_payload

LOBSTER_DIR = Path(__file__).resolve().parents[1]
STATE_PATH = LOBSTER_DIR / "data" / "runtime" / "gooaye" / "channel-state.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=str(STATE_PATH))
    ap.add_argument("extras", nargs="*")
    args = ap.parse_args()

    payload = fetch_gooaye_payload(state=Path(args.state))
    result = process_gooaye_payload(payload)
    print(result["message"])


if __name__ == "__main__":
    main()
