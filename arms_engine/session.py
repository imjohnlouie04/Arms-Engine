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


MEMORY_TEMPLATE = """# ARMS Project Memory

> Managed by ARMS Engine. This is a continuous learning file. APPEND only; never overwrite.

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
- Read `.arms/SESSION.md`, `.arms/BRAND.md`, and `.arms/MEMORY.md` before major changes.
- Ask the user for approval before updating `.arms/MEMORY.md`; only append after approval, and never overwrite it wholesale.
- Keep `.arms/SESSION.md` synchronized with task progress and blockers.
"""
SESSION_ARCHIVE_TEMPLATE = """# ARMS Session Archive

> Managed by ARMS Engine. Append completed or cancelled work here; never delete history.
"""


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
        ".gemini/skills",
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


def update_session(project_root, arms_root, skills_list, agents_list, yolo=False, startup_tasks_content="", context_overwrite=None):
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
{agents_list}

## Active Skills
{skills_list}

{tasks_content}"""

    write_text_atomic(session_path, content)
    return True
