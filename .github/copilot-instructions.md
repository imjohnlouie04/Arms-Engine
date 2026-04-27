# Copilot Instructions for Arms-Engine

> **Source of Truth:** `.github/copilot-instructions.md` is derived from `arms_engine/skills/arms-orchestrator/SKILL.md`, which is the authoritative specification for ARMS. If this document and SKILL.md diverge, **SKILL.md is correct**. Refer to the full skill document for authoritative protocol details.

## Build, Test & Lint

### Development Installation
```bash
# Install from current directory in editable mode
pip install -e .

# Or use pipx for global installation
pipx install git+https://github.com/imjohnlouie04/Arms-Engine.git
```

### Available Commands
- **`arms`** – Main orchestration CLI (entry point: `arms_engine.init_arms:main`)
- **`arms-docs`** – Auto-update README.md agent roster from agents.yaml (entry point: `arms_engine.update_docs:main`)

### Build & Packaging
```bash
# Build distribution packages
python -m build

# Dynamic versioning via git tags (setuptools-scm)
# Tags are automatically synced to _version.py
git tag v1.1.0 && git push origin v1.1.0
```

### Testing & Validation
- Minimal regression suite: `python -m unittest discover -s tests -p "test_*.py"`
- Validate `arms init` changes with the regression suite first, then use a real temp project for manual confirmation when behavior spans multiple CLI surfaces

### Linting
- **No lint configuration** – use Python conventions (PEP 8)

---

## Architecture Overview

### Hub and Spoke Model
ARMS operates with a strict separation of global engine logic from project-specific state:

- **Global Engine** (`arms_engine/` when installed): The "brain" containing agent definitions, skills, and workflows that never change per-project
- **Local Project State** (`.arms/` in each project): The managed execution state containing session history, brand context, memory, rules, engine instructions, and generated planning artifacts
- **Local Assistant Mirrors** (`.gemini/`, `.agents/`, `.github/agents/`): Synced helper assets for agent discovery, skill discovery, and CLI integration

### Key Components

#### 1. **Agent System** (`arms_engine/agents/` + `agents.yaml`)
- **agents.yaml**: Canonical registry mapping agents to roles, scopes, skills, and execution rules
- **Agent Markdown Files** (`agents/`): Individual agent instruction sets (imported by Copilot CLI via `/agent` command and synced to `.github/agents/` during `arms init`)
- **10 specialized agents**: Main (Orchestrator), Product, Backend, Frontend, DevOps, SEO, Media, Data, QA, Security

#### 2. **Skill System** (`arms_engine/skills/`)
- **Structure**: Each skill is a directory with a required `SKILL.md` + optional `references/` (checklists, best practices) and `scripts/` (utility scripts)
- **Metadata Headers**: Each `SKILL.md` has frontmatter with `name`, `description`, and optional metadata (same format as agents)
- **Discovery**: Valid skills must contain `SKILL.md` and are registered during init sync
- **Copilot CLI Sync**: All valid `SKILL.md` files are synced to `.agents/skills/` for Copilot CLI discovery
- **Current Skills**: arms-orchestrator, backend-system-architect, frontend-design, devops-orchestrator, logo-design, nano-banana-pro, qa-automation-testing, security-code-review, seo-web-performance-expert, arms-docs-generator, caveman-compressor
- **Skill Adoption**: Skills are adopted by agents to gain domain-specific capabilities for specialized tasks

#### 3. **Workflow Protocols** (`arms_engine/workflow/`)
- Standardized procedures for CI/CD, code review, issue resolution, deployment
- Synced to `.arms/workflow/` during `arms init` for project-specific reference

#### 4. **Initialization Pipeline** (`cli.py` + support modules)
The public entry point remains `arms_engine.init_arms:main`, but the implementation is split across focused modules:
- `cli.py` — CLI parsing, watch mode, and orchestration
- `brand.py` — brand inference, questionnaires, and structured answer parsing
- `prompts.py` — context synthesis, generated prompts, and startup task seeding
- `skills.py` — agent/skill sync and registry generation
- `session.py` — migrations, version guard, and atomic session updates

The initialization flow orchestrates:
1. **Folder Setup** – Creates `.arms/`, `.gemini/agents/`, `.agents/skills/`, and supporting report/output directories
2. **Agent Sync** – Copies agent .md files to `.gemini/agents/` and `.github/agents/` (for Copilot CLI `/agent` discovery)
3. **Skill Sync** – Copies valid skill directories (with `SKILL.md`) to `.agents/skills/` and regenerates the local skill registry/index
4. **Workflow Sync** – Copies protocol files to `.arms/workflow/`
5. **Instruction Sync** – Deploys `.arms/ENGINE.md` and root `AGENTS.md`
6. **Context Synthesis** – Generates `.arms/CONTEXT_SYNTHESIS.md` and `.arms/GENERATED_PROMPTS.md` when intake is complete
7. **Session Refresh** – Updates `.arms/SESSION.md` and seeds the startup task table when appropriate

---

## ARMS System: Critical Protocols

This section documents protocols from `arms_engine/skills/arms-orchestrator/SKILL.md`. All future Copilot sessions must follow these rules strictly.

### 1. **Path Discovery (Always Run First)**
Resolve ARMS engine location in this order:
1. `~/.gemini/Arms-Engine/` (Global Safe Zone — Preferred)
2. `../Arms-Engine/` (Sibling to project)
3. `./Arms-Engine/` (Inside project root)

Never assume a path. If not found, halt immediately and request setup.

### 2. **Session Bootstrap Files (Never Overwrite)**
The managed ARMS workspace persists across sessions:
- **`./.arms/SESSION.md`**: Active task table, execution mode, active skills. **CRITICAL:** Task continuity mandate — NEVER delete `Pending`/`In Progress`/`Blocked` tasks. Archive `Done` tasks to `SESSION_ARCHIVE.md`.
- **`./.arms/MEMORY.md`**: Continuous learning file. **CRITICAL:** APPEND only; NEVER overwrite with template.
- **`./.arms/BRAND.md`**: Visual identity & positioning (referenced by Frontend, SEO, Media agents).
- **`./.arms/ENGINE.md`**: ARMS engine instructions, architecture direction, deployment target, and standards for the engine workflow.
- **`./.arms/RULES.md`**: Folder structure, naming conventions, TypeScript strict mode, testing standards.
- **`./GEMINI.md` or `./.gemini/GEMINI.md`**: Optional project-owned instructions. Preserve them if they already exist; read them as project context instead of overwriting them.

**Golden Rule:** If `./.arms/` or `./.gemini/` exists with populated files, READ them — NEVER overwrite managed state or memory with a template. Overwriting project memory is a **protocol violation**.

### 3. **Task Table Schema (Standardized)**
Every task delegation uses this schema:

| # | Task | Assigned Agent | Active Skill | Dependencies | Status |
|---|------|----------------|--------------|--------------|--------|
| 1 | Concise description | agent-name | skill-folder OR — | — OR task #'s | Pending/In Progress/Pre-Flight/Done/Blocked/Failed |

**Status Lifecycle:**
```
Pending → In Progress → Pre-Flight → Done
                      ↘ Blocked (+ reason)
                      ↘ Failed (+ reason)
```

**Status Rules:**
- Only `arms-main-agent` transitions tasks to `Done`
- **Auto-Critique Gate:** No feature can be marked `Done` without `arms-qa-agent` validation (tests/lint/build)
- When task status becomes `Done` or `Cancelled`, immediately remove from `SESSION.md` and append to `SESSION_ARCHIVE.md`
- `SESSION_ARCHIVE.md` is the **ultimate record of truth** for completed work — NEVER delete

### 4. **Strict Response Template (Every Response)**
All agents must follow this structure — no exceptions:

```
[Speaking Agent]: <agent-name>
[Active Skill]:   <skill folder OR "None">

[State Updates]: <Files written to ./.gemini/ | "None">

[Action / Code]:
<Task execution, code generation, or task table>

[Next Step / Blocker]: <Clear instruction ending with HALT for approval>
```

### 5. **Global Commands & Protocols**
When users invoke commands, `arms-main-agent` reads the corresponding protocol:

| Command | Protocol | Action |
|---|---|---|
| `init` | Standard | Boot sequence. Halt for plan approval. |
| `init yolo` | Automated | Full automation. Skip initial approval. |
| `init compress` | Efficiency | Bootstrap + compress SESSION/MEMORY for token efficiency. |
| `yolo` | Override | Fast-track execution for current plan. |
| `run review` | REVIEW_PROTOCOL.md | Audit via QA, Security, Frontend. |
| `fix issues` | FIX_ISSUE_PROTOCOL.md | Parse review, generate tasks, delegate. |
| `run deploy` | DEPLOY_PROTOCOL.md | Pre-flight, sync DB, deploy. |
| `run status` | Inline | Dump current state (tasks, blockers, phase). |
| `run pipeline` | Sequence | REVIEW → FIX → DEPLOY (gates between phases). |

**YOLO Mode:** Architect executes entire task table without individual approvals. Flash Recovery allowed (one auto-fix attempt on minor lint/type errors) before halting.

### 6. **Execution Modes (Detect at Session Start)**

**Mode A — Parallel (Copilot CLI with subagent support):**
- Spawn all independent agents in the same turn
- Never sequential-first; launch everything at once
- Agents with dependencies → spawn sequentially, gate on output
- `arms-main-agent` aggregates outputs

**Mode B — Simulated (Web UI / No subagent environment):**
- YOU (Copilot) embody each agent in sequence (inline, same response)
- Every agent turn rendered explicitly with strict response template
- Separated by dividers; never collapsed or summarized
- Dependencies respected: independent agents first, dependent agents after

**Shared Rules (Both Modes):**
- NEVER overwrite `## Environment` or `## Active Skills` in SESSION.md
- NEVER remove `- Engine Version:` from the `## Environment` block when updating tasks, blockers, or execution state
- NEVER overwrite MEMORY.md
- Every agent receives: role definition + SKILL.md + SESSION.md + MEMORY.md
- `arms-main-agent` owns aggregation — subagents return output, orchestrator writes to SESSION.md
- If any agent returns a blocker → HALT immediately

### 7. **Conflict Resolution Protocol**
When agents produce contradictory outputs:

1. **PAUSE** — Do not apply either
2. **PRESENT** — Side-by-side recommendations
3. **CLASSIFY** — Label conflict type:
   - Security vs. Feature → Security wins (user can override)
   - Performance vs. UX → Present trade-off, user decides
   - Style/Convention → Defer to RULES.md, then user
   - Architectural → Always escalate
4. **RECOMMEND** — Single recommended resolution
5. **HALT** — Never auto-resolve architectural or security conflicts

### 8. **Error Recovery Playbook**
| Failure | Symptoms | Recovery |
|---------|----------|----------|
| Agent Timeout | No output / incomplete response | Mark `Failed`. Re-queue. If fails twice → decompose + **HALT** |
| Build Failure | npm build or type-check fails | Mark `Failed`. Present error. Do NOT advance pipeline → **HALT** |
| Conflicting File Writes | Two agents modified same file | Invoke Conflict Resolution. Revert later write + **HALT** |
| SESSION.md Corruption | Empty/malformed/missing sections | Re-scaffold from Bootstrap Template. Preserve readable content → **HALT** |
| Missing Skill | Task requires non-existent skill | Execute using baseline from agents.yaml. Log warning. |
| Partial Pipeline Failure | Pipeline fails mid-sequence | DO NOT restart from beginning. Resume from failed phase → **HALT** |

**Recovery Rules:**
- Never silently retry. Surface every failure.
- Never discard partial work.
- Always log failure in SESSION.md under `## Blockers` with timestamp.
- Escalate after 2 consecutive failures — present decomposition strategy → **HALT**

### 9. **Memory Management & Archival**
After significant technical work, ask user approval before updating `MEMORY.md`:

> "May I update `./.arms/MEMORY.md` with this bug fix / preference / architectural decision?"

**Archival Triggers:**
- Task completion (Done/Cancelled) → append to SESSION_ARCHIVE.md + remove from SESSION.md
- Pipeline completion → archive entire Active Tasks table + reset
- User requests cleanup → archive remaining Failed tasks

**Archival Format:**
```markdown
## Archive — <ISO 8601 date>
### Context: <feature name or pipeline run>

| # | Task | Agent | Status | Completed |
|---|------|-------|--------|-----------|
<tasks>
```

**Archival Integrity:** SESSION_ARCHIVE.md is the ultimate record of truth. Never delete. If too large, use `compress` skill but NEVER delete history.

### 10. **Safety Gates & Checkpoints**
- **Git Checkpoint (Before major work):** `git add . && git commit -m "chore: checkpoint before [Task Name]"`
- **Pre-Flight QA (Mandatory before Done):** Run local build, lint, type-check. Auto-fix minor issues or escalate blockers.
- **Automated Commit (After task completion):** Formulate Conventional Commit (`feat(...)`, `fix(...)`). Request approval before committing → **HALT**

### 11. **Security & Standards**
- Never read/write `.env` — use `.env.local` or `.env.example`
- TypeScript strict mode mandatory, no exceptions
- OWASP enforcement via `arms-security-agent`
- Supabase RLS policies required for all tables
- Pre-flight validation before every commit
- Responsive design mandate: sidebar breakpoint = `xl` (1280px), **never** `lg` (1024px)

---

### 1. **Workspace Isolation Rule**
- **Read from**: `arms_engine/` (global engine logic, agents, skills, workflows) — ALWAYS install via package
- **Write to**: `.gemini/` (project-specific session state, memory, task tables) + `.github/agents/` (Copilot agent definitions)
- **Never reverse**: Do NOT write project state back to `arms_engine/`; do NOT read session state from anywhere except `.gemini/`

### 2. **Version Management**
- **Dynamic Versioning**: Uses `setuptools-scm` to auto-sync git tags to `_version.py`
- **Release Tagging**: `git tag v1.x.x && git push origin v1.x.x` automatically updates the installed package version
- **Fallback**: Version defaults to "1.0.0-dev" if git tags are unavailable (for local development)

### 3. **Agent State Management**
- **agents.yaml** is the single source of truth for agent metadata (role, scope, skills, execution rules)
- Agent .md files (in `agents/`) contain detailed instruction sets and are auto-synced to `.github/agents/` for Copilot CLI discovery
- **Critical Rules from agents.yaml**:
  - **arms-frontend-agent**: Mobile-First Mandate — override default UI sizes to `h-11` min, hide dense tables on mobile (`hidden md:block`), provide stacked card layouts (`block md:hidden`)
  - **arms-data-agent**: Must use Supabase CLI (`supabase init/start`) for local schema testing before remote execution
  - **arms-qa-agent**: Must run Vitest and the configured E2E suite before marking tasks `Done`; prefer Cypress and only use Playwright when the project explicitly requires it
  - **arms-security-agent**: Must audit all database migrations and auth logic, ensure zero PII/secret exposure

### 4. **Skill Discovery & Validation**
- Only directories containing `SKILL.md` are registered as valid skills
- Skills are discovered and logged during `arms init` for reference
- `arms-orchestrator` is marked `[Active]` in skill listings (it's the primary orchestration skill)

### 5. **Documentation Automation**
- **`arms-docs` command** auto-updates README.md agent roster from agents.yaml
- Uses markers: `<!-- AGENT_ROSTER_START -->` and `<!-- AGENT_ROSTER_END -->`
- Parses agent role and scope from YAML and generates formatted markdown

### 6. **Package Data Management** (`pyproject.toml`)
- Included in distribution: `agents/*.md`, `agents.yaml`, `skills/**/*`, `workflow/*`, `ENGINE.md`, `AGENTS.md`
- These files are vendored into the installed package so ARMS works offline and from any directory

### 7. **Naming Conventions**
- **Agent names**: kebab-case with `arms-` prefix (e.g., `arms-backend-agent`, `arms-security-agent`)
- **Skill directories**: kebab-case (e.g., `arms-orchestrator`, `frontend-design`)
- **Project folders**: `.gemini/` (execution environment), `.github/agents/` (Copilot integration)

---

## Typical Development Workflow

1. **Install in editable mode**: `pip install -e .` during local development
2. **Make changes**: Modify agents.yaml, add/update skills, update instruction sets in agent .md files
3. **Test with a real project**:
   ```bash
   cd /path/to/test-project
   arms init
   # Verify .gemini/ and .github/agents/ are created and populated correctly
   ```
4. **Update documentation**: Run `arms-docs` to auto-sync README.md with latest agent roster
5. **Tag & release**: `git tag v1.x.x && git push origin v1.x.x` for version bump
6. **Deploy globally**: `pipx upgrade arms-engine` (for users with pipx installation)

---

## When to Call Which Agent via `/agent`

Use Copilot CLI's `/agent` command to invoke specialized agents (available in `.github/agents/` after `arms init`):

- **arms-main-agent**: Orchestration, planning, delegation, session state management
- **arms-product-agent**: Requirements gathering, user stories, PRD generation
- **arms-backend-agent**: APIs, models, auth, database schemas
- **arms-frontend-agent**: UI components, routing, state, styling (mobile-first)
- **arms-devops-agent**: CI/CD pipelines, deployment strategies, tech stack initialization
- **arms-seo-agent**: Meta tags, semantic HTML, Core Web Vitals optimization
- **arms-media-agent**: Asset creation, design, media generation
- **arms-data-agent**: Database design, migrations, query optimization (via Supabase CLI)
- **arms-qa-agent**: Unit/E2E test writing, pre-flight validation, regression testing
---

## Accessing Skills in Copilot CLI

Skills are fully discoverable in the Copilot CLI. After `arms init`, all skill files are synced to `.agents/skills/` with proper metadata for CLI discovery.

### Skills Registry & Index

Three files support skill discovery:
- **`.agents/skills/`** – Directory containing all skill folders with `SKILL.md`
- **`.agents/skills.yaml`** – Auto-generated YAML registry of all available skills with metadata
- **`.agents/skills-index.md`** – Markdown index with quick reference and usage examples

### Available Skills (Post-Init)

Reference any skill in `.agents/skills/`:

- **`arms-orchestrator/SKILL.md`** – Full-stack project orchestration, multi-agent workflows, approval gates
- **`backend-system-architect/SKILL.md`** – Backend architecture, API design, database schemas
- **`frontend-design/SKILL.md`** – Production-grade UI components with distinctive aesthetics
- **`devops-orchestrator/SKILL.md`** – CI/CD, deployment automation, and zero-drift infrastructure workflows
- **`security-code-review/SKILL.md`** – OWASP audits, auth validation, RLS configuration, secret scanning
- **`qa-automation-testing/SKILL.md`** – Unit/E2E test generation, stable QA strategy, Cypress-first with Playwright when required
- **`seo-web-performance-expert/SKILL.md`** – Meta tags, semantic HTML, Core Web Vitals, schema markup
- **`logo-designer/SKILL.md`** – Logo creation and asset design
- **`nano-banana-pro/SKILL.md`** – Specialized image generation and media handling
- **`arms-docs-generator/SKILL.md`** – Automatic documentation generation and updates
- **`caveman-compressor/SKILL.md`** – Session and memory compression for token efficiency

### How to Use Skills

**Method 1: Copilot CLI `/skills` slash command (if available):**
```
/skills
[Select from list of available skills]
```

**Method 2: File reference in conversation:**
```
@skills/frontend-design/SKILL.md
Build me a hero section with a bold brutalist aesthetic
```

**Method 3: Inline skill adoption in agent context:**
When delegating to an agent, include the skill path in the task definition (see Task Table Schema in Section 3.3).

Skills are composable — a single agent may adopt multiple skills for complex work.
