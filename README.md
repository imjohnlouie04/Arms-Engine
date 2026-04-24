# ARMS — Architectural Runtime Management System

> **Multi-agent orchestration for full-stack excellence.**

ARMS is a professional-grade multi-agent orchestration framework designed to govern complex web development workspaces. It coordinates specialized AI sub-agents (Backend, Frontend, DevOps, Security, SEO, QA) through explicit approval gates, persistent memory, and domain-specific skill registration.

---

## 🏗️ Core Architecture

ARMS operates on a **Hub and Spoke** model, ensuring that global engine intelligence is strictly separated from project-specific execution state.

### 1. Global Engine (`$ARMS_ROOT`)
The centralized "brain" of the system, typically installed in the **Global Safe Zone** (`~/.gemini/Arms-Engine/`).
- **`agents/`**: Core personality and instruction sets for specialized agents.
- **`skills/`**: Domain-specific capability modules (e.g., `frontend-design`, `security-audit`).
- **`workflow/`**: Standardized protocols for CI/CD, code review, and issue resolution.
- **`agents.yaml`**: The canonical registry mapping agents to their roles and skills.

### 2. Local Project Instance (`./.gemini/`)
When initialized, ARMS performs a **Full Installation** into the project root, creating a self-contained execution environment:
- **`SESSION.md`**: The live orchestration board and task registry.
- **`MEMORY.md`**: Project-specific persistent knowledge and technical debt tracker.
- **`agents/` & `skills/`**: Local mirrors of the engine's assets for low-latency context access.
- **`workflow/`**: Local copies of standard operating protocols.

---

## 🚀 Getting Started

### 1. Global Installation
Clone the engine into your system's global config directory:
```bash
mkdir -p ~/.gemini
git clone https://github.com/imjohnlouie04/Arms-Engine.git ~/.gemini/Arms-Engine
```

### 2. Bootstrapping a Project
Navigate to any project directory and run the activator:
```bash
bash ~/.gemini/Arms-Engine/init-arms.sh
```
This script:
1.  **Scaffolds** the local `.gemini/` infrastructure.
2.  **Installs** all global agents, skills, and protocols into the project.
3.  **Synchronizes** `agents.yaml` and `RULES.md`.
4.  **Initializes** the `SESSION.md` with an active roster of discovered entities.

---

## 🎮 Operational Commands

| Command | Mode | Execution Logic |
|:--- |:--- |:--- |
| `init` | **Standard** | Boots engine, syncs assets, and generates a **Strategic Task Table**. Halts for approval. |
| `init yolo` | **Automated** | Skips the planning gate. Executes all tasks sequentially without halting. |
| `init compress` | **Optimization** | Invokes the `compress` skill to shrink logs into token-efficient formats. |

---

## 🤖 The Agent Roster

ARMS dynamically discovers agents and their skills from `agents.yaml`. Standard agents include:

- **`arms-main-agent` (Architect)**: Orchestrates handoffs and maintains session integrity.
- **`arms-backend-agent`**: Logic, API design, and server-side stability.
- **`arms-frontend-agent`**: Visual excellence and responsive implementation.
- **`arms-data-agent`**: Schema management and query optimization.
- **`arms-security-agent`**: Security audits and OWASP compliance.
- **`arms-qa-agent`**: Quality gates and automated testing.
- **`arms-media-agent`**: Branding and asset generation.

---

## 🛠️ The Skill System

A **Skill** in ARMS is a self-contained directory containing a `SKILL.md` file. This file acts as a specialized instruction set that an agent "adopts" when performing specific tasks.

### Structure of a Skill:
```text
skills/
  └── my-specialized-skill/
      ├── SKILL.md        # The primary instruction set
      ├── references/     # (Optional) Best practices, checklists
      └── scripts/        # (Optional) Utility scripts for the agent
```

---

## 📋 Workflow Protocols

ARMS enforces standardized protocols found in the `workflow/` directory:
- **`DEPLOY_PROTOCOL.md`**: Requirements for moving code to production.
- **`REVIEW_PROTOCOL.md`**: Multi-agent peer review standards.
- **`FIX_ISSUE_PROTOCOL.md`**: Root-cause analysis and remediation steps.

---

## 🛡️ Core Principles

1.  **The Planning Gate**: No execution without an approved Task Table.
2.  **Quality Mandate**: Every feature requires a `Done` status from `arms-qa-agent`.
3.  **State Persistence**: All state is local to the project, ensuring full portability.
4.  **Non-Destructive Sync**: Subsequent `init` calls update skills and agents while preserving your active tasks and memory.

---

*ARMS orchestrates. You decide.*
