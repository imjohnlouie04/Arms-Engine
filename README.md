# ARMS — Architectural Runtime Management System

> **Multi-agent orchestration for full-stack excellence.**

ARMS is a professional-grade multi-agent orchestration framework designed to govern complex web development workspaces. It coordinates specialized AI sub-agents (Backend, Frontend, DevOps, Security, SEO, QA) through explicit approval gates, persistent memory, and domain-specific skill registration.

---

## 🏗️ The Architecture

ARMS operates on a "Hub and Spoke" model:

1.  **Global Engine ($ARMS_ROOT):** The centralized repository of agents, skills, and workflow protocols. This is the source of truth for all orchestration logic.
2.  **Project Instance (./.gemini/):** Localized session state, memory, and task logs that link back to the Global Engine.

### Core Agents
- **`arms-main-agent`**: The Orchestrator. Manages handoffs, task tables, and memory.
- **`arms-backend-agent`**: API, Auth, and Business Logic specialist.
- **`arms-frontend-agent`**: UI/UX and Responsive Design enforcer.
- **`arms-devops-agent`**: CI/CD, Git, and Deployment expert.
- **`arms-security-agent`**: Security auditor and OWASP enforcer.
- **`arms-qa-agent`**: Testing and Quality Gatekeeper.

---

## 🚀 Installation

To use ARMS as a global engine across all your projects:

### 1. Clone the Engine
We recommend placing the engine in a "Global Safe Zone":
```bash
mkdir -p ~/.gemini
git clone https://github.com/imjohnlouie04/Arms-Engine.git ~/.gemini/Arms-Engine
```

### 2. Configure Global Rules
Add the contents of `GEMINI.md` from the engine root to your AI assistant's global instructions. This ensures the assistant knows how to locate and boot the engine.

---

## 🛠️ Usage

### Bootstrapping a New Project
In any project directory, simply type:
```text
init
```
Or for full automation:
```text
init yolo
```

### How it Works
1.  **Path Resolution:** The assistant locates the global engine at `~/.gemini/Arms-Engine/`.
2.  **Linking:** The `init-arms.sh` script is executed to scaffold the local `./.gemini/` structure.
3.  **Registration:** All domain skills are linked to the project context.
4.  **Orchestration:** The `arms-orchestrator` skill takes over, generating a Strategic Task Table for your requirements.

---

## 📂 Structure

- `/skills`: Domain-specific `SKILL.md` definitions for specialized sub-agents.
- `/workflow`: Standardized protocols for `REVIEW`, `FIX`, and `DEPLOY`.
- `agents.yaml`: Master roster defining roles, scopes, and skill bindings.
- `init-arms.sh`: The universal linker script.

---

## 🛡️ Principles
- **Orchestrate, don't just generate.**
- **Explicit approval gates** at every major architectural decision.
- **Persistent memory** that adapts to developer preferences.
- **Strict standards enforcement** (TypeScript, SEO, Security, Responsive Design).

---

*ARMS orchestrates. You decide.*
