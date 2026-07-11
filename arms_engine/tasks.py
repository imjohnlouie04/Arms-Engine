import json
import os
import re
import time
from contextlib import contextmanager

import yaml

from .memory import auto_stage_memory_draft_from_task
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

_ROUTING_TOKEN_RE = re.compile(r"[a-z0-9.]+")
_ROUTING_TOKEN_STOPWORDS = {
    "a", "an", "and", "add", "all", "for", "fix", "from", "improve", "in",
    "make", "new", "of", "on", "our", "set", "setup", "the", "to", "up",
    "update", "with", "when", "where", "that", "this",
}


def _stem_routing_token(token):
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _routing_tokens(text):
    tokens = set()
    for raw_token in _ROUTING_TOKEN_RE.findall(text.lower()):
        token = _stem_routing_token(raw_token)
        if token and token not in _ROUTING_TOKEN_STOPWORDS:
            tokens.add(token)
    return tokens


def _build_routing_vocab():
    """Build per-agent stemmed token sets from the routing keyword lists."""
    vocab = []
    for agent_name, patterns in ROUTING_RULES:
        tokens = set()
        for pattern in patterns:
            tokens.update(_routing_tokens(pattern))
        vocab.append((agent_name, tokens))
    return tuple(vocab)


ROUTING_TOKEN_VOCAB = _build_routing_vocab()


def identify_task_command(command_parts: tuple) -> str:
    """Return the normalised task sub-command name or empty string if unrecognised."""
    normalized = tuple(part.strip().lower() for part in command_parts if part.strip())
    return TASK_COMMANDS.get(normalized, "")


def build_task_log_signature(
    task: str = "",
    assigned_agent: str = "",
    active_skill: str = "",
    dependencies: str = "",
    status: str = "",
) -> dict:
    """Build a stable signature for debouncing exact duplicate `task log` calls."""
    return {
        "task": normalize_text(task).casefold(),
        "assigned_agent": normalize_text(assigned_agent).casefold(),
        "active_skill": normalize_text(active_skill).casefold(),
        "dependencies": normalize_text(dependencies).casefold(),
        "status": normalize_text(status).casefold(),
    }


def check_task_log_debounce(project_root: str, signature: dict, debounce_seconds: int = 2) -> bool:
    """Return True only for an *exact* duplicate `task log` call inside the debounce window."""
    wp = WorkspacePaths(project_root)
    lock_path = wp.task_log_lock

    if not os.path.exists(lock_path):
        return False

    try:
        with open(lock_path, "r") as f:
            lock_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return False

    last_signature = lock_data.get("signature", {})
    last_timestamp = lock_data.get("timestamp", 0)
    elapsed = time.time() - last_timestamp

    if elapsed > debounce_seconds:
        return False

    return last_signature == signature


def update_task_log_debounce(project_root: str, signature: dict) -> None:
    """Record a `task log` signature and timestamp for future debounce checks."""
    wp = WorkspacePaths(project_root)
    lock_path = wp.task_log_lock

    os.makedirs(wp.arms_dir, exist_ok=True)
    lock_data = {
        "signature": signature,
        "timestamp": time.time(),
    }
    try:
        temp_lock_path = "{}.tmp".format(lock_path)
        with open(temp_lock_path, "w") as f:
            json.dump(lock_data, f)
        os.replace(temp_lock_path, lock_path)
    except IOError:
        pass


@contextmanager
def task_log_guard(project_root: str, wait_seconds: float = 2.0, stale_seconds: float = 10.0):
    """Guard `task log` critical section across concurrent processes."""
    wp = WorkspacePaths(project_root)
    guard_path = "{}.guard".format(wp.task_log_lock)
    os.makedirs(wp.arms_dir, exist_ok=True)

    deadline = time.time() + wait_seconds
    acquired = False
    while time.time() < deadline:
        try:
            fd = os.open(guard_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode("utf-8"))
            finally:
                os.close(fd)
            acquired = True
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(guard_path) > stale_seconds:
                    os.remove(guard_path)
                    continue
            except OSError:
                pass
            time.sleep(0.05)

    if not acquired:
        raise TaskCommandError("`arms task log` is busy. Please retry in a moment.")

    try:
        yield
    finally:
        try:
            os.remove(guard_path)
        except OSError:
            pass


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
            signature = build_task_log_signature(
                task=task,
                assigned_agent=assigned_agent,
                active_skill=active_skill,
                dependencies=dependencies,
                status=status,
            )
            with task_log_guard(project_root):
                # Refresh rows inside the guard so debounce and row updates observe
                # the latest on-disk state across concurrent IDE/Copilot calls.
                _, latest_sections = load_session_sections(project_root)
                latest_rows = parse_task_rows(latest_sections.get("Active Tasks", ""))

                if check_task_log_debounce(project_root, signature):
                    emit_task_response(
                        command_name,
                        project_root,
                        updates="None",
                        action_lines=[
                            "Skipped duplicate `arms task log` call received within debounce window.",
                            "Exact same task payload was already applied.",
                        ],
                        task_table=render_task_table(latest_rows, arms_root),
                        archive_diagnostics="",
                        next_step="No duplicate row was added. Continue work. → HALT",
                    )
                    return

                result = log_task_row(
                    latest_rows,
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
                update_task_log_debounce(project_root, signature)
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

    memory_candidate = result.get("memory_candidate")
    if memory_candidate:
        try:
            memory_result = auto_stage_memory_draft_from_task(
                project_root,
                task_text=memory_candidate.get("task", ""),
                status=memory_candidate.get("status", ""),
                blockers_text=sections.get("Blockers", "None"),
                dependencies=memory_candidate.get("dependencies", ""),
            )
            if memory_result:
                if memory_result.get("duplicate"):
                    result["action_lines"].append(
                        "Auto-memory draft already pending in `{}` (draft `{}`).".format(
                            memory_result["section"],
                            memory_result["draft_id"],
                        )
                    )
                else:
                    result["action_lines"].append(
                        "Auto-memory draft staged in `{}` (draft `{}`). Approve with `arms memory append --draft-id {}`.".format(
                            memory_result["section"],
                            memory_result["draft_id"],
                            memory_result["draft_id"],
                        )
                    )
        except Exception:  # noqa: BLE001 - auto-memory must not block task updates
            result["action_lines"].append("Auto-memory staging skipped due to an internal error.")

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
        delegation_hint = render_delegation_hint(finalized_row["Assigned Agent"], finalized_row.get("Model", ""))
        action_lines = [
            "Updated existing task row `#{}` instead of duplicating it.".format(finalized_row["#"]),
            "- Task: `{}`".format(finalized_row["Task"]),
            "- Assigned Agent: `{}`".format(finalized_row["Assigned Agent"]),
            "- Active Skill: `{}`".format(finalized_row["Active Skill"]),
            "- Status: `{}`".format(finalized_row["Status"]),
        ]
        if delegation_hint:
            action_lines.append("- Handoff: {}".format(delegation_hint))
        return {
            "rows": finalized_rows,
            "archive_context": "Task command: update existing row",
            "action_lines": action_lines,
            "next_step": "Task ledger updated. {}Continue work with `arms task update --task-id {}` as progress changes. → HALT".format(
                delegation_hint + " " if delegation_hint else "",
                finalized_row["#"],
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
    delegation_hint = render_delegation_hint(finalized_row["Assigned Agent"], finalized_row.get("Model", ""))
    action_lines = [
        "Logged a new task row in `.arms/SESSION.md`.",
        "- Task ID: `{}`".format(finalized_row["#"]),
        "- Task: `{}`".format(finalized_row["Task"]),
        "- Assigned Agent: `{}`".format(finalized_row["Assigned Agent"]),
        "- Active Skill: `{}`".format(finalized_row["Active Skill"]),
        "- Status: `{}`".format(finalized_row["Status"]),
    ]
    if delegation_hint:
        action_lines.append("- Handoff: {}".format(delegation_hint))
    return {
        "rows": finalized_rows,
        "archive_context": "Task command: log row",
        "action_lines": action_lines,
        "next_step": "Task logged. {}Advance it with `arms task update --task-id {}` or archive it with `arms task done --task-id {}` when complete. → HALT".format(
            delegation_hint + " " if delegation_hint else "",
            finalized_row["#"],
            finalized_row["#"],
        ),
        "memory_candidate": memory_candidate_from_row(finalized_row),
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
    delegation_hint = "" if archived else render_delegation_hint(
        finalized_row["Assigned Agent"], finalized_row.get("Model", "")
    )
    next_step = (
        "Task archived. Continue with the next active row or log a new task when more work appears. → HALT"
        if archived
        else "Task row updated. {}Continue advancing it with `arms task update --task-id {}` or archive it with `arms task done --task-id {}`. → HALT".format(
            delegation_hint + " " if delegation_hint else "",
            finalized_row["#"],
            finalized_row["#"],
        )
    )
    action_lines = [
        "Updated task row `#{}`.".format(finalized_row["#"]),
        "- Task: `{}`".format(finalized_row["Task"]),
        "- Assigned Agent: `{}`".format(finalized_row["Assigned Agent"]),
        "- Active Skill: `{}`".format(finalized_row["Active Skill"]),
        "- Dependencies: `{}`".format(finalized_row["Dependencies"]),
        "- Status: `{}`".format(finalized_row["Status"]),
    ]
    if delegation_hint:
        action_lines.append("- Handoff: {}".format(delegation_hint))
    return {
        "rows": finalized_rows,
        "archive_context": "Task command: update row",
        "action_lines": action_lines,
        "next_step": next_step,
        "memory_candidate": memory_candidate_from_row(finalized_row),
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
        "memory_candidate": memory_candidate_from_row(finalized_row),
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


def render_delegation_hint(agent_name, model_tier=""):
    """Render the explicit multi-agent handoff instruction for a task row.

    Updating `.arms/SESSION.md` does not itself switch the host AI tool into
    the specialist, so every log/update response spells out how each platform
    should hand the implementation turn to the assigned agent.
    """
    normalized_agent = (agent_name or "").strip()
    if not normalized_agent or normalized_agent == "arms-main-agent":
        return ""
    tier = (model_tier or "").strip()
    tier_note = " (model tier: `{}`)".format(tier) if tier and tier not in {"—", "-"} else ""
    return (
        "Delegate to `{agent}`{tier} — Claude Code: run the `{agent}` subagent via the Task tool; "
        "Copilot CLI: `/agent {agent}`; other CLIs: switch the session to the `{agent}` agent mirror."
    ).format(agent=normalized_agent, tier=tier_note)


def infer_agent_from_task(task_text):
    normalized = task_text.lower()

    # Pass 1: exact whole-phrase keyword rules (high precision, priority order).
    for agent_name, patterns in ROUTING_RULE_PATTERNS:
        if any(pattern.search(normalized) for pattern in patterns):
            return agent_name

    # Pass 2: scored token-overlap fallback so realistic phrasings land on the
    # right specialist instead of dumping everything on arms-main-agent.
    # A single shared token (e.g. "data", "user") is too weak a signal, so at
    # least two overlapping tokens are required; genuinely ambiguous tasks stay
    # with arms-main-agent for the orchestrator to triage.
    task_tokens = _routing_tokens(normalized)
    if task_tokens:
        best_agent = ""
        best_score = 0
        for agent_name, vocab_tokens in ROUTING_TOKEN_VOCAB:
            if agent_name == "arms-main-agent":
                continue  # main-agent is the fallback, not a scoring candidate
            score = len(task_tokens & vocab_tokens)
            if score > best_score:
                best_agent = agent_name
                best_score = score
        if best_agent and best_score >= 2:
            return best_agent

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


def memory_candidate_from_row(row):
    status = (row.get("Status", "") or "").strip()
    if status.lower() not in {"done", "blocked", "failed"}:
        return None
    return {
        "task": row.get("Task", ""),
        "status": status,
        "dependencies": row.get("Dependencies", ""),
    }


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
