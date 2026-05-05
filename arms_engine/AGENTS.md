# ARMS Agent Roster & Skill Discovery

This file helps Copilot CLI discover available agents and their capabilities in this ARMS-managed workspace.

---

## ⚠️ MANDATORY TASK INTAKE GATE

**Every request that creates durable work MUST be logged before execution.** This rule applies to ALL plain chat messages — not only explicit `arms task log` commands.

**Classify every incoming message before acting:**

| Message type | Action |
|---|---|
| Feature request, bug fix, audit, code review, improvement, refactor, "fix X", "add X", "build X" | Run `arms task log --task "<normalized 1-line ask>"` → route to specialist → execute |
| Clarification, approval, status nudge, follow-up on open task | Stay attached to current SESSION.md row — no new log entry |
| Protocol / orchestration (`arms init`, `arms doctor`, session state) | `arms-main-agent` handles directly |

> **Non-negotiable:** Executing a work request without logging it first is a protocol violation.

---

## Available Agents

ARMS automatically manages the following specialized agents. Use `/agent <agent-name>` in Copilot CLI to invoke them:

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

## Available Skills

Skills are mirrored from `arms_engine/skills/` into `.agents/skills/` and `.github/skills/`, while agent-to-skill bindings come from `arms_engine/agents.yaml`. Common skills include:

- **arms-orchestrator** – Full-stack project orchestration, multi-agent workflows, approval gates
- **backend-system-architect** – Backend architecture, API design, database schemas
- **frontend-design** – Production-grade UI components with distinctive aesthetics
- **ui-ux-pro-max** – Expanded UI/UX design system and review guidance
- **3d-web-experience** – Three.js, React Three Fiber, Spline, and immersive 3D web experience guidance
- **devops-orchestrator** – Deployment automation and zero-drift infrastructure workflows
- **security-code-review** – OWASP audits, auth validation, RLS configuration
- **qa-automation-testing** – Unit/E2E test generation, Cypress-first E2E strategy
- **Accessibility Auditor** – WCAG compliance, semantic HTML, and inclusive UX audits
- **seo-web-performance-expert** – Meta tags, semantic HTML, Core Web Vitals optimization
- **logo-design** – Logo creation and asset design
- **nano-banana-pro** – Specialized image generation
- **arms-docs-generator** – Automatic documentation generation
- **caveman-compressor** – Context and session compression

## How to Use

1. **In Copilot CLI:** Use `/agent <agent-name>` to invoke a specialized agent
   ```
   /agent arms-backend-agent
   Build me a REST API for user authentication
   ```

2. **Reference a Skill:** Use `@skills/<skill-name>/SKILL.md` to adopt specialized capabilities
   ```
   @skills/backend-system-architect
   Design a microservices architecture for our platform
   ```

3. **Check Project State:** Review `.arms/SESSION.md` for current active tasks, agents, and skills

## Normal Chat Intake

- A plain CLI or IDE chat message can still be a task intake event. Do **not** require the user to type `arms task log` manually after they already described the work.
- If a normal message, pasted issue body, screenshot, or image attachment starts or materially changes durable work, summarize the ask in text, then create or refresh the matching `.arms/SESSION.md` row using `arms task log --task "<normalized ask>"` semantics before substantive planning or implementation.
- Route that row to the correct specialist agent and auto-fill the bound skill from the ARMS registry.
- If the message is only a clarification, approval, status nudge, or continuation of an already-open task, keep it attached to the current row and use `arms task update` semantics only when the ledger entry itself materially changes.

## Project Instructions

For ARMS orchestration logic and system architecture details, see `.arms/ENGINE.md`.

For agent-specific instructions, see individual agent files in `.github/agents/`.
