# Worktree Sync And Publish Blockers

**Date:** 2026-04-20

**Goal:** Record the current environment blockers that prevented normal `fetch -> branch sync -> verify -> publish PR` flow, plus the exact next actions needed outside this sandbox.

---

## Context

This worktree started detached at commit `aaaf472` while the latest known local development line for the installed thesis workflow was on `codex/continue-runtime-spine-work` at `1eb5957`.

The development work for this run therefore used a manual file-port path instead of normal git sync and branch publishing.

## Confirmed Blockers

### 1. Git fetch is blocked by sandboxed worktree metadata writes

Evidence:

```bash
git -c core.fsmonitor=false fetch --all --prune
```

Observed error:

```text
error: cannot open '/Users/knowlet/ngi-lobster/.git/worktrees/ngi-lobster2/FETCH_HEAD': Operation not permitted
```

Impact:

- cannot refresh remote refs from inside this run
- cannot rely on normal `fetch` before development

### 2. The GitHub connector is not installed for `knowlet/ngi-lobster`

Evidence:

- `mcp__codex_apps__github._list_installed_accounts` did not list `knowlet`
- PR queries against `knowlet/ngi-lobster` returned HTTP `422`

Impact:

- cannot inspect the current PR state from the GitHub app
- cannot confirm unresolved review threads or publish PR updates through the connector

### 3. Python verification is blocked by a missing virtualenv and missing `pytest`

Evidence:

```bash
ls -la .venv
python3 -m pytest lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_source_runner_e2e.py -q
```

Observed results:

- `.venv` does not exist in this worktree
- `python3` is available, but `pytest` is not installed

Impact:

- JS verification can run
- Python runtime regression checks cannot run in this worktree until the environment is bootstrapped

## Mitigation Used In This Run

- compared the detached worktree against local ref `codex/continue-runtime-spine-work`
- manually ported the installed thesis workflow files, fixtures, tests, and docs into the current worktree
- verified:
  - `node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js`
  - `node --check index.js`
  - `node --check thesis-workflow-tool.js`

## Required Next Actions Outside This Sandbox

1. run git sync from a shell that can write repo metadata:
   - `git fetch --all --prune`
   - check whether `codex/continue-runtime-spine-work` should be resumed directly or merged into a new dev branch
2. bootstrap the runtime environment:
   - `./scripts/bootstrap_runtime.sh`
   - or otherwise create `.venv` and install `pytest`
3. rerun Python verification:
   - `.venv/bin/python -m pytest lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_source_runner_e2e.py -q`
4. restore PR visibility and publish path:
   - install the GitHub app on `knowlet/ngi-lobster` or use an authenticated `gh` session with network access
   - push the branch and open or update the PR after verification

## Resulting Development Rule

Until the blockers above are cleared, future automation runs in this sandbox should assume:

- latest remote truth may lag
- PR status may be unknown
- Python verification may be unavailable
- manual local-ref porting is the only safe sync fallback
