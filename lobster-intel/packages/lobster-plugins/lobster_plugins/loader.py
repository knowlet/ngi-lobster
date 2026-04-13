from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from .manifest import PluginManifest, read_manifest


def _load_module(module_path: Path):
    spec = spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module: {module_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_entrypoint(plugin_dir: str | Path, entrypoint: str):
    module_name, func_name = entrypoint.split(":", 1)
    module_path = Path(plugin_dir) / module_name
    module = _load_module(module_path)
    return getattr(module, func_name)


def load_plugin(plugin_dir: str | Path) -> tuple[PluginManifest, dict[str, object]]:
    plugin_dir = Path(plugin_dir)
    manifest = read_manifest(plugin_dir / "plugin.json")
    entrypoints = {
        "ingest": resolve_entrypoint(plugin_dir, manifest.entrypoints.ingest),
    }
    if manifest.entrypoints.compile:
        entrypoints["compile"] = resolve_entrypoint(plugin_dir, manifest.entrypoints.compile)
    if manifest.entrypoints.evaluate:
        entrypoints["evaluate"] = resolve_entrypoint(plugin_dir, manifest.entrypoints.evaluate)
    return manifest, entrypoints

