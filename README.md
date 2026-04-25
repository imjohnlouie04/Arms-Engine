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

### 2. Local Project Instance
When initialized, ARMS performs a **Split Installation** to isolate project state from AI context:

#### 📂 `.arms/` — Project Engine State
- **`SESSION.md`**: The live orchestration board and task registry.
- **`SESSION_ARCHIVE.md`**: Permanent history of completed tasks.
- **`BRAND.md`**: Project identity and brand metadata. Existing repos get an inferred first draft; new projects get a question-driven brief for the owner to complete.

#### 📂 `.gemini/` — AI Assistant Context
- **`MEMORY.md`**: Project-specific persistent knowledge and technical debt tracker.
- **`GEMINI.md`**: Core system directives for the AI assistant.
- **`RULES.md`**: Project-specific coding standards and guardrails.
- **`agents/`**: Local mirror of the engine's agent assets.
- **`workflow/`**: Local copies of standard operating protocols.

#### 📂 `.agents/` — Cross-CLI Skill Discovery
- **`skills/`**: Canonical skill mirror used for local CLI skill discovery.
- **`skills.yaml`** / **`skills-index.md`**: Generated registries that document the synced skill set.

---

## 🚀 Getting Started

### 1. Global Installation (Recommended)
The best way to install the ARMS Engine is using `pipx`, which keeps the engine isolated and accessible from anywhere:

```bash
# Install once globally
pipx install git+https://github.com/imjohnlouie04/Arms-Engine.git

# Use it in any project
arms init
```

### 2. Development Setup
If you are contributing to the engine or prefer a local link:
```bash
git clone https://github.com/imjohnlouie04/Arms-Engine.git
cd Arms-Engine
pip install -e .
```

---

## 🎮 Operational Commands

| Command | Mode | Execution Logic |
|:--- |:--- |:--- |
| `arms init` | **Standard** | Boots engine, syncs assets, and generates a **Strategic Task Table**. |
| `arms init yolo` | **Automated** | Skips the planning gate. Executes all tasks sequentially. |
| `arms-docs` | **Documentation** | Updates the `README.md` agent roster from `agents.yaml`. |

During `arms init`, missing brand context is handled differently by project state:
- Existing repository: ARMS inspects the project and writes a first-pass `.arms/BRAND.md`.
- New / empty project: ARMS creates a question-driven `.arms/BRAND.md` that captures both brand context and the initial technical direction. After filling it in, re-run `arms init` to resume from that checkpoint.

---

## 🔄 Updating & Versioning

### Standard Installation
```bash
pipx upgrade arms-engine
```

### Development Installation
```bash
cd /path/to/Arms-Engine
git pull
```

### Tagging a Release
To formally update the version number:
```bash
git tag v1.1.0
git push origin v1.1.0
```
The engine uses **Dynamic Versioning** to automatically sync with your Git tags.

---

## 🤖 The Agent Roster

ARMS dynamically discovers agents and their skills from `agents.yaml`.

<!-- AGENT_ROSTER_START -->
- **`arms-main-agent`** (Orchestrator): Planning, delegation, session management.
- **`arms-product-agent`** (Product Manager): Requirements gathering, user stories, PRD generation, feature prioritization.
- **`arms-backend-agent`** (Backend Specialist): APIs, models, auth, backend services.
- **`arms-frontend-agent`** (Frontend Specialist): UI components, routing, state, API integration.
- **`arms-devops-agent`** (DevOps Specialist): CI/CD, deployment, boilerplate initialization based on chosen tech stack.
- **`arms-seo-agent`** (SEO Specialist): Search engine optimization, meta tags, semantic HTML validation, schema markup, Core Web Vitals.
- **`arms-media-agent`** (Media Specialist): Asset creation.
- **`arms-data-agent`** (Data Specialist): Schema design, migrations, query optimization.
- **`arms-qa-agent`** (QA & Testing Specialist): Writing unit/E2E tests, performing pre-flight validation.
- **`arms-security-agent`** (Security Specialist): Enforces OWASP standards, validates auth flows, configures RLS, audits dependencies.
<!-- AGENT_ROSTER_END -->

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
