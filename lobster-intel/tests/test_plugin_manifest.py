import json
from pathlib import Path

import pytest

from lobster_plugins import read_manifest


def test_gooaye_manifest_loads():
    manifest_path = Path(__file__).resolve().parents[1] / "plugins" / "gooaye-tracker" / "plugin.json"
    manifest = read_manifest(manifest_path)
    assert manifest.id == "gooaye-tracker"
    assert manifest.type == "ingest"
    assert manifest.entrypoints.ingest == "plugin.py:ingest"


def test_gooaye_manifest_loads_tracker_contract():
    manifest_path = Path(__file__).resolve().parents[1] / "plugins" / "gooaye-tracker" / "plugin.json"
    manifest = read_manifest(manifest_path)
    assert manifest.tracker.source_family == "telegram_channel"
    assert manifest.tracker.default_source_type == "telegram_post"
    assert manifest.tracker.state_mode == "cursor_json"
    assert manifest.tracker.replayable is True
    assert manifest.tracker.follow_up_queues == ["linked_content_queue", "image_analysis_queue"]


def test_manifest_rejects_runtime_queue_output_without_tracker_contract(tmp_path: Path):
    manifest_path = tmp_path / "plugin.json"
    manifest_path.write_text(
        json.dumps(
            {
                "id": "broken-tracker",
                "name": "Broken Tracker",
                "version": "0.1.0",
                "type": "ingest",
                "entrypoints": {"ingest": "plugin.py:ingest"},
                "produces": ["runtime.linked_content_queue"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="tracker.follow_up_queues"):
        read_manifest(manifest_path)


def test_new_tracker_manifests_load():
    root = Path(__file__).resolve().parents[1] / "plugins"
    for plugin_id in ["polymarket-tracker", "official-statements-tracker", "watchlist-tracker"]:
        manifest = read_manifest(root / plugin_id / "plugin.json")
        assert manifest.id == plugin_id
        assert manifest.type == "ingest"
        assert manifest.entrypoints.ingest == "plugin.py:ingest"
