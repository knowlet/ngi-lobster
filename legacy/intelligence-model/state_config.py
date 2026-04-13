#!/usr/bin/env python3
import json
import os
from copy import deepcopy

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_CONFIG_PATH = os.path.join(SCRIPT_DIR, "state_config.json")

DEFAULT_STATE = "PRE_AGREEMENT"


def load_state_config(path=STATE_CONFIG_PATH):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def get_current_state(config):
    states = (config or {}).get("states") or {}
    state = (config or {}).get("current_state") or DEFAULT_STATE
    if state not in states:
        return DEFAULT_STATE
    return state


def get_state_bundle(config, state=None):
    state = state or get_current_state(config)
    states = (config or {}).get("states") or {}
    bundle = deepcopy(states.get(state) or {})
    bundle["state"] = state
    return bundle


def get_active_target(bundle):
    target = (bundle or {}).get("target")
    if not isinstance(target, dict):
        return None
    return deepcopy(target)


def get_fallback_target(bundle):
    target = (bundle or {}).get("fallback_target")
    if not isinstance(target, dict):
        return None
    return deepcopy(target)
