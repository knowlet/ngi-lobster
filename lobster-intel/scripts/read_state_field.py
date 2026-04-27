from __future__ import annotations

import sys
from pathlib import Path


def read_top_level_scalar(path: Path, field: str) -> str:
    prefix = f"{field}:"
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith(prefix):
            continue
        value = line[len(prefix):].split("#", 1)[0].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'\"', "'"}:
            value = value[1:-1]
        return value
    raise KeyError(f"field not found: {field}")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: read_state_field.py <state.yaml> <field>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    field = argv[2]
    try:
        print(read_top_level_scalar(path, field))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
