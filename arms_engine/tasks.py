import json
import os
import re
import time

import yaml

from .paths import WorkspacePaths
from .protocols import (
    KEEP_EXISTING,
    parse_task_rows,
    render_archive_diagnostics_section,
    render_task_table,
    renumber_rows,
    split_archivable_rows,
    update_protocol_session,
)
from .session import parse_markdown_sections, read_text_file
from .skills import build_agent_skill_bindings, resolve_agents_with_skills


TASK_COMMANDS = {
    ("task", "log"): "log",
    ("task", "update"): "update",
    ("task", "done"): "done",
    ("task", "list"): "list",
    ("task", "status"): "list",
}
STATUS_ALIASES = {
    "pending": "Pending",
    "in progress": "In Progress",
    "in-progress": "In Progress",
    "pre-flight": "Pre-Flight",
    "preflight": "Pre-Flight",
    "blocked": "Blocked",
    "failed": "Failed",
    "done": "Done",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
}
_ROUTING_YAML = os.path.join(os.path.dirname(__file__), "routing.yaml")
_ROUTING_RULES_FALLBACK = (
    (
        "arms-main-agent",
        (
            "session.md",
            "task table",
            "task ledger",
            "agent routing",
            "memory workflow",
            "orchestration",
            "orchestrator",
            "protocol command",
            "arms init",
            "engine workflow",
        ),
    ),
    (
        "arms-product-agent",
        (
            "requirements",
            "scope",
            "prd",
            "user story",
            "user stories",
            "prioritization",
            "prioritize",
            "roadmap",
            "success metric",
            "product charter",
            "feature brief",
        ),
    ),
    (
        "arms-media-agent",
        (
            "logo",
            "wordmark",
            "brand icon",
            "image",
            "images",
            "illustration",
            "graphic",
            "hero image",
            "asset",
            "assets",
        ),
    ),
    (
        "arms-security-agent",
        (
            "security",
            "owasp",
            "vulnerability",
            "vulnerabilities",
            "secret",
            "secrets",
            "pii",
            "csrf",
            "xss",
            "injection",
            "auth audit",
            "security audit",
            "permission audit",
            "rls policy",
        ),
    ),
    (
        "arms-qa-agent",
        (
            "test",
            "tests",
            "testing",
            "qa",
            "e2e",
            "integration test",
            "regression",
            "a11y",
            "accessibility",
            "pre-flight",
        ),
    ),
    (
        "arms-devops-agent",
        (
            "deploy",
            "deployment",
            "ci",
            "cd",
            "pipeline",
            "workflow",
            "infra",
            "infrastructure",
            "docker",
            "container",
            "kubernetes",
            "vercel",
            "release build",
        ),
    ),
    (
        "arms-seo-agent",
        (
            "seo",
            "meta tag",
            "metadata",
            "open graph",
            "structured data",
            "schema markup",
            "core web vitals",
            "lighthouse",
            "performance",
            "web vitals",
        ),
    ),
    (
        "arms-data-agent",
        (
            "database",
            "schema",
            "migration",
            "migrations",
            "query",
            "postgres",
            "sql",
            "supabase",
            "table",
            "index",
        ),
    ),
    (
        "arms-frontend-agent",
        (
            "ui",
            "ux",
            "frontend",
            "component",
            "components",
            "page",
            "layout",
            "responsive",
            "mobile",
            "sidebar",
            "navbar",
            "hero",
            "theme",
            "styling",
            "css",
            "visual polish",
        ),
    ),
    (
        "arms-backend-agent",
        (
            "backend",
            "api",
            "endpoint",
            "service",
            "auth",
            "login",
            "logout",
            "session",
            "token",
            "model",
            "business logic",
            "server",
        ),
    ),
)


def _load_routing_rules():
    """Load routing rules from routing.yaml; fall back to hardcoded defaults."""
    try:
        with open(_ROUTING_YAML, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        routing = data.get("routing", {})
        return tuple(
            (agent, tuple(kw for kw in entry.get("keywords", [])))
            for agent, entry in routing.items()
        )
    except Exception:  # noqa: BLE001 — broad catch for missing/malformed YAML
        return _ROUTING_RULES_FALLBACK


ROUTING_RULES = _load_routing_rules()
ROUTING_RULE_PATTERNS = tuple(
    (
        agent_name,
        tuple(re.compile(r"\b{}\b".format(re.escape(pattern))) for pattern in patterns),
    )
    for agent_name, patterns in ROUTING_RULES
)


def identify_task_command(command_parts: tuple) -> str:
    """Return the normalised task sub-command name or empty string if unrecognised."""
    normalized = tuple(part.strip().lower() for part in command_parts if part.strip())
    return TASK_COMMANDS.get(normalized, "")


def check_task_log_debounce(project_root: str, normalized_task: str, debounce_seconds: int = 2) -> bool:
    """Check if a task was recently logged (within debounce window).

    This prevents rapid duplicate calls from the IDE/Copilot extension from
    creating duplicate task rows. Returns True if the task was recently logged
    and should be skipped; False if it's safe to log it.

    Args:
        project_root: Project root directory.
        normalized_task: Normalized task text (already lowercased/stripped).
        debounce_seconds: Window in seconds to consider as "recent" (default 2).

    Returns:
        True if task was recently logged (skip it), False if safe to log.
    """
    wp = WorkspacePaths(project_root)
    lock_path = wp.task_log_lock

    if not os.path.exists(lock_path):
        return False

    try:
        with open(lock_path, "r") as f:
            lock_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return False

    last_task = lock_data.get("task", "")
    last_timestamp = lock_data.get("timestamp", 0)
    elapsed = time.time() - last_timestamp

    if elapsed > debounce_seconds:
        return False

    return last_task.casefold() == normalized_task.casefold()


def update_task_log_debounce(project_root: str, normalized_task: str) -> None:
    """Record a task log call for debounce checking.

    Args:
        project_root: Project root directory.
        normalized_task: Normalized task text.
    """
    wp = WorkspacePaths(project_root)
    lock_path = wp.task_log_lock

    os.makedirs(wp.arms_dir, exist_ok=True)
    lock_data = {
        "task": normalized_task,
        "timestamp": time.time(),
    }
    try:
        with open(lock_path, "w") as f:
            json.dump(lock_data, f)
    except IOError:
        pass  # Silently ignore lock file write errors


def handle_task_command(
    project_root: str,
    arms_root: str,
    command_name: str,
    task: str = "",
    task_id: str = "",
    assigned_agent: str = "",
    active_skill: str = "",
    dependencies: str = "",
    status: str = "",
) -> None:
    """Dispatch a ``task log``, ``task update``, or ``task done`` command and print a structured response."""
    try:
        _, sections = load_session_sections(project_root)
    except FileNotFoundError:
        emit_task_response(
            command_name,
            project_root,
            updates="None",
            action_lines=[
                "Structured task commands require an initialized workspace. Run `arms init` first.",
            ],
            task_table="",
            archive_diagnostics="",
            next_step="Initialize the workspace first with `arms init`, then rerun the task command. → HALT",
        )
        raise SystemExit(1)

    agent_names, agent_skill_bindings, skill_catalog_by_name = load_routing_context(arms_root)
    active_rows = parse_task_rows(sections.get("Active Tasks", ""))

    if command_name == "list":
        table = list_task_rows(active_rows, arms_root)
        emit_task_response(
            command_name,
            project_root,
            updates="None",
            action_lines=["Current active task table from `.arms/SESSION.md`:"],
            task_table=table,
            archive_diagnostics="",
            next_step="No changes were made. → HALT",
        )
        return

    try:
        if command_name == "log":
            normalized_task = normalize_text(task)
            
            if check_task_log_debounce(project_root, normalized_task):
                emit_task_response(
                    command_name,
                    project_root,
                    updates="None",
                    action_lines=[
                        f"Task recently logged (within 2 seconds): `{normalized_task[:60]}...`",
                        "Skipping duplicate to prevent rapid IDE re-execution from creating duplicates.",
                    ],
                    task_table=render_task_table(active_rows, arms_root),
                    archive_diagnostics="",
                    next_step="The task is already in the ledger. Continue work or await agent response. → HALT",
                )
                return

            result = log_task_row(
                active_rows,
                arms_root,
                agent_names,
                agent_skill_bindings,
                skill_catalog_by_name,
                task=task,
                assigned_agent=assigned_agent,
                active_skill=active_skill,
                dependencies=dependencies,
                status=status,
            )
            
            update_task_log_debounce(project_root, normalized_task)
        elif command_name == "update":
            result = update_task_row(
                active_rows,
                arms_root,
                agent_names,
                agent_skill_bindings,
                skill_catalog_by_name,
                task_id=task_id,
                task=task,
                assigned_agent=assigned_agent,
                active_skill=active_skill,
                dependencies=dependencies,
                status=status,
            )
        else:
            result = complete_task_row(
                active_rows,
                task_id=task_id,
            )
    except TaskCommandError as error:
        emit_task_response(
            command_name,
            project_root,
            updates="None",
            action_lines=[str(error)],
            task_table="",
            archive_diagnostics="",
            next_step="Resolve the input issue and rerun the task command. → HALT",
        )
        raise SystemExit(1)

    archive_diagnostics = update_protocol_session(
        project_root,
        arms_root,
        result["rows"],
        blockers=KEEP_EXISTING,
        archive_context=result["archive_context"],
    )
    remaining_rows, _ = split_archivable_rows(result["rows"])

    emit_task_response(
        command_name,
        project_root,
        updates="Updated `.arms/SESSION.md`{}.".format(
            " and `.arms/SESSION_ARCHIVE.md`" if archive_diagnostics else ""
        ),
        action_lines=result["action_lines"],
        task_table=render_task_table(remaining_rows, arms_root),
        archive_diagnostics=render_archive_diagnostics_section(archive_diagnostics),
        next_step=result["next_step"],
    )


def log_task_row(
    active_rows,
    arms_root,
    agent_names,
    agent_skill_bindings,
    skill_catalog_by_name,
    task="",
    assigned_agent="",
    active_skill="",
    dependencies="",
    status="",
):
    normalized_task = normalize_text(task)
    if not normalized_task:
        raise TaskCommandError("`arms task log` requires `--task`.")

    rows = renumber_rows(active_rows)
    existing_index = find_task_index_by_text(rows, normalized_task)
    if existing_index is not None:
        row = rows[existing_index]
        if assigned_agent.strip():
            validated_agent = validate_agent_name(assigned_agent, agent_names)
            validate_skill_name(validated_agent, active_skill, agent_skill_bindings, skill_catalog_by_name)
            row["Assigned Agent"] = validated_agent
            row["Active Skill"] = normalize_skill_value(active_skill, missing_default="—")
        elif active_skill.strip():
            validate_skill_name(row["Assigned Agent"], active_skill, agent_skill_bindings, skill_catalog_by_name)
            row["Active Skill"] = normalize_skill_value(active_skill, missing_default="—")
        if dependencies.strip():
            dep_ids = parse_dependency_ids(normalize_dependencies(dependencies))
            cycle = detect_dependency_cycle(rows, row["#"], dep_ids)
            if cycle:
                raise TaskCommandError(
                    "Setting dependencies `{}` on task `#{}` would create a cycle: {}.".format(
                        dependencies, row["#"], " → ".join(cycle)
                    )
                )
            row["Dependencies"] = normalize_dependencies(dependencies)
        if status.strip():
            row["Status"] = normalize_status(status)
        row["Task"] = normalized_task
        finalized_rows = finalize_rows(rows, arms_root)
        finalized_row = finalized_rows[existing_index]
        return {
            "rows": finalized_rows,
            "archive_context": "Task command: update existing row",
            "action_lines": [
                "Updated existing task row `#{}` instead of duplicating it.".format(finalized_row["#"]),
                "- Task: `{}`".format(finalized_row["Task"]),
                "- Assigned Agent: `{}`".format(finalized_row["Assigned Agent"]),
                "- Active Skill: `{}`".format(finalized_row["Active Skill"]),
                "- Status: `{}`".format(finalized_row["Status"]),
            ],
            "next_step": "Task ledger updated. Continue work with `arms task update --task-id {}` as progress changes. → HALT".format(
                finalized_row["#"]
            ),
        }

    resolved_agent = validate_agent_name(assigned_agent, agent_names) if assigned_agent.strip() else infer_agent_from_task(normalized_task)
    validate_skill_name(resolved_agent, active_skill, agent_skill_bindings, skill_catalog_by_name)
    new_task_id = str(len(rows) + 1)
    normalized_dep_value = normalize_dependencies(dependencies)
    if dependencies.strip():
        dep_ids = parse_dependency_ids(normalized_dep_value)
        # The new row isn't in `rows` yet; temporarily add a stub so the graph is complete.
        stub_rows = list(rows) + [{"#": new_task_id, "Dependencies": normalized_dep_value}]
        cycle = detect_dependency_cycle(stub_rows, new_task_id, dep_ids)
        if cycle:
            raise TaskCommandError(
                "Setting dependencies `{}` on new task would create a cycle: {}.".format(
                    dependencies, " → ".join(cycle)
                )
            )
    rows.append(
        {
            "#": new_task_id,
            "Task": normalized_task,
            "Assigned Agent": resolved_agent,
            "Active Skill": normalize_skill_value(active_skill, missing_default="—"),
            "Dependencies": normalized_dep_value,
            "Status": normalize_status(status or "Pending"),
        }
    )
    finalized_rows = finalize_rows(rows, arms_root)
    finalized_row = finalized_rows[-1]
    return {
        "rows": finalized_rows,
        "archive_context": "Task command: log row",
        "action_lines": [
            "Logged a new task row in `.arms/SESSION.md`.",
            "- Task ID: `{}`".format(finalized_row["#"]),
            "- Task: `{}`".format(finalized_row["Task"]),
            "- Assigned Agent: `{}`".format(finalized_row["Assigned Agent"]),
            "- Active Skill: `{}`".format(finalized_row["Active Skill"]),
            "- Status: `{}`".format(finalized_row["Status"]),
        ],
        "next_step": "Task logged. Advance it with `arms task update --task-id {}` or archive it with `arms task done --task-id {}` when complete. → HALT".format(
            finalized_row["#"],
            finalized_row["#"],
        ),
    }


def update_task_row(
    active_rows,
    arms_root,
    agent_names,
    agent_skill_bindings,
    skill_catalog_by_name,
    task_id="",
    task="",
    assigned_agent="",
    active_skill="",
    dependencies="",
    status="",
):
    normalized_task_id = normalize_text(task_id)
    if not normalized_task_id:
        raise TaskCommandError("`arms task update` requires `--task-id`.")
    if not any(value.strip() for value in (task, assigned_agent, active_skill, dependencies, status)):
        raise TaskCommandError(
            "`arms task update` requires at least one field to change (`--task`, `--assigned-agent`, `--active-skill`, `--dependencies`, or `--status`)."
        )

    rows = renumber_rows(active_rows)
    task_index = find_task_index_by_id(rows, normalized_task_id)
    if task_index is None:
        raise TaskCommandError("No active task row matched `--task-id {}`.".format(normalized_task_id))

    row = rows[task_index]
    if task.strip():
        row["Task"] = normalize_text(task)

    if assigned_agent.strip():
        validated_agent = validate_agent_name(assigned_agent, agent_names)
        validate_skill_name(validated_agent, active_skill, agent_skill_bindings, skill_catalog_by_name)
        row["Assigned Agent"] = validated_agent
        row["Active Skill"] = normalize_skill_value(active_skill, missing_default="—")
    elif active_skill.strip():
        validate_skill_name(row["Assigned Agent"], active_skill, agent_skill_bindings, skill_catalog_by_name)
        row["Active Skill"] = normalize_skill_value(active_skill, missing_default="—")

    if dependencies.strip():
        dep_ids = parse_dependency_ids(normalize_dependencies(dependencies))
        cycle = detect_dependency_cycle(rows, row["#"], dep_ids)
        if cycle:
            raise TaskCommandError(
                "Setting dependencies `{}` on task `#{}` would create a cycle: {}.".format(
                    dependencies, row["#"], " → ".join(cycle)
                )
            )
        row["Dependencies"] = normalize_dependencies(dependencies)
    if status.strip():
        row["Status"] = normalize_status(status)

    finalized_rows = finalize_rows(rows, arms_root)
    finalized_row = finalized_rows[task_index]
    archived = finalized_row["Status"].strip().lower() in {"done", "cancelled", "canceled"}
    next_step = (
        "Task archived. Continue with the next active row or log a new task when more work appears. → HALT"
        if archived
        else "Task row updated. Continue advancing it with `arms task update --task-id {}` or archive it with `arms task done --task-id {}`. → HALT".format(
            finalized_row["#"],
            finalized_row["#"],
        )
    )
    return {
        "rows": finalized_rows,
        "archive_context": "Task command: update row",
        "action_lines": [
            "Updated task row `#{}`.".format(finalized_row["#"]),
            "- Task: `{}`".format(finalized_row["Task"]),
            "- Assigned Agent: `{}`".format(finalized_row["Assigned Agent"]),
            "- Active Skill: `{}`".format(finalized_row["Active Skill"]),
            "- Dependencies: `{}`".format(finalized_row["Dependencies"]),
            "- Status: `{}`".format(finalized_row["Status"]),
        ],
        "next_step": next_step,
    }


def list_task_rows(active_rows, arms_root):
    """Return the current active task table as a formatted string without modifying any files."""
    rows = renumber_rows(active_rows)
    if not rows:
        return "No active tasks in `.arms/SESSION.md`."
    return render_task_table(rows, arms_root)


def complete_task_row(active_rows, task_id=""):
    normalized_task_id = normalize_text(task_id)
    if not normalized_task_id:
        raise TaskCommandError("`arms task done` requires `--task-id`.")

    rows = renumber_rows(active_rows)
    task_index = find_task_index_by_id(rows, normalized_task_id)
    if task_index is None:
        raise TaskCommandError("No active task row matched `--task-id {}`.".format(normalized_task_id))

    row = rows[task_index]
    row["Status"] = "Done"
    finalized_rows = renumber_rows(rows)
    finalized_row = finalized_rows[task_index]
    return {
        "rows": finalized_rows,
        "archive_context": "Task command: complete row",
        "action_lines": [
            "Marked task row `#{}` as `Done` and moved it out of hot context.".format(finalized_row["#"]),
            "- Task: `{}`".format(finalized_row["Task"]),
            "- Assigned Agent: `{}`".format(finalized_row["Assigned Agent"]),
        ],
        "next_step": "Task archived. Continue with the next active row or log a new task when more work appears. → HALT",
    }


def load_routing_context(arms_root):
    resolved_agents, skill_catalog, _ = resolve_agents_with_skills(arms_root, announce=False)
    agent_names = {agent["name"] for agent in resolved_agents}
    return agent_names, build_agent_skill_bindings(resolved_agents), {skill["name"]: skill for skill in skill_catalog}


def load_session_sections(project_root):
    session_path = os.path.join(project_root, ".arms", "SESSION.md")
    if not os.path.exists(session_path):
        raise FileNotFoundError(session_path)
    return parse_markdown_sections(read_text_file(session_path))


def finalize_rows(rows, arms_root):
    return parse_task_rows(render_task_table(rows, arms_root))


def infer_agent_from_task(task_text):
    normalized = task_text.lower()
    for agent_name, patterns in ROUTING_RULE_PATTERNS:
        if any(pattern.search(normalized) for pattern in patterns):
            return agent_name
    return "arms-main-agent"


def find_task_index_by_text(rows, task_text):
    normalized = task_text.casefold()
    for index, row in enumerate(rows):
        if row.get("Task", "").strip().casefold() == normalized:
            return index
    return None


def find_task_index_by_id(rows, task_id):
    normalized = task_id.strip()
    for index, row in enumerate(rows):
        if row.get("#", "").strip() == normalized:
            return index
    return None


def validate_agent_name(agent_name, agent_names):
    normalized = normalize_text(agent_name)
    if normalized not in agent_names:
        raise TaskCommandError("Unknown agent `{}`. Choose one defined in `arms_engine/agents.yaml`.".format(normalized))
    return normalized


def validate_skill_name(agent_name, skill_name, agent_skill_bindings, skill_catalog_by_name):
    normalized_skill = normalize_text(skill_name)
    if not normalized_skill:
        return
    if normalized_skill not in skill_catalog_by_name:
        raise TaskCommandError("Unknown skill `{}`. Choose one from the synced skill registry.".format(normalized_skill))
    bound_skills = list(agent_skill_bindings.get(agent_name, []))
    if not bound_skills:
        raise TaskCommandError("Agent `{}` does not have a bound skill, so `--active-skill` must be omitted.".format(agent_name))
    if normalized_skill not in bound_skills:
        raise TaskCommandError(
            "Skill `{}` is not bound to `{}`. Use one of: {}.".format(
                normalized_skill,
                agent_name,
                ", ".join(bound_skills),
            )
        )


def normalize_text(value):
    return " ".join((value or "").split()).strip()


def normalize_skill_value(value, missing_default=""):
    normalized = normalize_text(value)
    return normalized or missing_default


def normalize_dependencies(value):
    normalized = normalize_text(value)
    if normalized.lower() in {"", "-", "—", "none", "n/a", "na"}:
        return "—"
    return normalized


def parse_dependency_ids(dep_value):
    """Return a set of task-ID strings parsed from a Dependencies cell value.

    Handles ``"—"``, ``"1"``, ``"1, 2"``, ``"1,2"`` and mixed whitespace.
    """
    if not dep_value or dep_value.strip() in {"", "-", "—"}:
        return set()
    return {part.strip() for part in re.split(r"[,\s]+", dep_value) if part.strip().isdigit()}


def detect_dependency_cycle(rows, target_id, new_dep_ids):
    """Return the offending cycle path if adding *new_dep_ids* to *target_id* creates a cycle.

    Uses depth-first search over the task-row dependency graph.
    Returns a list of task IDs forming the cycle, or an empty list if no cycle.
    """
    # Build a full adjacency map: task_id → set of dependency IDs
    dep_map = {}
    for row in rows:
        rid = row.get("#", "").strip()
        if rid:
            dep_map[rid] = parse_dependency_ids(row.get("Dependencies", ""))

    # Apply the proposed change
    dep_map[target_id] = new_dep_ids

    # DFS reachability: from each dep in new_dep_ids, can we reach target_id?
    def _dfs(current, visited, path):
        if current == target_id:
            return path + [current]
        if current in visited:
            return []
        visited.add(current)
        for next_id in dep_map.get(current, set()):
            result = _dfs(next_id, visited, path + [current])
            if result:
                return result
        return []

    for dep_id in new_dep_ids:
        cycle = _dfs(dep_id, set(), [target_id])
        if cycle:
            return cycle
    return []


def normalize_status(value):
    normalized = normalize_text(value)
    if not normalized:
        return "Pending"
    alias = STATUS_ALIASES.get(normalized.lower())
    if alias:
        return alias
    return " ".join(part.capitalize() for part in normalized.replace("-", " ").split())


def emit_task_response(command_name, project_root, updates, action_lines, task_table, archive_diagnostics, next_step):
    print("[Speaking Agent]: arms-main-agent")
    print("[Active Skill]:   arms-orchestrator")
    print()
    print("[State Updates]: {}".format(updates))
    print()
    print("[Action / Code]:")
    print("## Task {}".format(command_name.title()))
    print()
    print("**Project Root:** `{}`".format(project_root))
    print()
    for line in action_lines:
        print(line)
    if task_table:
        print()
        print(task_table)
    if archive_diagnostics:
        print()
        print(archive_diagnostics)
    print()
    print("[Next Step / Blocker]: {}".format(next_step))


class TaskCommandError(ValueError):
    pass
