# Gemini Instructions

> Managed bridge created by ARMS so Gemini CLI normal chat follows the shared task-intake protocol.
> If `./GEMINI.md` exists, read it as additional project context and preserve it as project-owned instructions.

### ARMS Orchestration & Intake
- **Workflow:** This project uses the ARMS (Architectural Runtime Management System). Follow the protocols in `.arms/RULES.md`.
- **Durable Tasks:** Every net-new issue, bug report, or feature request arriving through chat must be logged to `.arms/SESSION.md` using `arms task log` or `arms task update` before substantive execution begins. Use the standard task-table schema for all handoffs.
- **Routing Syntax:** When routing must be explicit, use `--assigned-agent` / `--active-skill` on task commands. `--agent` / `--skill` are accepted aliases.
- **Agent Handoff:** Updating `.arms/SESSION.md` does not itself switch Copilot into the specialist. After the row is assigned, invoke `/agent <assigned-agent>` for the implementation turn.
- **Verification:** No task is "Done" until validated by `arms-qa-agent` and pre-flight checks (lint, build, unit tests) pass.

---
