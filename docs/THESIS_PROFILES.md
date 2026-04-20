# Thesis Profiles

## Project goal

NGI Lobster exists to turn the current NGI workflow into an installable OpenClaw plugin product.

Thesis profiles are part of that install surface: they let `openclaw plugins install` carry stable runtime defaults without moving thesis decision logic into delivery code.

## What a thesis profile is

Bundled thesis profiles live under:

```text
lobster-intel/examples/thesis-profiles/<thesis-id>.json
```

They define the install-surface contract for one runnable thesis:

- thesis identity and operator-facing metadata
- runtime defaults such as `semantic_frame`, `probability_direction`, and `state`
- linked registry defaults
- explicit source-pack config paths for each bundled tracker

## Required contract fields

The current installed workflow treats these fields as required for a ready profile:

- `thesis_id`
- `semantic_frame`
- `probability_direction`
- `state`
- `registry_file_path`
- `source_config_paths.official-statements-tracker`
- `source_config_paths.watchlist-tracker`
- `source_config_paths.polymarket-tracker`

If any of these are missing, the profile is considered incomplete.

## Operator-facing behavior

The native OpenClaw wrapper now exposes the contract state directly:

- `ngi_lobster_list_installed_theses`
  returns `contractStatus` plus `validationErrors` for each bundled thesis
- `ngi_lobster_run_installed_thesis_workflow`
  refuses to launch source plugins or the thesis runtime when the selected profile is incomplete

This keeps install-time defaults explicit and fail-closed while leaving runtime truth in `lobster-intel/data/`.

## Example

```json
{
  "thesis_id": "regional-escalation",
  "title": "Regional escalation monitor",
  "summary": "Tracks the active military-operations end-state thesis and bundled market target defaults.",
  "semantic_frame": "military_operations_end_by_deadline",
  "probability_direction": "yes_is_peace",
  "state": "ACTIVE_TRUCE",
  "registry_file_path": "lobster-intel/examples/target-registries/regional-escalation.json",
  "source_config_paths": {
    "official-statements-tracker": "lobster-intel/examples/source-packs/official-statements.json",
    "watchlist-tracker": "lobster-intel/examples/source-packs/watchlist.json",
    "polymarket-tracker": "lobster-intel/examples/source-packs/polymarket.json"
  }
}
```
