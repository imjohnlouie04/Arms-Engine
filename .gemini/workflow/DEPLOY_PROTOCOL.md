# ARMS GLOBAL PROTOCOL: DEPLOY
**Primary Executors:** `arms-main-agent`, `arms-devops-agent`, `arms-data-agent`

## Overview
This protocol governs the final release of localized code to the remote environment. It enforces strict environmental checks, secure database migrations, automated release note generation, and the final absolute deployment gate.

---

## Phase 1: Environment & Sanity Check (`arms-devops-agent`)
Before initiating any remote connection, the DevOps agent must audit the finalized local state.

* **Commit Verification:** Ensure there are no uncommitted changes in the working directory. The `FIX_ISSUE_PROTOCOL` or manual work must be fully staged and committed.
* **Secret Shield:** Verify that no `.env`, `.env.local`, or `service_role` keys are staged for deployment.
* **Build Validation:** Run the final production build command (e.g., `npm run build`) locally to guarantee the bundle compiles successfully.

## Phase 2: Database Synchronization (`arms-data-agent`)
If the deployment includes database schema changes or new migrations, they must be applied *before* the application code is deployed.

1.  **Diff Review:** Summarize the pending local migrations in `supabase/migrations/` that differ from the remote project.
2.  **Approval Gate:** Present the migration summary.
    > *"Pending database migrations detected. Shall I execute `supabase db push` to the remote environment?"* -> **HALT**
3.  **Execution:** Upon approval, push the schema to the remote Supabase project.

## Phase 3: Release Note Generation (`arms-main-agent`)
Transform raw technical progress into client-friendly updates.

1.  **Fetch History:** Extract the recent conventional commits added since the last deployment.
2.  **AI Synthesis:** Process these technical commits through the AI context window to rewrite them into a polished, client-friendly changelog. Highlight new features, resolved bugs, and performance improvements while stripping out internal developer jargon.
3.  **Log State:** Save this changelog to `./.gemini/reports/release-notes-<YYYY-MM-DD>.md` in the local project directory.

## Phase 4: Final Deployment (`arms-devops-agent`)
The final step triggers the remote build process (e.g., pushing to the `main` branch to trigger Vercel, or pushing a Docker container).

> **Execution Mandate:** End the pre-deployment phase with the generated release notes and the final prompt:
> *"Pre-flight checks passed, DB synchronized, and release notes generated. Shall I initiate the final push to production?"* -> **HALT**

## Phase 5: Post-Deployment Cleanup
Once the user approves and the deployment is successful:
1.  **Prune Session:** Archive the completed deployment tasks from `./.arms/SESSION.md` into `./.arms/SESSION_ARCHIVE.md`.
2.  **Update Status:** Mark the deployment as complete and present the live URLs.