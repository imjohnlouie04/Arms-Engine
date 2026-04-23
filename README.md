# ARMS — Architectural Runtime Management System

> **Multi-agent orchestration for full-stack excellence.**

ARMS is a professional-grade multi-agent orchestration framework designed to govern complex web development workspaces. It coordinates specialized AI sub-agents (Backend, Frontend, DevOps, Security, SEO, QA) through explicit approval gates, persistent memory, and domain-specific skill registration.

---

## 🏗️ The Architecture

ARMS operates on a **Hub and Spoke** model, separating global intelligence from project-specific execution:

1.  **Global Engine (`$ARMS_ROOT`):** The centralized repository of agents, skills, and workflow protocols. Located at `~/.gemini/Arms-Engine/` by default.
2.  **Project Instance (`./.gemini/`):** Localized session state, memory, and task logs that link back to the Global Engine. This directory is created automatically during initialization.

### Core Agents
- **`arms-main-agent`**: The System Architect. Manages handoffs, task tables, and memory.
- **`arms-backend-agent`**: API, Auth, and Business Logic specialist.
- **`arms-frontend-agent`**: UI/UX and Responsive Design enforcer.
- **`arms-devops-agent`**: CI/CD, Git, and Deployment expert.
- **`arms-seo-agent`**: SEO, Meta Tags, and Core Web Vitals enforcer.
- **`arms-media-agent`**: Asset creation and visual branding specialist.
- **`arms-data-agent`**: Database schema, migrations, and query optimizer.
- **`arms-security-agent`**: Security auditor and OWASP enforcer.
- **`arms-qa-agent`**: Testing and Quality Gatekeeper.

---

## 🚀 Installation

To use ARMS as a global engine across all your projects:

### 1. Clone the Engine
Place the engine in the recommended "Global Safe Zone":
```bash
mkdir -p ~/.gemini
git clone https://github.com/imjohnlouie04/Arms-Engine.git ~/.gemini/Arms-Engine
```

### 2. Configure Assistant Instructions
Add the contents of `$ARMS_ROOT/GEMINI.md` to your AI assistant's **Global Instructions** or **System Prompt**. This acts as the bootloader, teaching the assistant how to resolve paths and execute the initialization sequence.

---

## 🛠️ Usage & Commands

### Activation Commands
| Command | Mode | Description |
|:--- |:--- |:--- |
| `init` / `start` | **Standard** | Boots the engine and generates a Strategic Task Table. Halts for approval. |
| `init yolo` / `start yolo` | **Automated** | Skips the planning gate. Executes the entire task sequence without halting. |
| `init compress` | **Optimization** | Compresses session and memory files into token-efficient formats. |

### How it Works
1.  **Boot Sequence:** The assistant locates the engine at `~/.gemini/Arms-Engine/`.
2.  **Scaffolding:** `init-arms.sh` runs to link global skills and create `./.gemini/`.
3.  **Registration:** The `## Active Skills` roster is built in `SESSION.md`.
4.  **Planning Gate:** A **Strategic Task Table** is generated for the current requirements.
5.  **Execution:** Specialized agents are dispatched to complete individual tasks.

---

## 📂 Project State (`./.gemini/`)

ARMS maintains state exclusively within the project's root to ensure portability and context preservation:

- **`SESSION.md`**: The live project board. Contains the active Task Table and registered skills.
- **`MEMORY.md`**: The persistent knowledge base. Stores project-specific patterns, developer preferences, and technical debt.
- **`SESSION_ARCHIVE.md`**: The historical record of all completed tasks. Used for context recovery and verification.

---

## 🛡️ Protocols & Principles

- **The Planning Gate:** No work begins without an approved Task Table.
- **The Quality Gate:** Features are not marked `Done` until `arms-qa-agent` verifies them via tests/linting.
- **State Synchronization:** Every agent turn must be reflected in `SESSION.md`.
- **Memory Integrity:** We never overwrite project history; we append and refine.
- **Orchestrate, Don't Just Generate:** Focus on architecture and long-term maintainability over quick hacks.

---

*ARMS orchestrates. You decide.*
