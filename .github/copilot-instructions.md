# Copilot Instructions for Arms-Engine

> **Source of Truth:** `arms_engine/skills/arms-orchestrator/SKILL.md` is the authoritative specification for ARMS protocols. If this file and SKILL.md diverge, **SKILL.md is correct**.

## Build, Test & Lint

```bash
# Development install
pip install -e .

# Full regression suite
python -m unittest discover -s tests -p "test_*.py"

# Single test file
python -m unittest tests.test_init_regression

# Single test case
python -m unittest tests.test_init_regression.InitRegressionTests.test_sync_engine_instructions_preserves_root_gemini

# Build distribution packages
python -m build
```

No lint configuration — follow PEP 8.

After changing `arms init` behavior, run the regression suite first, then manually test with a real temp project when behavior spans multiple CLI surfaces.

---

## Architecture

### Hub-and-Spoke Model

```
arms_engine/          ← Global engine (never write project state here)
  agents/             ← Agent .md instruction sets (synced to .github/agents/, .claude/agents/)
  agents.yaml         ← Canonical agent registry (roles, skills, rules)
  skills/             ← Skill directories (each must contain SKILL.md)
  workflow/           ← Protocol .md files (REVIEW, FIX_ISSUE, DEPLOY)
  ENGINE.md           ← Deployed as .arms/ENGINE.md in target projects

.arms/                ← Per-project managed state (never overwrite templates)
  SESSION.md          ← Active task table + hot-context roster
  MEMORY.md           ← Append-only lessons file
  BRAND.md            ← Visual identity (watched by --watch mode)
  ENGINE.md           ← Copied from arms_engine/ENGINE.md on init
  RULES.md            ← Project-specific rules
  SESSION_ARCHIVE.md  ← Completed task history — never delete

.agents/skills/       ← Skill mirror for Copilot CLI discovery
.claude/agents/       ← Agent mirror for Claude Code sub-agents
.claude/commands/     ← Skill mirror for Claude Code slash commands (flat .md files)
.gemini/agents/       ← Agent mirror for Gemini CLI discovery
.github/agents/       ← Agent mirror for Copilot /agent command
.github/skills/       ← Skill mirror for GitHub Copilot
```

### Initialization Pipeline (`cli.py` → support modules)

The public entry point is `arms_engine.init_arms:main` (a thin shim). Real logic lives in:

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Argument parsing, watch mode, `run_init_once()` orchestration |
| `brand.py` | Brand questionnaire, preset application, answer parsing |
| `session.py` | Version guard, migrations, `update_session()`, token budgets |
| `skills.py` | Agent/skill sync to mirrors, registry generation (`skills.yaml`, `skills-index.md`) |
| `prompts.py` | `CONTEXT_SYNTHESIS.md` and `GENERATED_PROMPTS.md` generation, startup task seeding |
| `protocols.py` | `run review`, `fix issues`, `run deploy`, `run pipeline`, `run status` handlers |
| `tasks.py` | `arms task log/update/done` — SESSION.md task row management |
| `memory.py` | `arms memory draft/append` — MEMORY.md staged-approval workflow |
| `doctor.py` | Workspace diagnostics, required file/dir checks, token budget warnings |
| `compression.py` | SESSION.md and MEMORY.md compaction (`arms init compress`) |
| `release.py` | `arms release check` pre-release gate (read-only, exits non-zero on blockers) |
| `monitor.py` | `--monitor` HUD: live HTML debug report at `.arms/reports/init-monitor-latest.html` |
| `versioning.py` | Version resolution from git tags, `_version.py`, and installed metadata |
| `update_docs.py` | `arms-docs` command — auto-updates README.md agent roster from agents.yaml |

`init_arms.py` is a **compatibility shim** — do not add logic there; put it in the appropriate module above.

---

## Key Conventions

### Command Handler Pattern
Every sub-command follows the same two-function pattern, dispatched from `cli.py`:

```python
# In the handler module (e.g., tasks.py, memory.py, protocols.py):
def identify_<command>(command_parts) -> str | None:
    # Returns a command key or empty string; never raises

def handle_<command>(project_root, arms_root, command_name, **kwargs):
    # Executes the command; raises SystemExit on failure
```

`cli.py` calls each `identify_*` function in order and short-circuits on the first match.

### Skill Validation
A skill directory is **only valid** if it contains `SKILL.md`. Directories without it are silently ignored during sync. `REFERENCE_ONLY_SKILL_DIRS` in `skills.py` lists skill subdirs that are excluded from the project mirror.

### Session File Rules
- `SESSION.md`: NEVER delete `Pending`/`In Progress`/`Blocked` rows. Archive `Done`/`Cancelled` rows to `SESSION_ARCHIVE.md` immediately.
- `MEMORY.md`: APPEND only — never overwrite with a template.
- `SESSION_ARCHIVE.md`: Never delete. Compress with `arms init compress` if too large.
- `ENGINE.md` and `AGENTS.md` at project root are engine-owned and overwritten on every `arms init`. `GEMINI.md` and `.github/copilot-instructions.md` are **project-owned** — read them for context, never overwrite.

### Version Management
- Dynamic versioning via `setuptools-scm` writes to `arms_engine/_version.py`.
- Release: `git tag v1.x.x && git push origin v1.x.x`.
- Dev fallback: `"1.0.0-dev"` when git tags are unavailable.
- `arms doctor` reports all version sources (git describe, `_version.py`, installed metadata).

### Package Data
Files vendored into the distribution (declared in `pyproject.toml`):
`agents/*.md`, `agents.yaml`, `skills/**/*`, `workflow/*`, `ENGINE.md`, `AGENTS.md`

Adding a new file under these paths requires no `pyproject.toml` change. Adding a new top-level directory does.

### Naming Conventions
- **Agent names**: kebab-case with `arms-` prefix (`arms-backend-agent`)
- **Skill directories**: kebab-case (`backend-system-architect`, `arms-orchestrator`)
- **Workspace dirs**: `.arms/` (state), `.agents/` (Copilot skills), `.claude/` (Claude Code), `.gemini/` (Gemini), `.github/agents/` (Copilot agents)

### Test Patterns
All tests use `unittest.TestCase` with `TemporaryDirectory` for isolation and `mock.patch.object(sys, "argv", [...])` + `redirect_stdout` to invoke the CLI without subprocess overhead:

```python
def invoke_cli(self, cwd, *args):
    stdout = io.StringIO()
    with working_directory(cwd), mock.patch.object(sys, "argv", ["arms", *args]), redirect_stdout(stdout):
        init_arms.main()
    return stdout.getvalue()
```

Always pass `--root str(ARMS_ROOT)` in tests so init uses the local engine source, not any globally installed version.

---

## Development Workflow

1. `pip install -e .` — editable install
2. Change agent `.md` files, `agents.yaml`, skill `SKILL.md`, or Python modules
3. `python -m unittest discover -s tests -p "test_*.py"` — verify no regressions
4. Manually test in a real temp project: `cd /tmp/myproject && arms init --root /path/to/arms_engine`
5. `arms-docs` — sync README.md agent roster from agents.yaml
6. `git tag v1.x.x && git push origin v1.x.x` — release

### Useful Diagnostic Commands
```bash
arms doctor               # Check workspace health
arms doctor --fix         # Resync engine-owned files before reporting issues
arms release check        # Pre-release gate (non-zero exit on blocking issues)
arms init --monitor       # Live HTML debug HUD during init
```

### ARMS Orchestration & Intake
- **Workflow:** This project uses the ARMS (Architectural Runtime Management System). Follow the protocols in `.arms/RULES.md`.
- **Durable Tasks:** Every net-new issue, bug report, or feature request arriving through chat must be logged to `.arms/SESSION.md` using `arms task log` or `arms task update` before substantive execution begins. Use the standard task-table schema for all handoffs.
- **Routing Syntax:** When routing must be explicit, use `--assigned-agent` / `--active-skill` on task commands. `--agent` / `--skill` are accepted aliases.
- **Agent Handoff:** Updating `.arms/SESSION.md` does not itself switch the host tool into the specialist. After a row is assigned, hand the implementation turn to that agent: Claude Code runs the assigned agent as a subagent via its Task tool; Copilot CLI invokes `/agent <assigned-agent>`; other CLIs switch to the matching agent mirror. Run the specialist on the model tier shown in the row's `Model` column (resolved per platform by `model_routing.yaml`). Do not implement a specialist-assigned task inline as the orchestrator.
- **Brand Intake Display:** If `arms init` / `arms start` halts with `Awaiting Brand Context answers`, immediately read `.arms/BRAND_INTAKE.md` and display the compact answer block inline to the user. Do not merely tell the user to open the file unless they asked for a path-only summary.
- **Architecture Assessment (non-blocking):** `arms init` never blocks on the assessment — new projects bootstrap with fallback values immediately. When `.arms/RESEARCH_BRIEF.md` exists, offer the assessment conversationally: present the questions from `.arms/BRAND_INTAKE.md` as a numbered form, wait for answers, then follow `.arms/RESEARCH_BRIEF.md` — web-search the current best-fit stack for those answers (any stack, not just ARMS presets; verify latest stable names via search), and apply the resulting Stack Proposal with `arms intake --answers-text "<block>"`, then rerun `arms init`.
- **Verification:** No task is "Done" until validated by `arms-qa-agent` and pre-flight checks (lint, build, unit tests) pass.

---

## ARMS Protocol Quick Reference

> Full specification: `arms_engine/skills/arms-orchestrator/SKILL.md`

### CLI Commands
| Command | Action |
|---------|--------|
| `arms init` | Bootstrap workspace; halt for plan approval |
| `arms init yolo` | Full automation, skip initial approval |
| `arms init compress` | Bootstrap + compact SESSION/MEMORY |
| `arms run review` | Audit via QA, Security, Frontend |
| `arms fix issues` | Parse review report, generate tasks, delegate |
| `arms run deploy` | Pre-flight, sync DB, deploy |
| `arms run pipeline` | REVIEW → FIX → DEPLOY with gates |
| `arms run status` | Dump current tasks and blockers |
| `arms task log --task "..."` | Add a task row to SESSION.md |
| `arms task update --task-id N` | Update an existing task row |
| `arms task done --task-id N` | Archive a completed task |
| `arms memory draft` | Stage a MEMORY.md lesson for approval |
| `arms memory append` | Approve a staged draft and refresh SESSION.md |

### Session Bootstrap Files (Never Overwrite)
- `.arms/SESSION.md` — task table + execution mode
- `.arms/MEMORY.md` — append-only lessons
- `.arms/BRAND.md` — visual identity
- `.arms/RULES.md` — project conventions
- Project-owned: `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` — read only, never modify

### Agent/Skill Discovery (Post-Init)
- Agents: `.github/agents/` (Copilot), `.gemini/agents/` (Gemini), `.claude/agents/` (Claude Code)
- Skills: `.agents/skills/` + `.agents/skills.yaml` + `.agents/skills-index.md`; `.claude/commands/` + `.claude/skills.yaml` (Claude Code slash commands)
- `arms-docs` auto-updates README.md agent roster from `arms_engine/agents.yaml`
