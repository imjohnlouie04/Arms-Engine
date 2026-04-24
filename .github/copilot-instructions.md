# Copilot Instructions for Arms-Engine

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
- **No formal test suite exists yet** – focus on manual validation during development
- Validate by running `arms init` in a test project and verifying output structure (`.gemini/` files created correctly)

### Linting
- **No lint configuration** – use Python conventions (PEP 8)

---

## Architecture Overview

### Hub and Spoke Model
ARMS operates with a strict separation of global engine logic from project-specific state:

- **Global Engine** (`arms_engine/` when installed): The "brain" containing agent definitions, skills, and workflows that never change per-project
- **Local Project Instance** (`.gemini/` in each project): The execution environment containing session state, memory, and task tables that are project-specific

### Key Components

#### 1. **Agent System** (`arms_engine/agents/` + `agents.yaml`)
- **agents.yaml**: Canonical registry mapping agents to roles, scopes, skills, and execution rules
- **Agent Markdown Files** (`agents/`): Individual agent instruction sets (imported by Copilot CLI via `/agent` command and synced to `.github/agents/` during `arms init`)
- **10 specialized agents**: Main (Orchestrator), Product, Backend, Frontend, DevOps, SEO, Media, Data, QA, Security

#### 2. **Skill System** (`arms_engine/skills/`)
- **Structure**: Each skill is a directory with a required `SKILL.md` + optional `references/` (checklists, best practices) and `scripts/` (utility scripts)
- **Metadata Headers**: Each `SKILL.md` has frontmatter with `name`, `description`, and optional metadata (same format as agents)
- **Discovery**: Valid skills must contain `SKILL.md` (validated in `init_arms.py:sync_skills()`)
- **Copilot CLI Sync**: All valid `SKILL.md` files are synced to `.github/skills/` as individual `.md` files for Copilot CLI discovery
- **Current Skills**: arms-orchestrator, backend-system-architect, frontend-design, logo-designer, nano-banana-pro, qa-automation-testing, security-code-review, seo-web-performance-expert, arms-docs-generator
- **Skill Adoption**: Skills are adopted by agents to gain domain-specific capabilities for specialized tasks

#### 3. **Workflow Protocols** (`arms_engine/workflow/`)
- Standardized procedures for CI/CD, code review, issue resolution, deployment
- Synced to `.gemini/workflow/` during `arms init` for project-specific reference

#### 4. **Initialization Pipeline** (`init_arms.py`)
The main entry point orchestrates:
1. **Folder Setup** – Creates `.gemini/` structure (agents, skills, workflow, reports, agent-outputs)
2. **Agent Sync** – Copies agent .md files to `.gemini/agents/` and `.github/agents/` (for Copilot CLI `/agent` discovery)
3. **Skill Sync** – Copies skill directories (with `SKILL.md`) to `.gemini/skills/` and `SKILL.md` files to `.github/skills/` (for Copilot CLI skill discovery)
4. **Workflow Sync** – Copies protocol files to `.gemini/workflow/`
5. **Copilot Instructions** – Syncs AGENTS.md to project root (Copilot instruction loading)
6. **Agent + Skill Discovery** – Scans `agents.yaml` and `skills/` directory, logs them to console output

---

## Key Conventions

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
  - **arms-qa-agent**: Must run Vitest/Playwright before marking tasks `Done`, strictly validates pre-flight checks
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
- Included in distribution: `agents/*.md`, `agents.yaml`, `skills/**/*`, `workflow/*`, `GEMINI.md`, `AGENTS.md`
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

Skills are also available in the Copilot CLI through file references or inline activation. After `arms init`, all SKILL.md files are synced to `.github/skills/`:

### Available Skills (Post-Init)

Located in `.github/skills/`:

- **`arms-orchestrator.md`** – Full-stack project orchestration, multi-agent workflows, approval gates
- **`backend-system-architect.md`** – Backend architecture, API design, database schemas
- **`frontend-design.md`** – Production-grade UI components with distinctive aesthetics
- **`security-code-review.md`** – OWASP audits, auth validation, RLS configuration, secret scanning
- **`qa-automation-testing.md`** – Unit/E2E test generation, Vitest/Playwright validation
- **`seo-web-performance-expert.md`** – Meta tags, semantic HTML, Core Web Vitals, schema markup
- **`logo-designer.md`** – Logo creation and asset design
- **`nano-banana-pro.md`** – Specialized image generation and media handling
- **`arms-docs-generator.md`** – Automatic documentation generation and updates

### How to Use Skills

Skills can be referenced inline in Copilot CLI conversations:

```
@skills/frontend-design.md
Build me a hero section with a bold brutalist aesthetic
```

Or adopt a skill within an agent context for specialized task execution. Skills are designed to be composed together—a single agent may adopt multiple skills for a complex task.
