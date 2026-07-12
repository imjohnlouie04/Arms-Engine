# Claude Instructions

> Project-owned Claude instructions scaffolded by ARMS. Customize this file with repository-specific guidance as the project evolves.

### ARMS Orchestration & Intake
- **Workflow:** This project uses the ARMS (Architectural Runtime Management System). Follow the protocols in `.arms/RULES.md`.
- **Durable Tasks:** Every net-new issue, bug report, or feature request arriving through chat must be logged to `.arms/SESSION.md` using `arms task log` or `arms task update` before substantive execution begins. Use the standard task-table schema for all handoffs.
- **Routing Syntax:** When routing must be explicit, use `--assigned-agent` / `--active-skill` on task commands. `--agent` / `--skill` are accepted aliases.
- **Agent Handoff:** Updating `.arms/SESSION.md` does not itself switch the host tool into the specialist. After a row is assigned, hand the implementation turn to that agent: Claude Code runs the assigned agent as a subagent via its Task tool; Codex CLI spawns the assigned custom agent (defined in `.codex/agents/*.toml`) and waits for its result; Copilot CLI invokes `/agent <assigned-agent>`; other CLIs switch to the matching agent mirror. Run the specialist on the model tier shown in the row's `Model` column (resolved per platform by `model_routing.yaml`). Do not implement a specialist-assigned task inline as the orchestrator.
- **Brand Intake Display:** If `arms init` / `arms start` halts with `Awaiting Brand Context answers`, immediately read `.arms/BRAND_INTAKE.md` and display the compact answer block inline to the user. Do not merely tell the user to open the file unless they asked for a path-only summary.
- **Architecture Assessment (non-blocking):** `arms init` never blocks on the assessment — new projects bootstrap with fallback values immediately. When `.arms/RESEARCH_BRIEF.md` exists, offer the assessment conversationally: present the questions from `.arms/BRAND_INTAKE.md` as a numbered form, wait for answers, then follow `.arms/RESEARCH_BRIEF.md` — web-search the current best-fit stack for those answers (any stack, not just ARMS presets; verify latest stable names via search), and apply the resulting Stack Proposal with `arms intake --answers-text "<block>"`, then rerun `arms init`.
- **Verification:** No task is "Done" until validated by `arms-qa-agent` and pre-flight checks (lint, build, unit tests) pass.

---
