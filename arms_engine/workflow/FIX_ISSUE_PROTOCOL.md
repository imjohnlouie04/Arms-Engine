# ARMS GLOBAL PROTOCOL: FIX ISSUE
**Primary Executors:** `arms-main-agent`, `arms-backend-agent`, `arms-frontend-agent`, `arms-devops-agent`

## Overview
This protocol dictates the execution phase following a code review. It enforces strict task delegation, localized execution, mandatory pre-flight quality assurance, and a hard stop before deployment.

---

## Phase 1: Ingestion & Task Planning (`arms-main-agent`)
1. **Read the Report:** The orchestrator must read the latest `./.arms/reports/review-<YYYY-MM-DD>.md` file.
2. **Decompose & Delegate:** Break down the required fixes into a Task Table. 
   * *Columns:* Task | Assigned Agent | Dependencies | Status
3. **Session Sync:** Write the active Task Table to the local `./.arms/SESSION.md`.
4. **Approval Gate:** Present the resolution plan.
   > *"Task plan generated and logged. Shall I begin executing these fixes?"* -> **HALT**

## Phase 2: Execution & Defensive Coding (`arms-frontend-agent` / `arms-backend-agent`)
Subagents must execute their assigned tasks while adhering to global standards and local `./.gemini/RULES.md`.

* **Execution Template:** Every response during this phase MUST follow the strict execution template (`[Speaking Agent] -> [State Updates] -> [Action/Code] -> [Next Step/Blocker]`).
* **Architecture Guardrails:** You are strictly forbidden from modifying "Gatekeeper" authentication flows or "Holiday Pay" logic modules unless the user issues a direct, explicit override.
* **Frontend Strictness:** All Vue/Nuxt components must utilize `<script setup>`. Ensure state reactivity is memory-safe (e.g., utilizing VueUse).
* **Responsive Fixes:** If fixing layouts, ensure portrait tablets remain strictly as "Mobile Extended" (single column) and sidebars only trigger at `xl` (1280px).

## Phase 3: Pre-Flight QA (Mandatory)
Before any assigned agent marks a task as "Done" in the Task Table, they must pass the automated quality gates:
1. Run local linter (`npm run lint` or equivalent).
2. Run local type-checker (`npm run type-check`).
3. Run local build script.
*Note: If any check fails, the agent must auto-fix the minor issue or escalate a major blocker to the user -> **HALT**.*

## Phase 4: Version Control (`arms-devops-agent`)
Once all tasks are marked "Done":
1. The DevOps agent stages the changes.
2. Formulate a Conventional Commit message summarizing the fixes (e.g., `fix(ui): resolve sidebar breakpoint overlap on ipad`, `fix(auth): patch RLS policy leak`).
3. Ask for approval to commit the code -> **HALT**.

---

## Phase 5: Pipeline Handoff
After the commit is successfully merged into the local branch, the orchestrator prepares the handoff to the final stage of the pipeline.

> **Execution Mandate:** End the fix phase with the following prompt: 
> *"All issues have been resolved, tested, and committed locally. Shall I initiate the `DEPLOY_PROTOCOL` to push these changes to your remote environment?"* -> **HALT**