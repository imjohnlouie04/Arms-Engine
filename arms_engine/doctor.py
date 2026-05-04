import io
import os
import re
from collections import OrderedDict
from contextlib import redirect_stdout

from . import __version__
from .paths import WorkspacePaths
from .prompts import CONTEXT_SYNTHESIS_TOKEN_BUDGET, GENERATED_PROMPTS_TOKEN_BUDGET
from .protocols import collect_recent_commit_subjects, find_latest_report, parse_actionable_issues
from .session import (
    SESSION_TOKEN_BUDGET,
    assess_token_budget,
    compare_versions,
    extract_session_engine_version,
    parse_markdown_sections,
    read_text_file,
)
from .skills import (
    build_agent_sync_content,
    create_skills_registry,
    discover_skill_catalog,
    load_agents_registry,
    remove_obsolete_gemini_skill_artifacts,
    sync_agents,
    sync_agents_copilot,
    sync_engine_instructions,
    sync_root_agents_guide,
    sync_skills_copilot,
    sync_workflow,
)
from .brand import (
    extract_brand_field,
    get_missing_new_project_brand_fields,
    is_new_project_brand_questionnaire,
    parse_pyproject_metadata,
)
from .update_docs import get_agent_docs
from .versioning import collect_version_diagnostics


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
TASK_INTAKE_GUIDANCE_MARKERS = (
    "arms task log",
    ".arms/session.md",
)
ACTIVE_TASKS_HEADER = "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |"


def check_brand_drift(project_root):
    """Analyse BRAND.md for staleness and return a list of drift warning strings.

    Checks performed:
    - Unanswered TBD fields that a ``pyproject.toml`` or ``package.json`` could fill.
    - ``Project Name`` in BRAND.md does not match the name in ``pyproject.toml``.
    """
    wp = WorkspacePaths(project_root)
    brand_path = wp.brand
    if not os.path.isfile(brand_path):
        return []

    brand_content = read_text_file(brand_path)
    if not brand_content.strip():
        return []

    warnings = []

    # --- unanswered fields while project metadata exists ----------------------
    missing_fields = get_missing_new_project_brand_fields(brand_content)
    if missing_fields:
        has_package_json = os.path.isfile(os.path.join(project_root, "package.json"))
        has_pyproject = os.path.isfile(os.path.join(project_root, "pyproject.toml"))
        if has_package_json or has_pyproject:
            warnings.append(
                "BRAND.md still has {} unanswered field(s) ({}) but the project has metadata files — "
                "run `arms init` to infer missing values.".format(
                    len(missing_fields),
                    ", ".join(f"`{f}`" for f in missing_fields[:3])
                    + (" …" if len(missing_fields) > 3 else ""),
                )
            )

    # --- project-name mismatch ------------------------------------------------
    brand_project_name = extract_brand_field(brand_content, "Project Name").strip().lower()
    if brand_project_name and brand_project_name not in {"tbd", "unknown", ""}:
        pyproject_path = os.path.join(project_root, "pyproject.toml")
        if os.path.isfile(pyproject_path):
            pyproject_meta = parse_pyproject_metadata(read_text_file(pyproject_path))
            pkg_name = pyproject_meta.get("name", "").strip().lower()
            if pkg_name and pkg_name != brand_project_name:
                warnings.append(
                    "BRAND.md `Project Name` (`{}`) does not match `pyproject.toml` name (`{}`). "
                    "Update BRAND.md or re-run `arms init` to resync.".format(
                        extract_brand_field(brand_content, "Project Name").strip(),
                        pyproject_meta["name"].strip(),
                    )
                )

    return warnings


def identify_doctor_command(command_parts):
    normalized = tuple(part.strip().lower() for part in command_parts if part.strip())
    return normalized == ("doctor",)


def handle_doctor_command(project_root, arms_root, apply_fixes=False):
    repairs = []
    repair_notes = []
    if apply_fixes:
        repairs, repair_notes = apply_safe_doctor_repairs(project_root, arms_root)
    report = build_doctor_report(project_root, arms_root)
    report["repair_mode"] = apply_fixes
    report["repairs"] = repairs
    report["repair_notes"] = repair_notes
    emit_doctor_response(report)
    if report["counts"]["fail"] > 0:
        raise SystemExit(1)


def build_doctor_report(project_root, arms_root):
    categories = OrderedDict(
        (
            ("Workspace Health", []),
            ("Context Budgets", []),
            ("Version Diagnostics", []),
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

    brand_drift_warnings = check_brand_drift(project_root)
    if brand_drift_warnings:
        for drift_warning in brand_drift_warnings:
            add_check(
                categories,
                counts,
                "Workspace Health",
                "warn",
                drift_warning,
            )
    else:
        brand_path = WorkspacePaths(project_root).brand
        if os.path.isfile(brand_path):
            add_check(
                categories,
                counts,
                "Workspace Health",
                "ok",
                "BRAND.md has no detected drift against project metadata.",
            )

    session_path = WorkspacePaths(project_root).session
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
    validate_version_diagnostics(arms_root, categories, counts)
    validate_token_budget(
        project_root,
        ".arms/SESSION.md",
        SESSION_TOKEN_BUDGET,
        "hot-context session",
        categories,
        counts,
        "Keep only active execution context in `.arms/SESSION.md`, archive completed work, or run `arms init compress`.",
    )
    validate_token_budget(
        project_root,
        ".arms/CONTEXT_SYNTHESIS.md",
        CONTEXT_SYNTHESIS_TOKEN_BUDGET,
        "context synthesis",
        categories,
        counts,
        "Trim duplicated intake detail in `.arms/BRAND.md` or tighten synthesis output before rerunning `arms init`.",
    )
    validate_token_budget(
        project_root,
        ".arms/GENERATED_PROMPTS.md",
        GENERATED_PROMPTS_TOKEN_BUDGET,
        "generated prompts",
        categories,
        counts,
        "Keep prompts thin and reference `.arms/CONTEXT_SYNTHESIS.md` instead of repeating dense context.",
    )

    validate_synced_file(
        project_root,
        os.path.join(arms_root, "ENGINE.md"),
        WorkspacePaths(project_root).engine,
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
    validate_synced_file(
        project_root,
        os.path.join(arms_root, "agents.yaml"),
        os.path.join(project_root, ".gemini", "agents.yaml"),
        "Ownership Safety",
        "Mirrored agent registry",
        categories,
        counts,
        "Rerun `arms init` to resync `.gemini/agents.yaml` from the engine source.",
    )
    validate_engine_repo_readme_roster(project_root, arms_root, categories, counts)

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
        missing_task_intake_files = [
            relative_path
            for relative_path in detected_instruction_files
            if not project_instruction_has_task_intake_guidance(project_root, relative_path)
        ]
        if missing_task_intake_files:
            add_check(
                categories,
                counts,
                "Ownership Safety",
                "warn",
                "Project-owned instruction files are missing ARMS task-intake guidance: {}.".format(
                    ", ".join(f"`{path}`" for path in missing_task_intake_files)
                ),
                "Add the normal-chat rule that durable asks must create or refresh `.arms/SESSION.md` rows using `arms task log` / `arms task update` semantics.",
            )
        else:
            add_check(
                categories,
                counts,
                "Ownership Safety",
                "ok",
                "Project-owned instruction files include ARMS task-intake guidance for normal chat.",
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
    wp = WorkspacePaths(project_root)
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
    deploy_workflow_path = WorkspacePaths(project_root).workflow_file("DEPLOY_PROTOCOL.md")
    if not os.path.isfile(deploy_workflow_path):
        deploy_prereqs.append(".arms/workflow/DEPLOY_PROTOCOL.md")
    if not os.path.isdir(WorkspacePaths(project_root).reports_dir):
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


def apply_safe_doctor_repairs(project_root, arms_root):
    session_path = WorkspacePaths(project_root).session
    if not os.path.isfile(session_path):
        return [], [
            "Skipped automatic repair because `.arms/SESSION.md` is missing. Run `arms init` before using `arms doctor --fix`."
        ]

    session_content = read_text_file(session_path)
    recorded_engine_version = extract_session_engine_version(session_content)
    if recorded_engine_version and compare_versions(recorded_engine_version, __version__) > 0:
        return [], [
            "Skipped automatic repair because the workspace was last synced with newer engine version `{}` than the current engine `{}`.".format(
                recorded_engine_version,
                __version__,
            )
        ]

    removed_obsolete = remove_obsolete_gemini_skill_artifacts(project_root)
    with redirect_stdout(io.StringIO()):
        sync_agents(arms_root, project_root)
        sync_agents_copilot(arms_root, project_root)
        sync_skills_copilot(arms_root, project_root)
        create_skills_registry(arms_root, project_root)
        sync_workflow(arms_root, project_root)
        sync_engine_instructions(arms_root, project_root)
        sync_root_agents_guide(arms_root, project_root)

    repairs = [
        "Resynced `.gemini/agents/` and `.gemini/agents.yaml` from the engine.",
        "Resynced `.github/agents/` from the engine.",
        "Rebuilt `.agents/skills/`, `.github/skills/`, and the generated skill registries.",
        "Resynced `.arms/workflow/`, `.arms/ENGINE.md`, and the root `AGENTS.md` guide.",
    ]
    if removed_obsolete:
        repairs.append(
            "Removed obsolete Gemini skill artifacts: {}.".format(
                ", ".join(f"`{path}`" for path in removed_obsolete)
            )
        )
    return repairs, []


def validate_agent_mirrors(project_root, arms_root, categories, counts):
    source_agents_dir = os.path.join(arms_root, "agents")
    agent_registry = {
        agent["name"]: agent
        for agent in load_agents_registry(arms_root)
    }
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
            continue

        out_of_sync = []
        for filename in mirrored_files:
            source_path = os.path.join(source_agents_dir, filename)
            mirrored_path = os.path.join(mirror_dir, filename)
            agent_name = os.path.splitext(filename)[0]
            expected_content = build_agent_sync_content(
                read_text_file(source_path),
                agent_registry.get(agent_name, {}),
            )
            if expected_content != read_text_file(mirrored_path):
                out_of_sync.append(f"`{filename}`")
        if out_of_sync:
            mismatches.append(
                "`{}` has stale content in {}".format(
                    relative_dir,
                    ", ".join(out_of_sync),
                )
            )

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
            "Rerun `arms init` to rebuild `.agents/skills/`, `.github/skills/`, and the generated skill registries.",
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
    mirror_dir = WorkspacePaths(project_root).workflow_dir
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


def validate_version_diagnostics(arms_root, categories, counts):
    diagnostics = collect_version_diagnostics(arms_root, __version__)
    details = [
        "runtime `{}`".format(diagnostics["runtime_version"] or "unavailable"),
        "git describe `{}`".format(diagnostics["git_describe_raw"] or "unavailable"),
        "latest tag `{}`".format(diagnostics["latest_tag"] or "unavailable"),
        "generated `_version.py` `{}`".format(diagnostics["generated_version"] or "unavailable"),
        "installed package `{}`".format(diagnostics["installed_version"] or "unavailable"),
    ]
    add_check(
        categories,
        counts,
        "Version Diagnostics",
        "ok",
        "Version sources: {}.".format(", ".join(details)),
    )

    runtime_version = diagnostics["runtime_version"]
    git_describe_version = diagnostics["git_describe_version"]
    if git_describe_version and runtime_version and git_describe_version != runtime_version:
        add_check(
            categories,
            counts,
            "Version Diagnostics",
            "warn",
            "Runtime version `{}` does not match git describe `{}`.".format(
                runtime_version,
                git_describe_version,
            ),
            "Prefer the git-tagged checkout or refresh the installed package so CLI version output matches the current source tree.",
        )
        return

    installed_version = diagnostics["installed_version"]
    if installed_version and runtime_version and installed_version != runtime_version:
        add_check(
            categories,
            counts,
            "Version Diagnostics",
            "warn",
            "Runtime version `{}` does not match installed package metadata `{}`.".format(
                runtime_version,
                installed_version,
            ),
            "Reinstall or upgrade the package if the CLI should match the installed distribution metadata.",
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


def validate_token_budget(project_root, relative_path, budget, label, categories, counts, fix):
    target_path = os.path.join(project_root, relative_path)
    if not os.path.isfile(target_path):
        return

    budget_assessment = assess_token_budget(read_text_file(target_path), budget)
    tokens = budget_assessment["tokens"]
    warn_at = budget_assessment["warn_at"]
    if budget_assessment["status"] == "fail":
        add_check(
            categories,
            counts,
            "Context Budgets",
            "fail",
            "{} `{}` uses {} tokens, exceeding the budget of {}.".format(
                label.capitalize(),
                relative_path,
                tokens,
                budget,
            ),
            fix,
        )
        return
    if budget_assessment["status"] == "warn":
        add_check(
            categories,
            counts,
            "Context Budgets",
            "warn",
            "{} `{}` uses {} tokens, nearing the warning threshold of {} / {}.".format(
                label.capitalize(),
                relative_path,
                tokens,
                warn_at,
                budget,
            ),
            fix,
        )
        return
    add_check(
        categories,
        counts,
        "Context Budgets",
        "ok",
        "{} `{}` stays within budget at {} / {} tokens.".format(
            label.capitalize(),
            relative_path,
            tokens,
            budget,
        ),
    )


def validate_engine_repo_readme_roster(project_root, arms_root, categories, counts):
    repo_root = os.path.abspath(os.path.join(arms_root, os.pardir))
    if os.path.abspath(project_root) != repo_root:
        return

    readme_path = os.path.join(project_root, "README.md")
    if not os.path.isfile(readme_path):
        return

    readme_content = read_text_file(readme_path)
    start_marker = "<!-- AGENT_ROSTER_START -->"
    end_marker = "<!-- AGENT_ROSTER_END -->"
    if start_marker not in readme_content or end_marker not in readme_content:
        add_check(
            categories,
            counts,
            "Ownership Safety",
            "fail",
            "Engine README roster markers are missing from `README.md`.",
            "Restore the README roster markers or rerun `arms-docs` after replacing them.",
        )
        return

    start_index = readme_content.rfind(start_marker)
    end_index = readme_content.rfind(end_marker)
    actual_roster = ""
    if start_index != -1 and end_index != -1 and end_index > start_index:
        actual_roster = readme_content[start_index + len(start_marker):end_index].strip()
    expected_roster = get_agent_docs(arms_root).strip()
    if actual_roster != expected_roster:
        add_check(
            categories,
            counts,
            "Ownership Safety",
            "fail",
            "Engine README agent roster is out of sync with `arms_engine/agents.yaml`.",
            "Run `arms-docs` to regenerate the README roster block before release.",
        )
        return

    add_check(
        categories,
        counts,
        "Ownership Safety",
        "ok",
        "Engine README agent roster matches `arms_engine/agents.yaml`.",
    )


def has_environment_key(environment_content, key):
    pattern = r"^- {}: .+$".format(re.escape(key))
    return bool(re.search(pattern, environment_content or "", re.MULTILINE))


def project_instruction_has_task_intake_guidance(project_root, relative_path):
    content = read_text_file(os.path.join(project_root, relative_path)).lower()
    return all(marker in content for marker in TASK_INTAKE_GUIDANCE_MARKERS)


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

    if report.get("repair_mode"):
        body_lines.append("### Repair Mode")
        if report.get("repairs"):
            for repair in report["repairs"]:
                body_lines.append("- [FIXED] {}".format(repair))
        if report.get("repair_notes"):
            for note in report["repair_notes"]:
                body_lines.append("- [SKIPPED] {}".format(note))
        if not report.get("repairs") and not report.get("repair_notes"):
            body_lines.append("- No automatic repairs were necessary.")
        body_lines.append("")

    for category, checks in report["categories"].items():
        if not checks:
            continue
        body_lines.append("### {}".format(category))
        for check in checks:
            body_lines.append("- [{}] {}".format(check["status"].upper(), check["summary"]))
            if check["fix"]:
                body_lines.append("  Fix: {}".format(check["fix"]))
        body_lines.append("")

    fails = collect_report_items(report, "fail")
    warns = collect_report_items(report, "warn")
    fixed = report.get("repairs") or []
    skipped = report.get("repair_notes") or []
    body_lines.append("### Final Triage")
    if fails:
        body_lines.append("- Blocking issues ({}): {}".format(len(fails), "; ".join(fails)))
    else:
        body_lines.append("- Blocking issues: none.")
    if warns:
        body_lines.append("- Warnings ({}): {}".format(len(warns), "; ".join(warns)))
    else:
        body_lines.append("- Warnings: none.")
    if fixed:
        body_lines.append("- Safe repairs applied ({}): {}".format(len(fixed), "; ".join(fixed)))
    else:
        body_lines.append("- Safe repairs applied: none.")
    if skipped:
        body_lines.append("- Repair notes ({}): {}".format(len(skipped), "; ".join(skipped)))
    body_lines.append("")

    if counts["fail"]:
        if report.get("repair_mode") and report.get("repairs"):
            next_step = "Doctor repaired what it could, but {} blocking issue(s) remain. Resolve the remaining failures and rerun `arms doctor --fix` or `arms doctor`. → HALT".format(
                counts["fail"]
            )
        else:
            next_step = "Doctor found {} blocking issue(s). Fix the failing items and rerun `arms doctor`. → HALT".format(
                counts["fail"]
            )
    else:
        if report.get("repair_mode") and report.get("repairs"):
            next_step = "Workspace health check complete. Safe automatic repairs were applied; address any warnings as needed before continuing. → HALT"
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


def collect_report_items(report, status):
    items = []
    for checks in report["categories"].values():
        for check in checks:
            if check["status"] == status:
                items.append(check["summary"])
    return items
