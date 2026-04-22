from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "packages"
for rel in [
    "lobster-core",
    "lobster-delivery",
    "lobster-ingest",
    "lobster-plugins",
    "lobster-runtime",
]:
    sys.path.insert(0, str(PACKAGES / rel))

from lobster_runtime.analyzers import analyze_evidence_artifact


def test_prediction_market_analyzer_emits_market_candidate_draft():
    evidence_artifact = {
        "artifact_id": "evidence:gooaye:polymarket-tracker:1517836",
        "external_id": "1517836",
        "source_type": "prediction_market",
        "content_refs": [
            {"kind": "title", "value": "Military operations end by June 30?"},
            {"kind": "url", "value": "military-operations-end-by-june-30"},
        ],
        "metadata": {
            "market_id": "1517836",
            "semantic_frame": "military_operations_end_by_deadline",
            "probability_direction": "yes_is_peace",
        },
        "provenance": {"source_ids": ["polymarket"]},
        "checksum": "abc123",
    }

    draft = analyze_evidence_artifact(evidence_artifact)

    assert draft.event_type == "market_candidate"
    assert draft.stance == "market_snapshot"
    assert draft.entity_refs == ["1517836"]
    assert "market_candidate" in draft.semantic_tags
    assert draft.extractive_rationale == "Military operations end by June 30?"
    assert draft.metadata["market_slug"] == "military-operations-end-by-june-30"
