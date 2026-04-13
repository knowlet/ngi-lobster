from lobster_plugins import read_manifest


def test_gooaye_manifest_loads():
    manifest = read_manifest("/Users/knowlet/.openclaw/workspace/lobster-intel/plugins/gooaye-tracker/plugin.json")
    assert manifest.id == "gooaye-tracker"
    assert manifest.type == "ingest"
    assert manifest.entrypoints.ingest == "plugin.py:ingest"

