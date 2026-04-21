# Install Guide Dispatcher Verification Plan

> **For agentic workers:** Keep this change scoped to operator-facing docs that already describe existing commands. Do not change runtime code or contract behavior in this plan.

**Goal:** Bring the root install guide up to date with the dispatcher acceptance and runtime target audit workflows that already exist in the repo, so operators can verify the current P0 delivery contract from the main install surface.

**Architecture:** Reuse the existing command surfaces documented under `lobster-intel/README.md` and `lobster-intel/docs/operations/reporting.md`, then add the missing operator steps to `docs/INSTALL_OPENCLAW.md`.

**Tech Stack:** Markdown docs only

**Status:** Implemented in the writable workspace on 2026-04-21.

---

### Task 1: Document The One-Shot Dispatcher Path

**Files:**
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Add the wrapper CLI example that writes suppressed and delivered dispatcher artifacts plus one shared bundle.
- [x] Explain what the command reads and writes so operators know which artifact families it materializes.

### Task 2: Document Latest-Target Audit

**Files:**
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Add the runtime target audit command that checks a reviewed run against `runtime/<thesis-id>/latest.json`.
- [x] Explain the fail-closed expectations for mismatched target ids and suppressed legacy fixtures.
