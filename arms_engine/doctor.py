import os
import re
from collections import OrderedDict

from . import __version__
from .protocols import collect_recent_commit_subjects, find_latest_report, parse_actionable_issues
from .session import compare_versions, extract_session_engine_version, parse_markdown_sections, read_text_file
from .skills import discover_skill_catalog


REQUIRED_SESSION_SECTIONS = (
    "Environment",
    "Active Agents",
    "Active Skills",
    "Active Tasks",
    "Completed Tasks",
    "Blockers",
)
REQUIRED_ENVIRONMENT_KEYS = (
    "ARMS Root",
    "Engine Version",
    "Project Root",
    "Project Name",
    "Execution Mode",
    "YOLO Mode",
)
REQUIRED_WORKSPACE_DIRECTORIES = (
    ".arms",
    ".arms/agent-outputs",
    ".arms/reports",
    ".arms/workflow",
    ".agents/skills",
    ".gemini/agents",
    ".gemini/skills",
    ".github/agents",
    ".github/skills",
)
REQUIRED_WORKSPACE_FILES = (
    ".arms/SESSION.md",
    ".arms/SESSION_ARCHIVE.md",
    ".arms/BRAND.md",
    ".arms/MEMORY.md",
    ".arms/RULES.md",
    ".arms/ENGINE.md",
    ".agents/skills.yaml",
    ".agents/skills-index.md",
    ".gemini/skills.yaml",
    ".gemini/skills-index.md",
    ".github/skills.yaml",
    ".github/skills-index.md",
    ".gemini/agents.yaml",
    "AGENTS.md",
)
PROJECT_INSTRUCTION_FILES = (
    "GEMINI.md",
    os.path.join(".gemini", "GEMINI.md"),
    os.path.join(".github", "copilot-instructions.md"),
)
ACTIVE_TASKS_HEADER = "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |"


def identify_doctor_command(command_parts):
    normalized = tuple(part.strip().lower() for part in command_parts if part.strip())
    return normalized == ("doctor",)


def handle_doctor_command(project_root, arms_root):
    report = build_doctor_report(project_root, arms_root)
    emit_doctor_response(report)
    if report["counts"]["fail"] > 0:
        raise SystemExit(1)


def build_doctor_report(project_root, arms_root):
    categories = OrderedDict(
        (
            ("Workspace Health", []),
            ("Ownership Safety", []),
            ("Protocol Readiness", []),
        )
    )
    counts = {"ok": 0, "warn": 0, "fail": 0}

    session_content = ""
    session_sections = {}
    blockers_text = "Unknown"

    missing_dirs = [
        relative_path
        for relative_path in REQUIRED_WORKSPACE_DIRECTORIES
        if not os.path.isdir(os.path.join(project_root, relative_path))
    ]
    if missing_dirs:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "fail",
            "Missing required workspace directories: {}.".format(", ".join(f"`{path}`" for path in missing_dirs)),
            "Run `arms init` to scaffold the managed workspace directories.",
        )
    else:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "ok",
            "Required workspace directories are present.",
        )

    missing_files = [
        relative_path
        for relative_path in REQUIRED_WORKSPACE_FILES
        if not os.path.isfile(os.path.join(project_root, relative_path))
    ]
    if missing_files:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "fail",
            "Missing required workspace files: {}.".format(", ".join(f"`{path}`" for path in missing_files)),
            "Run `arms init` to regenerate the managed workspace files.",
        )
    else:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "ok",
            "Required workspace files are present.",
        )

    session_path = os.path.join(project_root, ".arms", "SESSION.md")
    if os.path.isfile(session_path):
        session_content = read_text_file(session_path)
        _, parsed_sections = parse_markdown_sections(session_content)
        session_sections = OrderedDict(parsed_sections)

        missing_sections = [name for name in REQUIRED_SESSION_SECTIONS if name not in session_sections]
        missing_env_keys = [
            key for key in REQUIRED_ENVIRONMENT_KEYS
            if not has_environment_key(session_sections.get("Environment", ""), key)
        ]
        active_tasks_content = (session_sections.get("Active Tasks", "") or "").strip()
        if missing_sections:
            add_check(
                categories,
                counts,
                "Workspace Health",
                "fail",
                "`.arms/SESSION.md` is missing sections: {}.".format(", ".join(f"`{name}`" for name in missing_sections)),
                "Rerun `arms init` to repair the session structure.",
            )
        elif missing_env_keys:
            add_check(
                categories,
                counts,
                "Workspace Health",
                "fail",
                "`.arms/SESSION.md` is missing environment keys: {}.".format(", ".join(f"`{key}`" for key in missing_env_keys)),
                "Rerun `arms init` to restore the full environment block.",
            )
        elif not active_tasks_content.startswith(ACTIVE_TASKS_HEADER):
            add_check(
                categories,
                counts,
                "Workspace Health",
                "fail",
                "`.arms/SESSION.md` has a malformed `## Active Tasks` table.",
                "Normalize the session with `arms init` so the active task table uses the current schema.",
            )
        else:
            add_check(
                categories,
                counts,
                "Workspace Health",
                "ok",
                "`.arms/SESSION.md` contains the required sections and task-table schema.",
            )

        blockers_text = (session_sections.get("Blockers", "None") or "None").strip() or "None"
        recorded_engine_version = extract_session_engine_version(session_content)
        if not recorded_engine_version:
            add_check(
                categories,
                counts,
                "Workspace Health",
                "fail",
                "`.arms/SESSION.md` does not record an engine version.",
                "Rerun `arms init` so the workspace records the engine version it was synced with.",
            )
        else:
            version_comparison = compare_versions(recorded_engine_version, __version__)
            if version_comparison > 0:
                add_check(
                    categories,
                    counts,
                    "Workspace Health",
                    "fail",
                    "Workspace was last synced with newer engine version `{}` than the current engine `{}`.".format(
                        recorded_engine_version,
                        __version__,
                    ),
                    "Upgrade the engine or rerun with `arms init --allow-engine-downgrade` only if the downgrade is intentional.",
                )
            elif version_comparison < 0:
                add_check(
                    categories,
                    counts,
                    "Workspace Health",
                    "warn",
                    "Workspace was last synced with older engine version `{}` than the current engine `{}`.".format(
                        recorded_engine_version,
                        __version__,
                    ),
                    "Rerun `arms init` to refresh mirrored files and session metadata with the current engine.",
                )
            else:
                add_check(
                    categories,
                    counts,
                    "Workspace Health",
                    "ok",
                    "Workspace engine version matches the current engine (`{}`).".format(__version__),
                )
    else:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "fail",
            "`.arms/SESSION.md` is missing.",
            "Run `arms init` before using workspace protocols.",
        )

    validate_agent_mirrors(project_root, arms_root, categories, counts)
    validate_skill_mirror(project_root, arms_root, categories, counts)
    validate_workflow_mirror(project_root, arms_root, categories, counts)

    validate_synced_file(
        project_root,
        os.path.join(arms_root, "ENGINE.md"),
        os.path.join(project_root, ".arms", "ENGINE.md"),
        "Ownership Safety",
        "Engine instructions",
        categories,
        counts,
        "Rerun `arms init` to resync `.arms/ENGINE.md` from the engine source.",
    )
    validate_synced_file(
        project_root,
        os.path.join(arms_root, "AGENTS.md"),
        os.path.join(project_root, "AGENTS.md"),
        "Ownership Safety",
        "Root AGENTS guide",
        categories,
        counts,
        "Rerun `arms init` to resync the engine-managed `AGENTS.md` guide.",
    )

    detected_instruction_files = [
        relative_path
        for relative_path in PROJECT_INSTRUCTION_FILES
        if os.path.isfile(os.path.join(project_root, relative_path))
    ]
    if detected_instruction_files:
        add_check(
            categories,
            counts,
            "Ownership Safety",
            "ok",
            "Detected project-owned instruction files: {}.".format(", ".join(f"`{path}`" for path in detected_instruction_files)),
        )
    else:
        add_check(
            categories,
            counts,
            "Ownership Safety",
            "ok",
            "No project-owned instruction files were detected in the standard locations.",
        )

    review_prereqs = []
    for relative_path in (
        ".arms/SESSION.md",
        ".arms/reports",
        os.path.join(".arms", "workflow", "REVIEW_PROTOCOL.md"),
    ):
        absolute_path = os.path.join(project_root, relative_path)
        if relative_path.endswith(".md"):
            if not os.path.isfile(absolute_path):
                review_prereqs.append(relative_path)
        elif not os.path.isdir(absolute_path):
            review_prereqs.append(relative_path)
    if review_prereqs:
        add_check(
            categories,
            counts,
            "Protocol Readiness",
            "fail",
            "`arms run review` is missing prerequisites: {}.".format(", ".join(f"`{path}`" for path in review_prereqs)),
            "Run `arms init` to restore review workflow prerequisites.",
        )
    else:
        add_check(
            categories,
            counts,
            "Protocol Readiness",
            "ok",
            "`arms run review` has its required workspace files.",
        )

    review_report_path = find_latest_report(project_root, "review")
    if not review_report_path:
        add_check(
            categories,
            counts,
            "Protocol Readiness",
            "warn",
            "`arms fix issues` is waiting on a review report.",
            "Run `arms run review` first so ARMS can scaffold the latest review report.",
        )
    else:
        actionable_issues = parse_actionable_issues(read_text_file(review_report_path))
        if actionable_issues:
            add_check(
                categories,
                counts,
                "Protocol Readiness",
                "ok",
                "`arms fix issues` is ready; latest review report contains {} actionable issue(s).".format(len(actionable_issues)),
            )
        else:
            add_check(
                categories,
                counts,
                "Protocol Readiness",
                "warn",
                "`arms fix issues` found no actionable issues in `{}`.".format(os.path.relpath(review_report_path, project_root)),
                "Add bullet items under `## Actionable Issues` in the latest review report before rerunning `arms fix issues`.",
            )

    deploy_prereqs = []
    deploy_workflow_path = os.path.join(project_root, ".arms", "workflow", "DEPLOY_PROTOCOL.md")
    if not os.path.isfile(deploy_workflow_path):
        deploy_prereqs.append(".arms/workflow/DEPLOY_PROTOCOL.md")
    if not os.path.isdir(os.path.join(project_root, ".arms", "reports")):
        deploy_prereqs.append(".arms/reports")
    if deploy_prereqs:
        add_check(
            categories,
            counts,
            "Protocol Readiness",
            "fail",
            "`arms run deploy` is missing prerequisites: {}.".format(", ".join(f"`{path}`" for path in deploy_prereqs)),
            "Run `arms init` to restore deploy workflow prerequisites.",
        )
    else:
        deploy_messages = []
        if blockers_text not in {"", "None"}:
            deploy_messages.append("open blockers are recorded in `.arms/SESSION.md`")
        if not collect_recent_commit_subjects(project_root):
            deploy_messages.append("release notes will be generic because no recent git history was found")
        if deploy_messages:
            add_check(
                categories,
                counts,
                "Protocol Readiness",
                "warn",
                "`arms run deploy` has warnings: {}.".format("; ".join(deploy_messages)),
                "Clear blockers and confirm release-note inputs before deploying.",
            )
        else:
            add_check(
                categories,
                counts,
                "Protocol Readiness",
                "ok",
                "`arms run deploy` has the expected workflow files and release-note inputs.",
            )

    return {
        "project_root": project_root,
        "arms_root": arms_root,
        "categories": categories,
        "counts": counts,
    }


def validate_agent_mirrors(project_root, arms_root, categories, counts):
    source_agents_dir = os.path.join(arms_root, "agents")
    source_agent_files = sorted(
        name for name in os.listdir(source_agents_dir)
        if name.endswith(".md")
    ) if os.path.isdir(source_agents_dir) else []
    if not source_agent_files:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "fail",
            "Engine agent source files are missing under `agents/`.",
            "Restore the engine agent definitions before running workspace sync commands.",
        )
        return

    mismatches = []
    for relative_dir in (".gemini/agents", ".github/agents"):
        mirror_dir = os.path.join(project_root, relative_dir)
        mirrored_files = sorted(
            name for name in os.listdir(mirror_dir)
            if name.endswith(".md")
        ) if os.path.isdir(mirror_dir) else []
        missing = sorted(set(source_agent_files) - set(mirrored_files))
        extra = sorted(set(mirrored_files) - set(source_agent_files))
        if missing or extra:
            description = [f"`{relative_dir}`"]
            if missing:
                description.append("missing {}".format(", ".join(f"`{name}`" for name in missing)))
            if extra:
                description.append("has extra {}".format(", ".join(f"`{name}`" for name in extra)))
            mismatches.append("; ".join(description))

    if mismatches:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "fail",
            "Agent mirrors are out of sync: {}.".format(" | ".join(mismatches)),
            "Rerun `arms init` to resync `.gemini/agents/` and `.github/agents/` from the engine.",
        )
    else:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "ok",
            "Agent mirrors match the engine agent roster.",
        )


def validate_skill_mirror(project_root, arms_root, categories, counts):
    source_skills = {skill["source_directory"] for skill in discover_skill_catalog(arms_root)}
    mirror_roots = (
        ".agents/skills",
        ".gemini/skills",
        ".github/skills",
    )
    problems = []

    for relative_root in mirror_roots:
        mirror_root = os.path.join(project_root, relative_root)
        mirrored_skills = {
            name for name in os.listdir(mirror_root)
            if os.path.isdir(os.path.join(mirror_root, name))
        } if os.path.isdir(mirror_root) else set()
        missing = sorted(source_skills - mirrored_skills)
        extra = sorted(mirrored_skills - source_skills)
        invalid = sorted(
            name for name in mirrored_skills
            if not os.path.isfile(os.path.join(mirror_root, name, "SKILL.md"))
        )

        current_problems = []
        if missing:
            current_problems.append("missing {}".format(", ".join(f"`{name}`" for name in missing)))
        if extra:
            current_problems.append("extra {}".format(", ".join(f"`{name}`" for name in extra)))
        if invalid:
            current_problems.append("missing `SKILL.md` in {}".format(", ".join(f"`{name}`" for name in invalid)))
        if current_problems:
            problems.append(f"`{relative_root}`: " + "; ".join(current_problems))

    if problems:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "fail",
            "Skill mirrors are out of sync: {}.".format(" | ".join(problems)),
            "Rerun `arms init` to rebuild `.agents/skills/`, `.gemini/skills/`, `.github/skills/`, and the generated skill registries.",
        )
    else:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "ok",
            "Skill mirrors match the engine skill catalog.",
        )


def validate_workflow_mirror(project_root, arms_root, categories, counts):
    source_workflow_dir = os.path.join(arms_root, "workflow")
    source_files = {
        name for name in os.listdir(source_workflow_dir)
        if os.path.isfile(os.path.join(source_workflow_dir, name))
    } if os.path.isdir(source_workflow_dir) else set()
    mirror_dir = os.path.join(project_root, ".arms", "workflow")
    mirrored_files = {
        name for name in os.listdir(mirror_dir)
        if os.path.isfile(os.path.join(mirror_dir, name))
    } if os.path.isdir(mirror_dir) else set()
    missing = sorted(source_files - mirrored_files)
    if missing:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "fail",
            "Workflow mirror is missing files: {}.".format(", ".join(f"`{name}`" for name in missing)),
            "Rerun `arms init` to resync `.arms/workflow/`.",
        )
    else:
        add_check(
            categories,
            counts,
            "Workspace Health",
            "ok",
            "Workflow mirror matches the engine workflow directory.",
        )


def validate_synced_file(project_root, source_path, target_path, category, label, categories, counts, fix):
    relative_target = os.path.relpath(target_path, project_root)
    if not os.path.isfile(source_path):
        add_check(
            categories,
            counts,
            category,
            "fail",
            "{} source file is missing from the engine.".format(label),
            "Restore the engine file before resyncing workspaces.",
        )
        return
    if not os.path.isfile(target_path):
        add_check(
            categories,
            counts,
            category,
            "fail",
            "{} file `{}` is missing from the workspace.".format(label, relative_target),
            fix,
        )
        return
    if read_text_file(source_path) != read_text_file(target_path):
        add_check(
            categories,
            counts,
            category,
            "fail",
            "{} file `{}` is out of sync with the engine source.".format(label, relative_target),
            fix,
        )
        return
    add_check(
        categories,
        counts,
        category,
        "ok",
        "{} file `{}` matches the engine source.".format(label, relative_target),
    )


def has_environment_key(environment_content, key):
    pattern = r"^- {}: .+$".format(re.escape(key))
    return bool(re.search(pattern, environment_content or "", re.MULTILINE))


def add_check(categories, counts, category, status, summary, fix=""):
    categories[category].append(
        {
            "status": status,
            "summary": summary,
            "fix": fix.strip(),
        }
    )
    counts[status] += 1


def emit_doctor_response(report):
    counts = report["counts"]
    result = "FAIL" if counts["fail"] else "PASS"
    body_lines = [
        "## Doctor Summary",
        "",
        "**Project Root:** `{}`".format(report["project_root"]),
        "**Engine Root:** `{}`".format(report["arms_root"]),
        "**Result:** {}".format(result),
        "**Checks:** {} ok / {} warn / {} fail".format(counts["ok"], counts["warn"], counts["fail"]),
        "",
    ]

    for category, checks in report["categories"].items():
        body_lines.append("### {}".format(category))
        for check in checks:
            body_lines.append("- [{}] {}".format(check["status"].upper(), check["summary"]))
            if check["fix"]:
                body_lines.append("  Fix: {}".format(check["fix"]))
        body_lines.append("")

    if counts["fail"]:
        next_step = "Doctor found {} blocking issue(s). Fix the failing items and rerun `arms doctor`. → HALT".format(
            counts["fail"]
        )
    else:
        next_step = "Workspace health check complete. Address any warnings as needed before continuing. → HALT"

    print("[Speaking Agent]: arms-main-agent")
    print("[Active Skill]:   arms-orchestrator")
    print()
    print("[State Updates]: None")
    print()
    print("[Action / Code]:")
    print("\n".join(body_lines).rstrip())
    print()
    print("[Next Step / Blocker]: {}".format(next_step))
