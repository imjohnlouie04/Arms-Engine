import datetime
import os
import re
import shlex
import shutil
import sys
import tempfile
from collections import OrderedDict

from . import __version__
from .brand import infer_brand_context_from_project
from .skills import build_agent_skill_bindings, resolve_agents_with_skills
from .versioning import resolve_version

TOKEN_RE = re.compile(r"\S+")
DEFAULT_TOKEN_BUDGET_WARN_RATIO = 0.9
SESSION_TOKEN_BUDGET = 1400
MEMORY_ENTRY_ID_RE = re.compile(r"\[(memory-\d{8}-\d+)\]")
MEMORY_ENTRY_PREFIX_RE = re.compile(r"^\[(APPROVED|PENDING APPROVAL)\](?:\[(memory-\d{8}-\d+)\])?:\s*")
MEMORY_APPROVED_MARKER = "[APPROVED]"
MEMORY_PENDING_MARKER = "[PENDING APPROVAL]"


MEMORY_TEMPLATE = """# ARMS Project Memory

> Managed by ARMS Engine. This is a continuous learning file. APPEND only; never overwrite.
> Use `arms memory draft` to stage lessons for approval, then `arms memory append` to approve them and refresh `SESSION.md`.

## Project Context & MVP
## Primary Use Case & Implications
## Phase 2 Backlog
## Developer Preferences
## Known Bugs & Fixes
"""
RULES_TEMPLATE = """# ARMS Project Rules

> Managed by ARMS Engine. Replace these defaults with project-specific rules as the workspace matures.

## Structure & Naming
- Follow the existing project structure and naming conventions before introducing new patterns.
- Prefer feature- or domain-based organization over one-off utility sprawl.

## Code Quality
- Keep changes precise, type-safe, and explicit.
- Reuse existing helpers and conventions before adding new abstractions.
- Surface errors clearly; avoid silent fallbacks.

## Validation
- Use the project's existing build, lint, and test commands.
- Run the relevant validation before marking work complete.

## Agent Protocol
- Read `.arms/SESSION.md`, `.arms/BRAND.md`, and `.arms/MEMORY.md` before any task work.
- Treat `## Memory Signals` in `.arms/SESSION.md` as hot context, then open `.arms/MEMORY.md` when the work touches prior lessons, preferences, or known bugs.
- Ask the user for approval before updating `.arms/MEMORY.md`; only append after approval, and never overwrite it wholesale.
- After significant work, draft a concise memory lesson candidate and ask for approval before appending it to `.arms/MEMORY.md`.
- Keep `.arms/SESSION.md` synchronized with task progress and blockers.
"""
SESSION_ARCHIVE_TEMPLATE = """# ARMS Session Archive

> Managed by ARMS Engine. Append completed or cancelled work here; never delete history.
"""
MEMORY_SIGNAL_PREFIX = "- Read `.arms/MEMORY.md` before task work."
MEMORY_SIGNAL_SUFFIX = "- After significant work, draft a memory lesson candidate and ask approval before appending to `.arms/MEMORY.md`."
MEMORY_SIGNAL_EMPTY = "- No approved memory lessons recorded yet."
MEMORY_SUGGESTIONS_PREFIX = "- Review session-derived memory candidates before appending to `.arms/MEMORY.md`."
MEMORY_SUGGESTIONS_SUFFIX = "- Stage one with `arms memory draft --from-suggestion <n>` after review and approval."
MEMORY_SUGGESTIONS_EMPTY = "- No session-derived memory suggestions right now."


class SessionContextMismatchError(RuntimeError):
    def __init__(self, existing_root, current_root, existing_name="", current_name=""):
        self.existing_root = existing_root
        self.current_root = current_root
        self.existing_name = existing_name
        self.current_name = current_name
        super().__init__(
            f"Session file points to '{existing_root}' but current root is '{current_root}'."
        )


def setup_folders(project_root):
    agents_folders = [
        ".agents/skills",
    ]
    gemini_folders = [
        ".gemini/agents",
    ]
    github_folders = [
        ".github/agents",
        ".github/skills",
    ]
    arms_folders = [
        ".arms",
        ".arms/agent-outputs",
        ".arms/reports",
        ".arms/workflow",
    ]
    for folder in agents_folders + gemini_folders + github_folders + arms_folders:
        path = os.path.join(project_root, folder)
        os.makedirs(path, exist_ok=True)


def write_file_if_missing(path, content, label):
    if os.path.exists(path):
        return
    print(f"🧱 Scaffolding {label}...")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def bootstrap_runtime_files(project_root):
    write_file_if_missing(
        os.path.join(project_root, ".arms/SESSION_ARCHIVE.md"),
        SESSION_ARCHIVE_TEMPLATE,
        ".arms/SESSION_ARCHIVE.md",
    )
    write_file_if_missing(
        os.path.join(project_root, ".arms/MEMORY.md"),
        MEMORY_TEMPLATE,
        ".arms/MEMORY.md",
    )
    write_file_if_missing(
        os.path.join(project_root, ".arms/RULES.md"),
        RULES_TEMPLATE,
        ".arms/RULES.md",
    )


def migrate_legacy_state(project_root):
    migrations = [
        (
            "session log",
            os.path.join(project_root, ".gemini/SESSION.md"),
            os.path.join(project_root, ".arms/SESSION.md"),
        ),
        (
            "session log",
            os.path.join(project_root, "SESSION.md"),
            os.path.join(project_root, ".arms/SESSION.md"),
        ),
        (
            "session log",
            os.path.join(project_root, "session.md"),
            os.path.join(project_root, ".arms/SESSION.md"),
        ),
        (
            "session archive",
            os.path.join(project_root, ".gemini/SESSION_ARCHIVE.md"),
            os.path.join(project_root, ".arms/SESSION_ARCHIVE.md"),
        ),
        (
            "session archive",
            os.path.join(project_root, "SESSION_ARCHIVE.md"),
            os.path.join(project_root, ".arms/SESSION_ARCHIVE.md"),
        ),
        (
            "session archive",
            os.path.join(project_root, "session_archive.md"),
            os.path.join(project_root, ".arms/SESSION_ARCHIVE.md"),
        ),
        (
            "brand context",
            os.path.join(project_root, "brand-context.md"),
            os.path.join(project_root, ".arms/BRAND.md"),
        ),
        (
            "brand context",
            os.path.join(project_root, ".gemini/brand-context.md"),
            os.path.join(project_root, ".arms/BRAND.md"),
        ),
        (
            "brand context",
            os.path.join(project_root, ".gemini/BRAND.md"),
            os.path.join(project_root, ".arms/BRAND.md"),
        ),
        (
            "brand context",
            os.path.join(project_root, "BRAND.md"),
            os.path.join(project_root, ".arms/BRAND.md"),
        ),
        (
            "brand context",
            os.path.join(project_root, "brand.md"),
            os.path.join(project_root, ".arms/BRAND.md"),
        ),
        (
            "project memory",
            os.path.join(project_root, ".gemini/MEMORY.md"),
            os.path.join(project_root, ".arms/MEMORY.md"),
        ),
        (
            "project memory",
            os.path.join(project_root, "MEMORY.md"),
            os.path.join(project_root, ".arms/MEMORY.md"),
        ),
        (
            "project memory",
            os.path.join(project_root, "memory.md"),
            os.path.join(project_root, ".arms/MEMORY.md"),
        ),
        (
            "project rules",
            os.path.join(project_root, ".gemini/RULES.md"),
            os.path.join(project_root, ".arms/RULES.md"),
        ),
        (
            "project rules",
            os.path.join(project_root, "RULES.md"),
            os.path.join(project_root, ".arms/RULES.md"),
        ),
        (
            "project rules",
            os.path.join(project_root, "rules.md"),
            os.path.join(project_root, ".arms/RULES.md"),
        ),
        (
            "agent registry",
            os.path.join(project_root, "agents.yaml"),
            os.path.join(project_root, ".gemini/agents.yaml"),
        ),
        (
            "workflow mirror",
            os.path.join(project_root, ".gemini/workflow"),
            os.path.join(project_root, ".arms/workflow"),
        ),
        (
            "agent outputs",
            os.path.join(project_root, ".gemini/agent-outputs"),
            os.path.join(project_root, ".arms/agent-outputs"),
        ),
        (
            "reports",
            os.path.join(project_root, ".gemini/reports"),
            os.path.join(project_root, ".arms/reports"),
        ),
    ]

    for label, legacy_path, target_path in migrations:
        if not os.path.exists(legacy_path):
            continue
        if os.path.isdir(legacy_path):
            os.makedirs(target_path, exist_ok=True)
            moved_any = False
            for entry in os.listdir(legacy_path):
                legacy_entry = os.path.join(legacy_path, entry)
                target_entry = os.path.join(target_path, entry)
                if os.path.exists(target_entry):
                    print(
                        f"ℹ️  Found legacy {label} entry at "
                        f"{os.path.relpath(legacy_entry, project_root)}, but keeping existing "
                        f"{os.path.relpath(target_entry, project_root)} as authoritative."
                    )
                    continue
                print(
                    f"📦 Migrating legacy {label} entry from "
                    f"{os.path.relpath(legacy_entry, project_root)} to {os.path.relpath(target_entry, project_root)}..."
                )
                try:
                    shutil.move(legacy_entry, target_entry)
                    moved_any = True
                except (OSError, shutil.Error) as e:
                    print(
                        f"⚠️  Skipping migration of {os.path.relpath(legacy_entry, project_root)}: {str(e)}"
                    )
                    continue
            if not os.listdir(legacy_path):
                os.rmdir(legacy_path)
            elif not moved_any:
                print(
                    f"ℹ️  Found legacy {label} at {os.path.relpath(legacy_path, project_root)}, "
                    f"but keeping existing {os.path.relpath(target_path, project_root)} as authoritative."
                )
            continue
        if os.path.exists(target_path):
            print(
                f"ℹ️  Found legacy {label} at {os.path.relpath(legacy_path, project_root)}, "
                f"but keeping existing {os.path.relpath(target_path, project_root)} as authoritative."
            )
            continue

        print(
            f"📦 Migrating legacy {label} from "
            f"{os.path.relpath(legacy_path, project_root)} to {os.path.relpath(target_path, project_root)}..."
        )
        try:
            shutil.move(legacy_path, target_path)
        except (OSError, shutil.Error) as e:
            print(
                f"⚠️  Skipping migration of {os.path.relpath(legacy_path, project_root)}: {str(e)}"
            )


def is_missing_active_skill(value):
    normalized = value.strip().lower()
    return normalized in {"", "-", "—", "none", "n/a", "na"}


def score_task_skill_match(task_text, skill):
    task = task_text.lower()
    skill_name = skill["name"].lower()
    description = skill["description"].lower()
    score = 0

    if skill_name in task:
        score += 8

    task_tokens = {token for token in re.findall(r"[a-z0-9]+", task) if len(token) >= 3}
    skill_name_tokens = {token for token in re.findall(r"[a-z0-9]+", skill_name) if len(token) >= 3}
    skill_tokens = {token for token in re.findall(r"[a-z0-9]+", f"{skill_name} {description}") if len(token) >= 4}

    score += 4 * len(task_tokens & skill_name_tokens)
    score += len(task_tokens & skill_tokens)

    for task_token in task_tokens:
        for skill_token in skill_name_tokens:
            shared_prefix_length = len(os.path.commonprefix([task_token, skill_token]))
            if shared_prefix_length >= 5:
                score += 6
                break
    return score


def choose_task_active_skill(task_text, assigned_agent, current_skill, agent_skill_bindings, skill_catalog_by_name):
    if not is_missing_active_skill(current_skill):
        return current_skill

    bound_skills = list(agent_skill_bindings.get(assigned_agent, []))
    if not bound_skills:
        return "—"
    if len(bound_skills) == 1:
        return bound_skills[0]

    scored_skills = []
    for idx, skill_name in enumerate(bound_skills):
        skill = skill_catalog_by_name.get(skill_name, {"name": skill_name, "description": ""})
        scored_skills.append((score_task_skill_match(task_text, skill), idx, skill_name))

    scored_skills.sort(key=lambda item: (-item[0], item[1]))
    best_score, _, best_skill = scored_skills[0]
    if best_score <= 0:
        return bound_skills[0]
    if len(scored_skills) > 1 and best_score == scored_skills[1][0]:
        return bound_skills[0]
    return best_skill


def normalize_active_tasks_table(content, agent_skill_bindings=None, skill_catalog_by_name=None):
    new_header = "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |"
    new_divider = "|---|------|----------------|--------------|--------------|--------|"
    legacy_header = "| # | Task | Assigned Agent | Active Skill | Status |"
    legacy_divider = "|---|------|----------------|--------------|--------|"

    stripped = content.strip()
    if not stripped:
        return f"{new_header}\n{new_divider}"

    lines = stripped.splitlines()

    def normalize_row(line):
        row = line.strip()
        if not (row.startswith("|") and row.endswith("|")):
            return line
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) == 5:
            cells.insert(4, "None")
        if len(cells) != 6:
            return line
        if cells[0] == "#" and cells[1] == "Task":
            return new_header
        task_text = cells[1]
        assigned_agent = cells[2]
        current_skill = cells[3]
        cells[3] = choose_task_active_skill(
            task_text,
            assigned_agent,
            current_skill,
            agent_skill_bindings or {},
            skill_catalog_by_name or {},
        )
        return "| " + " | ".join(cells) + " |"

    if len(lines) >= 2 and lines[0].strip() == legacy_header and lines[1].strip() == legacy_divider:
        normalized = [new_header, new_divider]
        for line in lines[2:]:
            normalized.append(normalize_row(line))
        return "\n".join(normalized)

    normalized = []
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if index == 0 and stripped_line == new_header:
            normalized.append(new_header)
        elif index == 1 and stripped_line == new_divider:
            normalized.append(new_divider)
        else:
            normalized.append(normalize_row(line))

    return "\n".join(normalized)


def active_tasks_table_has_rows(content):
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 6:
            continue
        first_cell = cells[0].replace(" ", "")
        if cells[0] == "#" or set(first_cell) <= {"-"}:
            continue
        return True
    return False


def parse_active_task_rows(content):
    rows = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 6:
            continue
        first_cell = cells[0].replace(" ", "")
        if cells[0] == "#" or set(first_cell) <= {"-"}:
            continue
        rows.append(
            {
                "task": cells[1],
                "agent": cells[2],
                "skill": cells[3],
                "dependencies": cells[4],
                "status": cells[5],
            }
        )
    return rows


def filter_hot_task_rows(rows):
    return [
        row
        for row in rows
        if row["status"].strip().lower() not in {"done", "cancelled", "canceled"}
    ]


def render_compact_agent_roster(task_rows):
    seen = set()
    lines = []
    for row in task_rows:
        agent = row["agent"].strip()
        if not agent or agent in seen:
            continue
        seen.add(agent)
        lines.append(f"- {agent}")
    if not lines:
        lines.append("- arms-main-agent")
    lines.append("- Registry: .gemini/agents.yaml")
    return "\n".join(lines)


def render_compact_skill_roster(task_rows):
    seen = set()
    lines = []
    for row in task_rows:
        skill = row["skill"].strip()
        if skill.lower() in {"", "-", "—", "none", "n/a", "na"} or skill in seen:
            continue
        seen.add(skill)
        suffix = " [Active]" if skill == "arms-orchestrator" else ""
        lines.append(f"- {skill}{suffix}")
    if not lines:
        lines.append("- arms-orchestrator [Active]")
    lines.append("- Registry: .agents/skills.yaml")
    return "\n".join(lines)


def render_compact_skill_roster_with_inactive(task_rows, agent_skill_bindings):
    active_skills = []
    seen_active = set()
    for row in task_rows:
        skill = row["skill"].strip()
        if skill.lower() in {"", "-", "—", "none", "n/a", "na"} or skill in seen_active:
            continue
        seen_active.add(skill)
        active_skills.append(skill)

    lines = []
    if active_skills:
        for skill in active_skills:
            suffix = " [Active]" if skill == "arms-orchestrator" else ""
            lines.append(f"- {skill}{suffix}")
    else:
        lines.append("- arms-orchestrator [Active]")

    bound_skills = []
    seen_bound = set()
    for skills in (agent_skill_bindings or {}).values():
        for skill in skills:
            normalized_skill = (skill or "").strip()
            if normalized_skill.lower() in {"", "-", "—", "none", "n/a", "na"}:
                continue
            if normalized_skill in seen_bound:
                continue
            seen_bound.add(normalized_skill)
            bound_skills.append(normalized_skill)

    inactive_skills = [skill for skill in bound_skills if skill not in seen_active]
    if inactive_skills:
        lines.append("- Bound but inactive: {}".format(", ".join(inactive_skills)))

    lines.append("- Registry: .agents/skills.yaml")
    return "\n".join(lines)


def normalize_memory_signal(text, limit=180):
    collapsed = " ".join((text or "").split()).strip()
    collapsed = re.sub(r"^[-*]\s*", "", collapsed)
    if collapsed.startswith(MEMORY_PENDING_MARKER):
        return ""
    collapsed = MEMORY_ENTRY_PREFIX_RE.sub("", collapsed).strip()
    if not collapsed or collapsed.lower() in {"none", "n/a", "na", "tbd"}:
        return ""
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def collect_memory_signals(project_root, limit=4):
    memory_path = os.path.join(project_root, ".arms", "MEMORY.md")
    if not os.path.isfile(memory_path):
        return []

    _, sections = parse_markdown_sections(read_text_file(memory_path))
    signals = []
    seen = set()
    for title, body in sections.items():
        section_title = " ".join((title or "").split()).strip()
        for raw_line in (body or "").splitlines():
            normalized = normalize_memory_signal(raw_line)
            if not normalized:
                continue
            if normalized == section_title:
                continue
            candidate = f"{section_title}: {normalized}" if section_title else normalized
            if candidate in seen:
                continue
            seen.add(candidate)
            signals.append(candidate)
            if len(signals) >= limit:
                return signals
    return signals


def render_memory_signals(project_root):
    lines = [MEMORY_SIGNAL_PREFIX]
    memory_signals = collect_memory_signals(project_root)
    if memory_signals:
        lines.extend(f"- {item}" for item in memory_signals)
    else:
        lines.extend(extract_legacy_memory_signals(read_existing_memory_signals(project_root)))
    if len(lines) == 1:
        lines.append(MEMORY_SIGNAL_EMPTY)
    lines.append(MEMORY_SIGNAL_SUFFIX)
    return "\n".join(lines)


def summarize_memory_task_text(text, limit=96):
    collapsed = " ".join((text or "").split()).strip()
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3].rstrip() + "..."


def normalize_memory_suggestion_ref(value):
    normalized = (value or "").strip()
    if normalized.startswith("#"):
        normalized = normalized[1:].strip()
    return normalized


def choose_memory_suggestion_section(task_text, status, blockers_text, dependencies):
    normalized_task = (task_text or "").lower()
    normalized_status = (status or "").lower()
    normalized_dependencies = (dependencies or "").strip().lower()

    if normalized_status in {"blocked", "failed"}:
        return "Known Bugs & Fixes"
    if any(
        token in normalized_task
        for token in (
            "memory",
            "workflow",
            "routing",
            "prompt",
            "session",
            "task",
            "agent",
            "skill",
            "approval",
            "protocol",
            "convention",
        )
    ):
        return "Developer Preferences"
    if normalized_dependencies not in {"", "none", "-", "—", "n/a", "na"}:
        return "Phase 2 Backlog"
    if any(token in normalized_task for token in ("mvp", "brand", "product", "audience", "charter", "scope")):
        return "Project Context & MVP"
    if any(token in normalized_task for token in ("use case", "persona", "journey", "cta", "seo")):
        return "Primary Use Case & Implications"
    return "Developer Preferences"


def build_memory_suggestion_lesson(task_text, status, blockers_text, dependencies):
    normalized_task = summarize_memory_task_text(task_text).rstrip(".")
    normalized_status = (status or "").strip().lower()
    normalized_dependencies = (dependencies or "").strip()
    normalized_blockers = normalize_memory_signal(blockers_text, limit=140)

    if normalized_status in {"blocked", "failed"}:
        if normalized_blockers and normalized_blockers.lower() != "none":
            return "Document the root cause and final resolution for '{}' while the session blocker is still fresh: {}.".format(
                normalized_task,
                normalized_blockers,
            )
        return "Document the root cause and final resolution for '{}' while the failure path is still fresh.".format(
            normalized_task
        )
    if any(
        token in normalized_task.lower()
        for token in ("memory", "workflow", "routing", "prompt", "session", "task", "agent", "skill", "approval", "protocol")
    ):
        return "Capture the preferred orchestration pattern that emerged while implementing '{}' so future deep-dive work follows the same path.".format(
            normalized_task
        )
    if normalized_dependencies.lower() not in {"", "none", "-", "—", "n/a", "na"}:
        return "Record the dependency chain and follow-up rule for '{}' so deferred work stays traceable: {}.".format(
            normalized_task,
            normalized_dependencies,
        )
    return "Capture the reusable implementation decision behind '{}' if this session establishes a pattern worth repeating.".format(
        normalized_task
    )


def collect_memory_suggestions(active_task_rows, blockers_text="None", limit=3):
    suggestions = []
    seen = set()
    normalized_blockers = (blockers_text or "None").strip() or "None"

    for index, row in enumerate(active_task_rows, start=1):
        task_text = row.get("task", "").strip()
        status = row.get("status", "").strip()
        dependencies = row.get("dependencies", "").strip()
        if not task_text:
            continue
        blocker_context = normalized_blockers if (status or "").strip().lower() in {"blocked", "failed"} else "None"

        section = choose_memory_suggestion_section(task_text, status, blocker_context, dependencies)
        lesson = build_memory_suggestion_lesson(task_text, status, blocker_context, dependencies)
        key = (section, lesson)
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(
            {
                "index": str(len(suggestions) + 1),
                "section": section,
                "lesson": lesson,
                "source": "task #{} is {}".format(index, status or "Pending"),
            }
        )
        if len(suggestions) >= limit:
            return suggestions

    if normalized_blockers.lower() not in {"", "none"} and len(suggestions) < limit:
        blocker_lesson = "Document the blocker resolution rule for this session so repeated interruptions can be handled faster: {}.".format(
            normalize_memory_signal(normalized_blockers, limit=140)
        )
        key = ("Known Bugs & Fixes", blocker_lesson)
        if key not in seen:
            suggestions.append(
                {
                    "index": str(len(suggestions) + 1),
                    "section": "Known Bugs & Fixes",
                    "lesson": blocker_lesson,
                    "source": "session blocker",
                }
            )
    return suggestions


def render_memory_suggestions(active_task_rows, blockers_text="None"):
    lines = [MEMORY_SUGGESTIONS_PREFIX]
    suggestions = collect_memory_suggestions(active_task_rows, blockers_text=blockers_text)
    if suggestions:
        for suggestion in suggestions:
            lines.append(
                "- {}. [{}] {} Source: {}.".format(
                    suggestion["index"],
                    suggestion["section"],
                    suggestion["lesson"],
                    suggestion["source"],
                )
            )
    else:
        lines.append(MEMORY_SUGGESTIONS_EMPTY)
    lines.append(MEMORY_SUGGESTIONS_SUFFIX)
    return "\n".join(lines)


def load_session_rows_and_blockers(project_root):
    session_path = os.path.join(project_root, ".arms", "SESSION.md")
    if not os.path.isfile(session_path):
        return [], "None"
    _, sections = parse_markdown_sections(read_text_file(session_path))
    rows = filter_hot_task_rows(parse_active_task_rows(sections.get("Active Tasks", "")))
    blockers = (sections.get("Blockers", "None") or "None").strip() or "None"
    return rows, blockers


def resolve_memory_suggestion(project_root, suggestion_ref):
    normalized_ref = normalize_memory_suggestion_ref(suggestion_ref)
    rows, blockers = load_session_rows_and_blockers(project_root)
    derived = collect_memory_suggestions(rows, blockers_text=blockers)
    for suggestion in derived:
        if suggestion["index"] == normalized_ref:
            return suggestion
    return None


def read_existing_memory_signals(project_root):
    session_path = os.path.join(project_root, ".arms", "SESSION.md")
    if not os.path.isfile(session_path):
        return ""
    _, sections = parse_markdown_sections(read_text_file(session_path))
    return sections.get("Memory Signals", "")


def extract_legacy_memory_signals(content, limit=4):
    signals = []
    seen = set()
    for raw_line in (content or "").splitlines():
        normalized = normalize_memory_signal(raw_line)
        if not normalized:
            continue
        if raw_line.strip() in {
            MEMORY_SIGNAL_PREFIX,
            MEMORY_SIGNAL_EMPTY,
            MEMORY_SIGNAL_SUFFIX,
        }:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        signals.append(normalized)
        if len(signals) >= limit:
            break
    return signals


def estimate_token_count(text):
    return len(TOKEN_RE.findall(text or ""))


def assess_token_budget(content, budget, warn_ratio=DEFAULT_TOKEN_BUDGET_WARN_RATIO):
    tokens = estimate_token_count(content)
    warn_at = max(1, int(budget * warn_ratio))
    if tokens > budget:
        status = "fail"
    elif tokens >= warn_at:
        status = "warn"
    else:
        status = "ok"
    return {
        "status": status,
        "tokens": tokens,
        "budget": budget,
        "warn_at": warn_at,
    }


def format_token_budget_message(label, budget_assessment):
    status = budget_assessment["status"]
    if status == "fail":
        return (
            "⚠️  {} token budget exceeded: {} tokens (budget {}). "
            "Trim duplicated context or run `arms init compress`."
        ).format(label, budget_assessment["tokens"], budget_assessment["budget"])
    if status == "warn":
        return (
            "⚠️  {} token budget is nearing its limit: {} tokens "
            "(warning at {}, budget {})."
        ).format(
            label,
            budget_assessment["tokens"],
            budget_assessment["warn_at"],
            budget_assessment["budget"],
        )
    return (
        "✅ {} token budget healthy: {} / {} tokens."
    ).format(label, budget_assessment["tokens"], budget_assessment["budget"])


def extract_session_engine_version(session_content):
    match = re.search(r"- Engine Version: (.*)", session_content)
    return match.group(1).strip() if match else ""


def version_sort_key(value):
    cleaned = value.strip().lstrip("v")
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(.*)$", cleaned)
    if not match:
        return None

    major = int(match.group(1) or 0)
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    suffix = (match.group(4) or "").strip().lower()

    stage_rank = 0
    stage_number = 0
    if suffix:
        stage_match = re.search(r"(dev|a|alpha|b|beta|rc)[\.-]?(\d+)?", suffix)
        if stage_match:
            stage = stage_match.group(1)
            stage_number = int(stage_match.group(2) or 0)
            stage_rank = {
                "dev": -4,
                "a": -3,
                "alpha": -3,
                "b": -2,
                "beta": -2,
                "rc": -1,
            }.get(stage, -5)
        else:
            stage_rank = -5

    return (major, minor, patch, stage_rank, stage_number)


def compare_versions(left, right):
    left_key = version_sort_key(left)
    right_key = version_sort_key(right)
    if left_key is None or right_key is None:
        return 0
    if left_key < right_key:
        return -1
    if left_key > right_key:
        return 1
    return 0


def is_development_engine(arms_root):
    _ = arms_root
    version_text = (__version__ or "").lower()
    return (
        "dev" in version_text
        or "+" in version_text
        or version_text.startswith("0.0.0")
        or bool(re.fullmatch(r"[0-9a-f]{7,}", version_text))
    )


def normalize_engine_package_dir(path):
    candidate = os.path.abspath(path)
    if os.path.isfile(os.path.join(candidate, "agents.yaml")):
        return candidate

    package_dir = os.path.join(candidate, "arms_engine")
    if os.path.isfile(os.path.join(package_dir, "agents.yaml")):
        return package_dir
    return ""


def iter_local_engine_candidates(project_root, arms_root):
    candidate_paths = [
        arms_root,
        os.path.join(os.path.expanduser("~"), ".gemini", "Arms-Engine"),
        os.path.abspath(os.path.join(project_root, "..", "Arms-Engine")),
        os.path.join(project_root, "Arms-Engine"),
        project_root,
    ]
    seen = set()
    for path in candidate_paths:
        package_dir = normalize_engine_package_dir(path)
        if not package_dir or package_dir in seen:
            continue

        repo_root = os.path.dirname(package_dir)
        if not os.path.isdir(os.path.join(repo_root, ".git")):
            continue

        seen.add(package_dir)
        yield package_dir


def build_local_engine_rerun_command(project_root, arms_root, existing_engine_version):
    local_package_dir = ""
    local_version = ""
    for package_dir in iter_local_engine_candidates(project_root, arms_root):
        candidate_version = resolve_version(package_dir)
        if compare_versions(candidate_version, __version__) <= 0:
            continue
        if compare_versions(candidate_version, existing_engine_version) < 0:
            continue
        local_package_dir = package_dir
        local_version = candidate_version
        break

    if not local_package_dir:
        return None

    repo_root = os.path.dirname(local_package_dir)
    rerun_args = []
    raw_args = sys.argv[1:] or ["init"]
    skip_next = False
    for arg in raw_args:
        if skip_next:
            skip_next = False
            continue
        if arg == "--root":
            skip_next = True
            continue
        if arg.startswith("--root="):
            continue
        rerun_args.append(arg)
    rerun_args.extend(["--root", repo_root])

    command_parts = [
        f"PYTHONPATH={shlex.quote(repo_root)}",
        shlex.quote(sys.executable),
        "-m",
        "arms_engine.init_arms",
        *[shlex.quote(arg) for arg in rerun_args],
    ]
    return {
        "repo_root": repo_root,
        "version": local_version,
        "command": " ".join(command_parts),
    }


def enforce_engine_version_guard(project_root, arms_root, allow_engine_downgrade=False):
    session_path = os.path.join(project_root, ".arms/SESSION.md")
    if not os.path.exists(session_path):
        return

    with open(session_path, "r", encoding="utf-8", errors="ignore") as f:
        existing_content = f.read()

    existing_engine_version = extract_session_engine_version(existing_content)
    if not existing_engine_version:
        return

    if compare_versions(existing_engine_version, __version__) <= 0:
        return

    if allow_engine_downgrade:
        print(
            f"⚠️  Allowing engine downgrade override: project was last synced with {existing_engine_version}, "
            f"current engine is {__version__}."
        )
        return

    if is_development_engine(arms_root):
        print(
            f"⚠️  Project was last synced with ARMS Engine {existing_engine_version}, while the current "
            f"development engine reports {__version__}. Continuing because a development version is in use."
        )
        return

    print("❌ ERROR: This project was last synced by a newer ARMS Engine.")
    print(f"   Project engine version: {existing_engine_version}")
    print(f"   Current engine version: {__version__}")
    print("   To avoid downgrading project state, update the engine and rerun `arms init`.")
    print()
    local_checkout = build_local_engine_rerun_command(project_root, arms_root, existing_engine_version)
    if local_checkout:
        print("   A newer local engine checkout is available:")
        print(f"     {local_checkout['repo_root']} (version {local_checkout['version']})")
        print()
        print("   To rerun init with that checkout's code instead of the older installed CLI:")
        print(f"     {local_checkout['command']}")
        print()
    print("   Standard install:")
    print("     pipx upgrade arms-engine")
    print()
    print("   Development checkout:")
    print("     git pull")
    print("     pip install -e .")
    print()
    print("   If you intentionally want to proceed with an older engine, rerun with:")
    print("     arms init --allow-engine-downgrade")
    raise SystemExit(1)


def detect_execution_mode():
    override = os.getenv("ARMS_EXECUTION_MODE", "").strip().lower()
    if override in {"parallel", "simulated"}:
        return override.capitalize()

    parallel_env_markers = (
        "COPILOT_CLI",
        "GITHUB_COPILOT_CLI",
        "GEMINI_CLI",
        "CLAUDECODE",
        "CLAUDE_CODE",
        "OPENAI_CODEX_CLI",
    )
    if any(os.getenv(marker) for marker in parallel_env_markers):
        return "Parallel"
    return "Simulated"


def write_text_atomic(path, content):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    handle = None
    temp_path = None
    try:
        handle = tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=directory,
            delete=False,
        )
        temp_path = handle.name
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        handle = None
        os.replace(temp_path, path)
    finally:
        if handle is not None:
            handle.close()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def read_text_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as file_handle:
        return file_handle.read()


def parse_markdown_sections(content):
    preamble_lines = []
    sections = OrderedDict()
    current_title = None
    current_lines = []

    for line in content.splitlines():
        if line.startswith("## "):
            if current_title is not None:
                sections[current_title] = "\n".join(current_lines).strip()
            current_title = line[3:].strip()
            current_lines = []
            continue
        if current_title is None:
            preamble_lines.append(line)
        else:
            current_lines.append(line)

    if current_title is not None:
        sections[current_title] = "\n".join(current_lines).strip()

    return "\n".join(preamble_lines).strip(), sections


def write_markdown_sections(path, preamble, sections):
    parts = [preamble.strip()]
    for title, body in sections.items():
        normalized_body = (body or "").strip()
        parts.append(f"## {title}")
        if normalized_body:
            parts.append(normalized_body)
    content = "\n\n".join(part for part in parts if part).rstrip() + "\n"
    write_text_atomic(path, content)


def read_existing_session_context(session_path):
    existing_content = ""
    existing_root = None
    existing_name = None
    if os.path.exists(session_path):
        existing_content = read_text_file(session_path)
        root_match = re.search(r"- Project Root: (.*)", existing_content)
        if root_match:
            existing_root = root_match.group(1).strip()
        name_match = re.search(r"- Project Name: (.*)", existing_content)
        if name_match:
            existing_name = name_match.group(1).strip()
    return existing_content, existing_root, existing_name


def extract_current_project_name(project_root, existing_name=""):
    current_name = ""
    brand_path = os.path.join(project_root, ".arms/BRAND.md")
    if os.path.exists(brand_path):
        with open(brand_path, "r", encoding="utf-8", errors="ignore") as f:
            brand_content = f.read()
        name_match = re.search(r"- \*\*Project Name:\*\* (.*)", brand_content)
        if name_match:
            current_name = name_match.group(1).strip().strip("[]")

    if current_name and current_name.lower() not in {"unknown", "tbd"}:
        return current_name

    preserved_name = (existing_name or "").strip()
    if preserved_name and preserved_name.lower() not in {"unknown", "tbd"}:
        return preserved_name

    inferred_name = ""
    try:
        inferred_name = (infer_brand_context_from_project(project_root).get("project_name") or "").strip()
    except Exception:
        inferred_name = ""
    if inferred_name and inferred_name.lower() not in {"unknown", "tbd"}:
        return inferred_name

    directory_name = os.path.basename(os.path.abspath(project_root)).strip()
    return directory_name or "Project"


def update_session(project_root, arms_root, skills_list="", agents_list="", yolo=False, startup_tasks_content="", context_overwrite=None):
    print("📄 Updating session log...")
    session_path = os.path.join(project_root, ".arms/SESSION.md")

    existing_content, existing_root, existing_name = read_existing_session_context(session_path)
    current_name = extract_current_project_name(project_root, existing_name=existing_name or "")

    if existing_root and os.path.abspath(existing_root) != os.path.abspath(project_root):
        print(f"⚠️  Context Mismatch: Session file points to '{existing_root}'")
        print(f"   Current root: {project_root}")
        if yolo:
            print("🤖 [YOLO] Auto-accepting: Overwriting session with current project context.")
        elif context_overwrite is None:
            raise SessionContextMismatchError(
                existing_root=existing_root,
                current_root=project_root,
                existing_name=existing_name or "",
                current_name=current_name,
            )
        elif not context_overwrite:
            print("Aborting to preserve session state.")
            return False

    resolved_agents, skill_catalog, _ = resolve_agents_with_skills(arms_root, announce=False)
    agent_skill_bindings = build_agent_skill_bindings(resolved_agents)
    skill_catalog_by_name = {
        skill["name"]: skill
        for skill in skill_catalog
    }
    normalized_startup_tasks_content = startup_tasks_content
    if startup_tasks_content:
        normalized_startup_tasks_content = normalize_active_tasks_table(
            startup_tasks_content,
            agent_skill_bindings=agent_skill_bindings,
            skill_catalog_by_name=skill_catalog_by_name,
        )

    tasks_match = re.search(r"(## Active Tasks.*)", existing_content, re.DOTALL)
    active_tasks_content = ""
    blockers_content = "None"
    if tasks_match:
        tasks_content_raw = tasks_match.group(1)
        header_pattern = r"## (Active Tasks|Completed Tasks|Blockers)"
        parts = re.split(header_pattern, tasks_content_raw)
        seen_headers = set()
        new_tasks_content = []
        for i in range(1, len(parts), 2):
            header = parts[i]
            content = parts[i + 1].strip()
            if header not in seen_headers:
                if content:
                    if header == "Active Tasks":
                        content = normalize_active_tasks_table(
                            content,
                            agent_skill_bindings=agent_skill_bindings,
                            skill_catalog_by_name=skill_catalog_by_name,
                        )
                        if normalized_startup_tasks_content and not active_tasks_table_has_rows(content):
                            content = normalized_startup_tasks_content
                        active_tasks_content = content
                    if header == "Blockers":
                        blockers_content = content or "None"
                    new_tasks_content.append(f"## {header}\n{content}")
                else:
                    if header == "Active Tasks":
                        active_tasks_content = normalized_startup_tasks_content or (
                            "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
                            "|---|------|----------------|--------------|--------------|--------|"
                        )
                        new_tasks_content.append(f"## {header}\n{active_tasks_content}")
                    elif header == "Completed Tasks":
                        new_tasks_content.append(f"## {header}\n- None")
                    elif header == "Blockers":
                        blockers_content = "None"
                        new_tasks_content.append(f"## {header}\nNone")
                seen_headers.add(header)

        for req in ["Active Tasks", "Completed Tasks", "Blockers"]:
            if req not in seen_headers:
                if req == "Active Tasks":
                    active_tasks_content = normalized_startup_tasks_content or (
                        "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n"
                        "|---|------|----------------|--------------|--------------|--------|"
                    )
                    new_tasks_content.append(f"## {req}\n{active_tasks_content}")
                elif req == "Completed Tasks":
                    new_tasks_content.append(f"## {req}\n- None")
                elif req == "Blockers":
                    blockers_content = "None"
                    new_tasks_content.append(f"## {req}\nNone")

        tasks_content = "\n\n".join(new_tasks_content)
    else:
        active_tasks_content = normalized_startup_tasks_content or """| # | Task | Assigned Agent | Active Skill | Dependencies | Status |
|---|------|----------------|--------------|--------------|--------|"""
        tasks_content = f"""## Active Tasks
{active_tasks_content}

## Completed Tasks
- None

## Blockers
None"""

    hot_task_rows = filter_hot_task_rows(parse_active_task_rows(active_tasks_content))
    compact_agents_list = render_compact_agent_roster(hot_task_rows)
    compact_skills_list = render_compact_skill_roster_with_inactive(hot_task_rows, agent_skill_bindings)
    memory_signals = render_memory_signals(project_root)
    memory_suggestions = render_memory_suggestions(hot_task_rows, blockers_text=blockers_content)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    exec_mode = detect_execution_mode()
    yolo_status = "Enabled" if yolo else "Disabled"

    content = f"""# ARMS Session Log
Generated: {now}

## Environment
- ARMS Root: {arms_root}
- Engine Version: {__version__}
- Project Root: {project_root}
- Project Name: {current_name}
- Execution Mode: {exec_mode}
- YOLO Mode: {yolo_status}

## Active Agents
{compact_agents_list}

## Active Skills
{compact_skills_list}

## Memory Signals
{memory_signals}

## Memory Suggestions
{memory_suggestions}

{tasks_content}"""

    write_text_atomic(session_path, content)
    session_budget = assess_token_budget(content, SESSION_TOKEN_BUDGET)
    if session_budget["status"] != "ok":
        print(format_token_budget_message(".arms/SESSION.md", session_budget))
    return True
