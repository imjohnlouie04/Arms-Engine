# ARMS — Architectural Runtime Management System

> **Multi-agent orchestration for full-stack delivery with persistent project state.**

ARMS is a Python-powered orchestration engine that bootstraps a project workspace for AI-assisted delivery. It installs a local control plane for planning, memory, skills, workflow references, and agent discovery so the same project can be resumed consistently across sessions.

---

## Core Architecture

ARMS operates on a **hub-and-spoke** model:
1.  **Global Engine:** The installed package (`arms_engine/`) containing agent instructions, skills, and workflow protocols.
2.  **Local Project Instance:** Project-specific state and mirrors stored in `.arms/`, `.gemini/`, and `.github/`.

### Key Workspace Artifacts (managed by ARMS)
-   `.arms/SESSION.md`: Live orchestration board (tasks, environment, hot-context).
-   `.arms/BRAND.md`: Brand, stack, and product intake questionnaire.
-   `.arms/CONTEXT_SYNTHESIS.md`: AI-ready project brief derived from `BRAND.md`.
-   `.arms/MEMORY.md`: Persistent project memory (lessons learned, approved by user).
-   `.arms/ENGINE.md`: Managed engine instructions (synced from global engine).
-   `.arms/GENERATED_PROMPTS.md`: Agent-ready prompts referencing the synthesis brief.

---

## Building and Running

### Development Environment
-   **Language:** Python >= 3.8
-   **Dependencies:** Managed via `pyproject.toml` (primarily `pyyaml`).
-   **Setup:**
    ```bash
    git clone https://github.com/imjohnlouie04/Arms-Engine.git
    cd Arms-Engine
    pip install -e .
    ```

### Key CLI Commands
-   `arms init`: Bootstrap/sync a workspace. Supports `yolo`, `compress`, and `--monitor` modes.
-   `arms start`: Alias for `init`.
-   `arms doctor`: Workspace diagnostics and repair (`--fix`).
-   `arms memory`: Manage structured memory (`draft`, `append`).
-   `arms task`: Manage task ledger (`log`, `update`, `done`).
-   `arms run [status|review|deploy|pipeline]`: Protocol-driven workflow execution.
-   `arms release check`: Pre-release validation gate.
-   `arms-docs`: Automatically update agent roster in README.md.

### Testing
-   **Unit Tests:** Located in `tests/`.
-   **Run Tests:**
    ```bash
    python -m unittest discover -s tests -p "test_*.py"
    ```

---

## Development Conventions

### Code Structure
-   **Modularized Init:** The `init` logic is split into focused modules (`cli.py`, `brand.py`, `skills.py`, etc.) to facilitate testing and isolation.
-   **Strict Pathing:** Use `arms_engine.paths.WorkspacePaths` for all project-relative file resolutions.
-   **Version Guard:** ARMS prevents syncing a project with an older engine version than the one that last touched it (override with `--allow-engine-downgrade`).

### Agent & Skill Management
-   **Registry:** Agents and their skill bindings are defined in `arms_engine/agents.yaml`.
-   **Syncing:** Engine-owned files (agents, skills, workflow) are mirrored into projects during `arms init`. DO NOT edit mirrored files directly in a project; update the source in `arms_engine/`.
-   **Mirroring Locations:**
    -   Agents: `.gemini/agents/`, `.github/agents/`
    -   Skills: `.agents/skills/`, `.github/skills/`

### Workflow Protocols
Agents must strictly follow the protocols defined in `arms_engine/workflow/`:
-   **Review Protocol:** Strict criteria for QA (TS strictness), Frontend (Mobile-first mandate), and Security (RLS, Env vars).
-   **Fix Protocol:** Automated resolution based on review findings.
-   **Deploy Protocol:** Release note generation and pre-deployment gates.

### Memory & Task Discipline
-   **Planning First:** Always propose/update tasks in `.arms/SESSION.md` before execution.
-   **Memory Cycle:** Draft lessons from session findings -> User approves -> Append to `.arms/MEMORY.md` -> Refreshes hot-context signals.
