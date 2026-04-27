# ARMS Agent Roster & Skill Discovery

This file helps Copilot CLI discover available agents and their capabilities in this ARMS-managed workspace.

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

Skills are discovered from `.agents/skills/` and provide domain expertise to agents. Common skills include:

- **arms-orchestrator** – Full-stack project orchestration, multi-agent workflows, approval gates
- **backend-system-architect** – Backend architecture, API design, database schemas
- **frontend-design** – Production-grade UI components with distinctive aesthetics
- **devops-orchestrator** – Deployment automation and zero-drift infrastructure workflows
- **security-code-review** – OWASP audits, auth validation, RLS configuration
- **qa-automation-testing** – Unit/E2E test generation, Cypress-first E2E strategy
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

## Project Instructions

For ARMS orchestration logic and system architecture details, see `.arms/ENGINE.md`.

For agent-specific instructions, see individual agent files in `.github/agents/`.
