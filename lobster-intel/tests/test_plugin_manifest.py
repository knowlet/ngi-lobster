from pathlib import Path

from lobster_plugins import read_manifest


def test_gooaye_manifest_loads():
    manifest_path = Path(__file__).resolve().parents[1] / "plugins" / "gooaye-tracker" / "plugin.json"
    manifest = read_manifest(manifest_path)
    assert manifest.id == "gooaye-tracker"
    assert manifest.type == "ingest"
    assert manifest.entrypoints.ingest == "plugin.py:ingest"


def test_new_tracker_manifests_load():
    root = Path(__file__).resolve().parents[1] / "plugins"
    for plugin_id in ["polymarket-tracker", "official-statements-tracker", "watchlist-tracker"]:
        manifest = read_manifest(root / plugin_id / "plugin.json")
        assert manifest.id == plugin_id
        assert manifest.type == "ingest"
        assert manifest.entrypoints.ingest == "plugin.py:ingest"
