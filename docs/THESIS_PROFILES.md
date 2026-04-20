# Thesis Profiles

## Project goal

NGI Lobster is being productized as an installable OpenClaw plugin, not just a local script bundle.

The install path we are aiming to make real is:

```text
openclaw plugins install -> source ingest plugins -> runtime spine -> auditable artifacts -> downstream delivery
```

Thesis profiles exist so that installed workflows can carry a stable runtime contract without moving decision logic into delivery code or scattering defaults across wrapper-only glue.

## What a thesis profile defines

Bundled thesis profiles live under:

```text
lobster-intel/examples/thesis-profiles/
```

Each profile is a JSON document keyed by `thesis_id`. It should define:

- `thesis_id`
- `title`
- `summary`
- `semantic_frame`
- `probability_direction`
- `state`
- `registry_file_path`
- optional `source_pack_dir`
- optional `source_config_paths`

`registry_file_path` points at the bundled target registry used to resolve the active comparison target.
`source_config_paths` lets a thesis pin the exact source-pack JSON files that the installed workflow should run before invoking the runtime spine.

## Operator contract

The installed thesis workflow is considered operator-ready only when all of these are true:

1. the profile exists for the requested `thesisId`
2. `semantic_frame`, `probability_direction`, and `state` resolve to non-empty runtime defaults
3. `registry_file_path` resolves to a concrete file
4. every required source plugin and referenced source-pack config file exists

If any of those fail, the JS install-surface workflow should stop before running source plugins or the runtime.

## Native OpenClaw surfaces

The native plugin wrapper now exposes two profile-aware tools:

- `ngi_lobster_list_installed_theses`
- `ngi_lobster_run_installed_thesis_workflow`

The catalog tool returns `contractStatus` plus `validationErrors` so another OpenClaw can inspect what is installed before choosing a thesis.
The workflow tool uses the same validation rules and fails closed when the thesis contract is incomplete.

## Example

```json
{
  "thesis_id": "regional-escalation",
  "title": "Regional escalation monitor",
  "summary": "Tracks the military-operations end-state thesis and bundled target registry defaults.",
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

## Design rule

Thesis profiles define runtime defaults and install-surface wiring.
They do not send chat messages, bypass the runtime, or move compare/alert decisions into delivery-only code.
