import datetime
import os
import re
import subprocess
from collections import OrderedDict

from .session import (
    normalize_active_tasks_table,
    parse_markdown_sections,
    read_text_file,
    write_markdown_sections,
    write_text_atomic,
)
from .skills import build_agent_skill_bindings, resolve_agents_with_skills


TASK_TABLE_HEADER = "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |"
TASK_TABLE_DIVIDER = "|---|------|----------------|--------------|--------------|--------|"
KEEP_EXISTING = object()
PROTOCOL_BLOCKER_PREFIXES = (
    "No review report found",
    "No actionable issues found",
)


def identify_protocol_command(command_parts):
    normalized = tuple(part.strip().lower() for part in command_parts if part.strip())
    return {
        ("run", "review"): "review",
        ("fix", "issues"): "fix_issues",
        ("run", "deploy"): "deploy",
        ("run", "pipeline"): "pipeline",
        ("run", "status"): "status",
    }.get(normalized)


def handle_protocol_command(command_name, project_root, arms_root):
    try:
        if command_name == "review":
            run_review_protocol(project_root, arms_root)
            return
        if command_name == "fix_issues":
            run_fix_issues_protocol(project_root, arms_root)
            return
        if command_name == "deploy":
            run_deploy_protocol(project_root, arms_root)
            return
        if command_name == "pipeline":
            run_pipeline_protocol(project_root, arms_root)
            return
        if command_name == "status":
            run_status_protocol(project_root)
            return
    except FileNotFoundError:
        emit_protocol_response(
            "None",
            "⚠️ ARMS workspace not initialized. Run `arms init` in this project before using protocol commands.",
            "Initialize the workspace first with `arms init`, then rerun the protocol command. → HALT",
        )
        raise SystemExit(1)


def run_review_protocol(project_root, arms_root):
    _, sections = load_session_sections(project_root)
    existing_rows = parse_task_rows(sections.get("Active Tasks", ""))
    review_rows = build_review_rows()
    combined_rows = replace_phase_rows(existing_rows, ("Review:",), review_rows)
    update_protocol_session(
        project_root,
        arms_root,
        combined_rows,
        blockers=clear_protocol_blockers(sections.get("Blockers", "None")),
    )

    report_path = dated_report_path(project_root, "review")
    write_text_atomic(report_path, render_review_report(project_root, "run review"))
    emit_protocol_response(
        "SESSION.md updated; {} written".format(relative_to_project(project_root, report_path)),
        "\n".join(
            [
                "## Review Protocol",
                "",
                "**Workflow:** `.arms/workflow/REVIEW_PROTOCOL.md`",
                "**Review Report:** `{}`".format(relative_to_project(project_root, report_path)),
                "",
                render_task_table(combined_rows, arms_root),
            ]
        ),
        "Review protocol staged and logged. Populate findings in the review report, then decide whether to continue with `fix issues`. → HALT",
    )


def run_pipeline_protocol(project_root, arms_root):
    _, sections = load_session_sections(project_root)
    existing_rows = parse_task_rows(sections.get("Active Tasks", ""))
    review_rows = build_review_rows()
    combined_rows = replace_phase_rows(existing_rows, ("Review:", "Fix:", "Deploy:"), review_rows)
    update_protocol_session(
        project_root,
        arms_root,
        combined_rows,
        blockers=clear_protocol_blockers(sections.get("Blockers", "None")),
    )

    report_path = dated_report_path(project_root, "review")
    write_text_atomic(report_path, render_review_report(project_root, "run pipeline"))
    emit_protocol_response(
        "SESSION.md updated; {} written".format(relative_to_project(project_root, report_path)),
        "\n".join(
            [
                "## Pipeline Status",
                "",
                "**Current Phase:** Review",
                "**Review Report:** `{}`".format(relative_to_project(project_root, report_path)),
                "",
                render_task_table(combined_rows, arms_root),
            ]
        ),
        "Pipeline entered the Review phase. Confirm the review findings before continuing with `fix issues`, then `run deploy`. → HALT",
    )


def run_fix_issues_protocol(project_root, arms_root):
    _, sections = load_session_sections(project_root)
    review_path = find_latest_report(project_root, "review")
    if not review_path:
        blocker = "No review report found in `.arms/reports/`. Run `arms run review` first."
        update_protocol_session(
            project_root,
            arms_root,
            parse_task_rows(sections.get("Active Tasks", "")),
            blockers=blocker,
        )
        emit_protocol_response(
            "SESSION.md updated",
            blocker,
            "Review findings are required before fixes can be planned. → HALT",
        )
        return

    review_content = read_text_file(review_path)
    issues = parse_actionable_issues(review_content)
    if not issues:
        blocker = "No actionable issues found in `{}`. Add bullet items under `## Actionable Issues` and rerun `arms fix issues`.".format(
            relative_to_project(project_root, review_path)
        )
        update_protocol_session(
            project_root,
            arms_root,
            replace_phase_rows(parse_task_rows(sections.get("Active Tasks", "")), ("Fix:",), []),
            blockers=blocker,
        )
        emit_protocol_response(
            "SESSION.md updated",
            blocker,
            "Actionable review findings are required before fix planning can continue. → HALT",
        )
        return

    existing_rows = parse_task_rows(sections.get("Active Tasks", ""))
    fix_rows = build_fix_rows(issues)
    combined_rows = replace_phase_rows(existing_rows, ("Fix:",), fix_rows)
    blockers = clear_protocol_blockers(sections.get("Blockers", "None"))
    update_protocol_session(project_root, arms_root, combined_rows, blockers=blockers)

    plan_path = dated_report_path(project_root, "fix-plan")
    write_text_atomic(plan_path, render_fix_plan_report(project_root, review_path, fix_rows, arms_root))
    emit_protocol_response(
        "SESSION.md updated; {} written".format(relative_to_project(project_root, plan_path)),
        "\n".join(
            [
                "## Fix Protocol",
                "",
                "**Source Review:** `{}`".format(relative_to_project(project_root, review_path)),
                "**Fix Plan:** `{}`".format(relative_to_project(project_root, plan_path)),
                "",
                render_task_table(combined_rows, arms_root),
            ]
        ),
        "Task plan generated and logged. Shall I begin executing these fixes? → HALT",
    )


def run_deploy_protocol(project_root, arms_root):
    _, sections = load_session_sections(project_root)
    existing_rows = parse_task_rows(sections.get("Active Tasks", ""))
    deploy_rows = build_deploy_rows(project_root)
    combined_rows = replace_phase_rows(existing_rows, ("Deploy:",), deploy_rows)
    blockers = clear_protocol_blockers(sections.get("Blockers", "None"))
    update_protocol_session(project_root, arms_root, combined_rows, blockers=blockers)

    release_notes_path = dated_report_path(project_root, "release-notes")
    write_text_atomic(release_notes_path, render_release_notes(project_root))
    migration_summary = summarize_migrations(project_root)
    emit_protocol_response(
        "SESSION.md updated; {} written".format(relative_to_project(project_root, release_notes_path)),
        "\n".join(
            [
                "## Deploy Protocol",
                "",
                "**Workflow:** `.arms/workflow/DEPLOY_PROTOCOL.md`",
                "**Release Notes:** `{}`".format(relative_to_project(project_root, release_notes_path)),
                "**Migration Summary:** {}".format(migration_summary),
                "",
                render_task_table(combined_rows, arms_root),
            ]
        ),
        "Pre-flight tasks staged and release notes generated. Review the migration summary before any remote deployment. → HALT",
    )


def run_status_protocol(project_root):
    _, sections = load_session_sections(project_root)
    active_tasks_content = sections.get("Active Tasks", "{}\n{}".format(TASK_TABLE_HEADER, TASK_TABLE_DIVIDER)).strip()
    active_rows = parse_task_rows(active_tasks_content)
    blockers = (sections.get("Blockers", "None") or "None").strip() or "None"
    execution_mode = extract_environment_value(sections.get("Environment", ""), "Execution Mode") or "Unknown"
    current_phase = infer_current_phase(active_rows)
    last_completed = extract_last_completed(project_root, sections.get("Completed Tasks", "- None"))

    emit_protocol_response(
        "None",
        "\n".join(
            [
                "## Pipeline Status",
                "",
                "**Execution Mode:** {}".format(execution_mode),
                "**Current Phase:** {}".format(current_phase),
                "**Active Tasks:**",
                active_tasks_content,
                "",
                "**Blockers:**",
                blockers,
                "",
                "**Last Completed:**",
                last_completed,
            ]
        ),
        "Status report complete. Awaiting next command. → HALT",
    )


def build_review_rows():
    return [
        make_task_row(
            "Review: audit architecture, validation, and code quality",
            "arms-qa-agent",
            "qa-automation-testing",
        ),
        make_task_row(
            "Review: audit responsive UI, breakpoints, and UX rules",
            "arms-frontend-agent",
            "frontend-design",
        ),
        make_task_row(
            "Review: audit secrets, auth, dependencies, and OWASP risks",
            "arms-security-agent",
            "security-code-review",
        ),
    ]


def build_fix_rows(issues):
    rows = [
        make_task_row(
            "Fix: review findings and coordinate remediation plan",
            "arms-main-agent",
            "arms-orchestrator",
        )
    ]
    for issue in issues:
        assigned_agent, active_skill = choose_fix_assignment(issue)
        rows.append(
            make_task_row(
                "Fix: {}".format(issue),
                assigned_agent,
                active_skill,
            )
        )
    rows.append(
        make_task_row(
            "Fix: prepare a conventional commit after pre-flight passes",
            "arms-devops-agent",
            "devops-orchestrator",
        )
    )
    return rows


def build_deploy_rows(project_root):
    migration_summary = summarize_migrations(project_root)
    return [
        make_task_row(
            "Deploy: verify clean working tree and production build readiness",
            "arms-devops-agent",
            "devops-orchestrator",
        ),
        make_task_row(
            "Deploy: review pending database synchronization needs ({})".format(migration_summary),
            "arms-data-agent",
            "—",
        ),
        make_task_row(
            "Deploy: generate client-facing release notes from recent commits",
            "arms-main-agent",
            "arms-orchestrator",
        ),
        make_task_row(
            "Deploy: await final approval before remote production push",
            "arms-devops-agent",
            "devops-orchestrator",
        ),
    ]


def choose_fix_assignment(issue):
    issue_text = issue.lower()
    if any(token in issue_text for token in ("build", "deploy", "ci", "workflow", "docker", "vercel", "release")):
        return "arms-devops-agent", "devops-orchestrator"
    if any(
        token in issue_text
        for token in (
            "ui",
            "layout",
            "responsive",
            "sidebar",
            "mobile",
            "accessibility",
            "a11y",
            "seo",
            "meta",
            "schema",
            "component",
            "page",
            "frontend",
            "design",
        )
    ):
        return "arms-frontend-agent", "frontend-design"
    return "arms-backend-agent", "backend-system-architect"


def make_task_row(task, agent, active_skill, dependencies="—", status="Pending"):
    return {
        "Task": task,
        "Assigned Agent": agent,
        "Active Skill": active_skill,
        "Dependencies": dependencies,
        "Status": status,
    }


def replace_phase_rows(existing_rows, phase_prefixes, new_rows):
    filtered_rows = []
    for row in existing_rows:
        task_text = row.get("Task", "")
        if any(task_text.startswith(prefix) for prefix in phase_prefixes):
            continue
        filtered_rows.append(row)
    filtered_rows.extend(new_rows)
    return renumber_rows(filtered_rows)


def renumber_rows(rows):
    normalized = []
    for index, row in enumerate(rows, start=1):
        normalized.append(
            {
                "#": str(index),
                "Task": row.get("Task", "").strip(),
                "Assigned Agent": row.get("Assigned Agent", "").strip(),
                "Active Skill": row.get("Active Skill", "—").strip() or "—",
                "Dependencies": row.get("Dependencies", "—").strip() or "—",
                "Status": row.get("Status", "Pending").strip() or "Pending",
            }
        )
    return normalized


def render_task_table(rows, arms_root):
    lines = [TASK_TABLE_HEADER, TASK_TABLE_DIVIDER]
    for row in renumber_rows(rows):
        lines.append(
            "| {index} | {task} | {agent} | {skill} | {deps} | {status} |".format(
                index=row["#"],
                task=row["Task"],
                agent=row["Assigned Agent"],
                skill=row["Active Skill"],
                deps=row["Dependencies"],
                status=row["Status"],
            )
        )
    task_content = "\n".join(lines)
    agent_skill_bindings, skill_catalog_by_name = load_agent_skill_context(arms_root)
    return normalize_active_tasks_table(
        task_content,
        agent_skill_bindings=agent_skill_bindings,
        skill_catalog_by_name=skill_catalog_by_name,
    )


def parse_task_rows(content):
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
                "#": cells[0],
                "Task": cells[1],
                "Assigned Agent": cells[2],
                "Active Skill": cells[3],
                "Dependencies": cells[4],
                "Status": cells[5],
            }
        )
    return rows


def infer_current_phase(active_rows):
    for prefix, label in (("Deploy:", "Deploy"), ("Fix:", "Fix"), ("Review:", "Review")):
        if any(row.get("Task", "").startswith(prefix) for row in active_rows):
            return label
    return "Idle"


def extract_last_completed(project_root, completed_content):
    completed_lines = [line.strip() for line in completed_content.splitlines() if line.strip()]
    for line in reversed(completed_lines):
        if line == "- None":
            continue
        return line

    archive_path = os.path.join(project_root, ".arms", "SESSION_ARCHIVE.md")
    if not os.path.exists(archive_path):
        return "None"

    archive_lines = read_text_file(archive_path).splitlines()
    for raw_line in reversed(archive_lines):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 5 and cells[0] != "#" and set(cells[0].replace(" ", "")) != {"-"}:
                return raw_line.strip()
        if line.startswith("- "):
            return line
    return "None"


def extract_environment_value(environment_content, key):
    pattern = r"^- {}: (.*)$".format(re.escape(key))
    match = re.search(pattern, environment_content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def load_agent_skill_context(arms_root):
    resolved_agents, skill_catalog, _ = resolve_agents_with_skills(arms_root, announce=False)
    return build_agent_skill_bindings(resolved_agents), {skill["name"]: skill for skill in skill_catalog}


def update_protocol_session(project_root, arms_root, active_rows, blockers=KEEP_EXISTING):
    preamble, sections = load_session_sections(project_root)
    ordered_sections = OrderedDict(sections)
    ordered_sections["Active Tasks"] = render_task_table(active_rows, arms_root)
    if "Completed Tasks" not in ordered_sections:
        ordered_sections["Completed Tasks"] = "- None"
    if blockers is KEEP_EXISTING:
        if "Blockers" not in ordered_sections:
            ordered_sections["Blockers"] = "None"
    else:
        ordered_sections["Blockers"] = blockers
    session_path = os.path.join(project_root, ".arms", "SESSION.md")
    write_markdown_sections(session_path, preamble, ordered_sections)


def load_session_sections(project_root):
    session_path = os.path.join(project_root, ".arms", "SESSION.md")
    if not os.path.exists(session_path):
        raise FileNotFoundError(session_path)
    return parse_markdown_sections(read_text_file(session_path))


def dated_report_path(project_root, prefix):
    reports_dir = os.path.join(project_root, ".arms", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    return os.path.join(reports_dir, "{}-{}.md".format(prefix, stamp))


def find_latest_report(project_root, prefix):
    reports_dir = os.path.join(project_root, ".arms", "reports")
    if not os.path.isdir(reports_dir):
        return ""
    matches = []
    for name in os.listdir(reports_dir):
        if name.startswith(prefix + "-") and name.endswith(".md"):
            matches.append(os.path.join(reports_dir, name))
    if not matches:
        return ""
    matches.sort()
    return matches[-1]


def parse_actionable_issues(content):
    match = re.search(
        r"^## Actionable Issues\s*$\n?([\s\S]*?)(?=^## |\Z)",
        content,
        re.MULTILINE,
    )
    if not match:
        return []

    issues = []
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip()
        if not line.startswith(("- ", "* ")):
            continue
        issue = line[2:].strip()
        if not issue or issue.lower() in {"none", "none yet"}:
            continue
        issues.append(issue)
    return issues


def clear_protocol_blockers(blockers_text):
    normalized = (blockers_text or "None").strip() or "None"
    for prefix in PROTOCOL_BLOCKER_PREFIXES:
        if normalized.startswith(prefix):
            return "None"
    return normalized


def summarize_migrations(project_root):
    migrations_dir = os.path.join(project_root, "supabase", "migrations")
    if not os.path.isdir(migrations_dir):
        return "No local Supabase migrations directory detected"
    migration_files = sorted(
        name
        for name in os.listdir(migrations_dir)
        if name.endswith(".sql")
    )
    if not migration_files:
        return "No local migration files detected"
    if len(migration_files) <= 3:
        return "{} migration file(s): {}".format(len(migration_files), ", ".join(migration_files))
    return "{} migration file(s): {} ... {}".format(
        len(migration_files),
        ", ".join(migration_files[:2]),
        migration_files[-1],
    )


def render_review_report(project_root, command_name):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return """# ARMS Review Report

Generated: {now}

## Protocol
- Command: `arms {command_name}`
- Workflow: `.arms/workflow/REVIEW_PROTOCOL.md`
- Project Root: `{project_root}`

## Summary
- Review protocol staged in `.arms/SESSION.md`.
- Populate the findings sections below or replace this scaffold with generated review results.
- Keep `## Actionable Issues` as one bullet per fixable item before running `arms fix issues`.

## QA Findings
No findings recorded yet.

## Frontend Findings
No findings recorded yet.

## Security Findings
No findings recorded yet.

## Actionable Issues
<!-- Add one bullet per actionable issue before running `arms fix issues`. -->
""".format(
        now=now,
        command_name=command_name,
        project_root=project_root,
    )


def render_fix_plan_report(project_root, review_path, fix_rows, arms_root):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    issue_lines = []
    for index, row in enumerate(fix_rows[1:-1], start=1):
        issue_lines.append("{}. {}".format(index, row["Task"].replace("Fix: ", "", 1)))
    parsed_issues = "\n".join(issue_lines) if issue_lines else "1. No issues parsed."
    return """# ARMS Fix Plan

Generated: {now}

## Source Review
- Report: `{review_path}`
- Workflow: `.arms/workflow/FIX_ISSUE_PROTOCOL.md`
- Project Root: `{project_root}`

## Parsed Issues
{parsed_issues}

## Task Table
{task_table}
""".format(
        now=now,
        review_path=relative_to_project(project_root, review_path),
        project_root=project_root,
        parsed_issues=parsed_issues,
        task_table=render_task_table(fix_rows, arms_root),
    )


def render_release_notes(project_root):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit_subjects = collect_recent_commit_subjects(project_root)
    if commit_subjects:
        highlight_lines = ["- {}".format(humanize_commit_subject(subject)) for subject in commit_subjects[:10]]
        technical_lines = ["- {}".format(subject) for subject in commit_subjects[:10]]
    else:
        highlight_lines = ["- No recent git commit history was available for automatic release-note synthesis."]
        technical_lines = ["- No commit subjects found."]
    return """# ARMS Release Notes

Generated: {now}

## Highlights
{highlights}

## Technical Commits
{technical_commits}
""".format(
        now=now,
        highlights="\n".join(highlight_lines),
        technical_commits="\n".join(technical_lines),
    )


def collect_recent_commit_subjects(project_root):
    try:
        run_git(project_root, ["rev-parse", "--is-inside-work-tree"])
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    latest_tag = ""
    try:
        latest_tag = run_git(project_root, ["describe", "--tags", "--abbrev=0"]).stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        latest_tag = ""

    log_args = ["log", "-10", "--pretty=%s"]
    if latest_tag:
        log_args = ["log", "{}..HEAD".format(latest_tag), "--pretty=%s"]
    try:
        completed = run_git(project_root, log_args)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def run_git(project_root, args):
    return subprocess.run(
        ["git", "-C", project_root] + list(args),
        capture_output=True,
        text=True,
        check=True,
    )


def humanize_commit_subject(subject):
    normalized = subject.strip()
    conventional = re.match(r"^(feat|fix|docs|refactor|perf|chore|test)(?:\([^)]+\))?:\s*(.+)$", normalized, re.IGNORECASE)
    if conventional:
        change_type = conventional.group(1).lower()
        detail = conventional.group(2).strip().rstrip(".")
        detail = strip_leading_change_verb(detail)
        prefix = {
            "feat": "Added",
            "fix": "Fixed",
            "docs": "Documented",
            "refactor": "Refined",
            "perf": "Improved",
            "chore": "Updated",
            "test": "Expanded coverage for",
        }.get(change_type, "Updated")
        if change_type == "test":
            return "{} {}.".format(prefix, detail)
        return "{} {}.".format(prefix, detail)

    stripped = normalized.rstrip(".")
    if not stripped:
        return "Updated the project."
    return stripped[0].upper() + stripped[1:] + "."


def strip_leading_change_verb(detail):
    lowered = detail.lower()
    prefixes = (
        "add ",
        "adds ",
        "added ",
        "fix ",
        "fixes ",
        "fixed ",
        "update ",
        "updates ",
        "updated ",
        "improve ",
        "improves ",
        "improved ",
        "document ",
        "documents ",
        "documented ",
        "preserve ",
        "preserves ",
        "preserved ",
        "refactor ",
        "refactors ",
        "refactored ",
        "expand ",
        "expands ",
        "expanded ",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return detail[len(prefix):].strip()
    return detail


def relative_to_project(project_root, path):
    return os.path.relpath(path, project_root)


def emit_protocol_response(state_updates, action_body, next_step):
    print("[Speaking Agent]: arms-main-agent")
    print("[Active Skill]:   arms-orchestrator")
    print()
    print("[State Updates]: {}".format(state_updates or "None"))
    print()
    print("[Action / Code]:")
    print(action_body.rstrip())
    print()
    print("[Next Step / Blocker]: {}".format(next_step))
