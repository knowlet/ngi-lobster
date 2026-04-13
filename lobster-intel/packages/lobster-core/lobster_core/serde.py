from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


def to_plain_data(value: Any):
    if is_dataclass(value):
        return {k: to_plain_data(v) for k, v in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [to_plain_data(v) for v in value]
    if isinstance(value, dict):
        return {k: to_plain_data(v) for k, v in value.items()}
    return value

