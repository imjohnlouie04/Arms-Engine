import os

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
ROUTING_RULES = (
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


def identify_task_command(command_parts):
    normalized = tuple(part.strip().lower() for part in command_parts if part.strip())
    return TASK_COMMANDS.get(normalized, "")


def handle_task_command(
    project_root,
    arms_root,
    command_name,
    task="",
    task_id="",
    assigned_agent="",
    active_skill="",
    dependencies="",
    status="",
):
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

    try:
        if command_name == "log":
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
    rows.append(
        {
            "#": str(len(rows) + 1),
            "Task": normalized_task,
            "Assigned Agent": resolved_agent,
            "Active Skill": normalize_skill_value(active_skill, missing_default="—"),
            "Dependencies": normalize_dependencies(dependencies),
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
    for agent_name, patterns in ROUTING_RULES:
        if any(pattern in normalized for pattern in patterns):
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
