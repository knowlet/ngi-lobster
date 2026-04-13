from pathlib import Path

from lobster_plugins import read_manifest


def test_gooaye_manifest_loads():
    manifest_path = Path(__file__).resolve().parents[1] / "plugins" / "gooaye-tracker" / "plugin.json"
    manifest = read_manifest(manifest_path)
    assert manifest.id == "gooaye-tracker"
    assert manifest.type == "ingest"
    assert manifest.entrypoints.ingest == "plugin.py:ingest"
