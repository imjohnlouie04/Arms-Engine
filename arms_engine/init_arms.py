import os
import sys
import shutil
import datetime
import argparse
import json
import re
import textwrap
import time
import hashlib

try:
    import yaml
except ImportError:
    yaml = None

try:
    from ._version import version as __version__
except (ImportError, ValueError):
    __version__ = "1.3.5-dev" # Fallback for local development

NEW_PROJECT_BRAND_MARKER = "> New project detected."
NEW_PROJECT_BRAND_FIELDS = (
    "Mission",
    "Vision",
    "Personality",
    "Voice & Tone",
    "Primary Audience",
    "Core Values",
    "Differentiation",
    "Color Palette",
    "Typography",
    "Logo Status",
    "Visual Direction",
    "Project Type",
    "Design Priority",
    "Preferred Tech Stack",
    "Deployment Target",
    "Backend / Data Layer",
    "Authentication Requirement",
    "Technical Constraints",
    "Experience Type",
    "Industry / Business Niche",
    "Service Area / Local SEO Target",
    "Required Website Sections",
    "Primary Calls to Action",
    "Icon System",
    "Image Requirements",
    "SEO Focus",
)
BOOTSTRAP_ONLY_FILES = {
    "README.md",
    "README.mdx",
    "LICENSE",
    "LICENSE.md",
    "CHANGELOG",
    "CHANGELOG.md",
}
SOURCE_FILE_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".cs",
    ".swift",
    ".scala",
    ".sh",
}
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
- Append new project knowledge to `.arms/MEMORY.md`; never overwrite it wholesale.
- Keep `.arms/SESSION.md` synchronized with task progress and blockers.
"""
SESSION_ARCHIVE_TEMPLATE = """# ARMS Session Archive

> Managed by ARMS Engine. Append completed or cancelled work here; never delete history.
"""
GENERATED_PROMPTS_HEADER = """# ARMS Generated Prompts

> Managed by ARMS Engine. Regenerated from `.arms/BRAND.md` during `arms init`.
> Update the brand brief and re-run `arms init` to refresh these prompts.
"""
WATCH_POLL_INTERVAL_SECONDS = 2.0

def get_arms_root():
    # When installed as a package, this is the arms_engine directory
    return os.path.dirname(os.path.abspath(__file__))

def get_project_root():
    """Resolve the active project root.

    If the current directory is effectively empty, treat it as a new project root
    instead of climbing to a parent repository marker.
    """
    curr = os.getcwd()
    original_cwd = curr

    meaningful_entries = [
        name for name in os.listdir(original_cwd)
        if name not in IGNORED_PROJECT_ENTRIES and not name.startswith(".")
    ]
    if not meaningful_entries and not any(
        os.path.exists(os.path.join(original_cwd, marker))
        for marker in [".git", ".arms", ".gemini", "package.json"]
    ):
        return original_cwd

    while curr != os.path.dirname(curr):
        if any(os.path.exists(os.path.join(curr, m)) for m in [".git", ".arms", ".gemini", "package.json"]):
            return curr
        curr = os.path.dirname(curr)
    return original_cwd

def setup_folders(project_root):
    # .agents/ — Skill & agent discovery folder (detected by Gemini CLI and Copilot CLI)
    agents_folders = [
        ".agents/skills",
    ]
    # .gemini/ — Gemini AI assistant config and mirrored assets
    gemini_folders = [
        ".gemini/agents",
        
    ]
    # .arms/ — ARMS engine state (SESSION.md, SESSION_ARCHIVE.md, BRAND.md, MEMORY.md)
    arms_folders = [
        ".arms",
        ".arms/agent-outputs",
        ".arms/reports",
        ".arms/workflow",
    ]
    for folder in agents_folders + gemini_folders + arms_folders:
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
        os.path.join(project_root, ".gemini/RULES.md"),
        RULES_TEMPLATE,
        ".gemini/RULES.md",
    )

def clean_legacy_gemini_skill_mirror(project_root):
    legacy_dir = os.path.join(project_root, ".gemini/skills")
    if not os.path.isdir(legacy_dir):
        return

    removed_entries = False
    for entry in os.listdir(legacy_dir):
        entry_path = os.path.join(legacy_dir, entry)
        if os.path.isdir(entry_path):
            shutil.rmtree(entry_path)
            removed_entries = True
        elif os.path.isfile(entry_path) and entry.endswith(".md"):
            os.remove(entry_path)
            removed_entries = True

    if removed_entries:
        print("🧹 Removed legacy .gemini/skills mirror to prevent duplicate CLI skill discovery.")

def migrate_legacy_state(project_root):
    """Move legacy project-state files into .arms/ without overwriting existing state."""
    migrations = [
        (
            "session log",
            os.path.join(project_root, ".gemini/SESSION.md"),
            os.path.join(project_root, ".arms/SESSION.md"),
        ),
        (
            "session archive",
            os.path.join(project_root, ".gemini/SESSION_ARCHIVE.md"),
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
            "project memory",
            os.path.join(project_root, ".gemini/MEMORY.md"),
            os.path.join(project_root, ".arms/MEMORY.md"),
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
                shutil.move(legacy_entry, target_entry)
                moved_any = True
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
        shutil.move(legacy_path, target_path)

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
    """Upgrade legacy Active Tasks tables to the current schema and repair stale skill cells."""
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

def sync_agents(arms_root, project_root):
    print("🤖 Syncing Agents...")
    agents_dir = os.path.join(arms_root, "agents")
    target_dir = os.path.join(project_root, ".gemini/agents")
    
    if os.path.exists(agents_dir):
        for filename in os.listdir(agents_dir):
            if filename.endswith(".md"):
                src = os.path.join(agents_dir, filename)
                dest = os.path.join(target_dir, filename)
                
                with open(src, 'r') as f:
                    content = f.read()
                
                if "tools:" not in content:
                    # Insert tools: ["*"] after the first ---
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = "---\ntools: [\"*\"]" + parts[1] + "---" + parts[2]
                
                with open(dest, 'w') as f:
                    f.write(content)
    
    # Sync agents.yaml
    yaml_src = os.path.join(arms_root, "agents.yaml")
    yaml_dest = os.path.join(project_root, ".gemini/agents.yaml")
    if os.path.exists(yaml_src):
        print("📄 Syncing agents.yaml...")
        shutil.copy(yaml_src, yaml_dest)

def sync_agents_copilot(arms_root, project_root):
    """Sync agent .md files to .github/agents/ for Copilot CLI /agent discovery."""
    print("🤖 Syncing Agents for Copilot CLI...")
    agents_dir = os.path.join(arms_root, "agents")
    target_dir = os.path.join(project_root, ".github/agents")
    os.makedirs(target_dir, exist_ok=True)

    if os.path.exists(agents_dir):
        for filename in os.listdir(agents_dir):
            if filename.endswith(".md"):
                src = os.path.join(agents_dir, filename)
                dest = os.path.join(target_dir, filename)
                with open(src, 'r') as f:
                    content = f.read()
                
                # Ensure tools: ["*"] is present for Copilot CLI discovery
                if "tools:" not in content:
                    # Insert tools: ["*"] after the first ---
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = "---\ntools: [\"*\"]" + parts[1] + "---" + parts[2]
                
                with open(dest, 'w') as f:
                    f.write(content)

def infer_skill_description(content, skill_name):
    lines = content.splitlines()
    start_index = 0
    if lines and lines[0].strip() == "---":
        for idx, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                start_index = idx + 1
                break

    for raw_line in lines[start_index:]:
        line = raw_line.strip()
        if not line:
            continue
        if line == "---":
            continue
        if line.startswith("#"):
            continue
        if line.startswith("**ID"):
            continue
        if line.startswith("**Role"):
            return re.sub(r"^\*\*Role:?\*\*:?\s*", "", line).strip().strip(".")
        return line[:240]
    return f"Specialized guidance for {skill_name.replace('-', ' ')}."

def parse_skill_metadata(skill_md_path, fallback_name):
    metadata = {"name": fallback_name, "description": ""}
    with open(skill_md_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    lines = content.splitlines()
    if lines and lines[0].strip() == "---":
        frontmatter_lines = []
        for line in lines[1:]:
            if line.strip() == "---":
                break
            frontmatter_lines.append(line)
        frontmatter = "\n".join(frontmatter_lines)
        if frontmatter.strip():
            parsed_frontmatter = {}
            if yaml is not None:
                try:
                    parsed_frontmatter = yaml.safe_load(frontmatter) or {}
                except yaml.YAMLError:
                    parsed_frontmatter = {}
            if not isinstance(parsed_frontmatter, dict) or not parsed_frontmatter:
                idx = 0
                while idx < len(frontmatter_lines):
                    line = frontmatter_lines[idx]
                    if ":" not in line or line.startswith((" ", "\t")):
                        idx += 1
                        continue
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if value in {">", "|"}:
                        block_lines = []
                        idx += 1
                        while idx < len(frontmatter_lines):
                            next_line = frontmatter_lines[idx]
                            if next_line.startswith((" ", "\t")):
                                block_lines.append(next_line.strip())
                                idx += 1
                                continue
                            break
                        separator = " " if value == ">" else "\n"
                        parsed_frontmatter[key] = separator.join(part for part in block_lines if part).strip()
                        continue
                    parsed_frontmatter[key] = value.strip('"').strip("'")
                    idx += 1
            if isinstance(parsed_frontmatter, dict):
                for key, value in parsed_frontmatter.items():
                    normalized_key = str(key).strip().lower()
                    if isinstance(value, str):
                        metadata[normalized_key] = " ".join(value.split()).strip()
                    elif value is not None:
                        metadata[normalized_key] = str(value).strip()

    metadata["name"] = metadata.get("name") or fallback_name
    raw_description = metadata.get("description", "")
    if raw_description in {"", ">", "|"}:
        raw_description = infer_skill_description(content, fallback_name)
    metadata["description"] = raw_description
    return metadata

def ensure_skill_frontmatter(content, skill_name):
    stripped = content.lstrip()
    if stripped.startswith("---"):
        return content

    description = infer_skill_description(content, skill_name)
    frontmatter = (
        "---\n"
        f"name: {skill_name}\n"
        f"description: {json.dumps(description)}\n"
        "---\n\n"
    )
    return frontmatter + stripped

def sync_skills_copilot(arms_root, project_root):
    """Sync skill directories to CLI discovery folders."""
    print("🔌 Syncing Skills for CLI discovery...")
    skills_src = os.path.join(arms_root, "skills")
    target_dirs = [
        os.path.join(project_root, ".agents/skills"),
    ]
    for target_dir in target_dirs:
        os.makedirs(target_dir, exist_ok=True)
        for entry in os.listdir(target_dir):
            entry_path = os.path.join(target_dir, entry)
            if os.path.isdir(entry_path):
                shutil.rmtree(entry_path)
            elif os.path.isfile(entry_path):
                os.remove(entry_path)

    if os.path.exists(skills_src):
        for skill_name in os.listdir(skills_src):
            skill_path = os.path.join(skills_src, skill_name)
            skill_md_path = os.path.join(skill_path, "SKILL.md")
            
            if os.path.isdir(skill_path) and os.path.exists(skill_md_path):
                metadata = parse_skill_metadata(skill_md_path, skill_name)
                for target_dir in target_dirs:
                    legacy_dest = os.path.join(target_dir, f"{skill_name}.md")
                    if os.path.isfile(legacy_dest):
                        os.remove(legacy_dest)

                    dest_dir = os.path.join(target_dir, skill_name)
                    shutil.copytree(
                        skill_path,
                        dest_dir,
                        ignore=shutil.ignore_patterns(".DS_Store", "__pycache__"),
                    )

                    dest_skill_md_path = os.path.join(dest_dir, "SKILL.md")
                    with open(dest_skill_md_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    normalized_content = ensure_skill_frontmatter(content, metadata["name"])

                    with open(dest_skill_md_path, 'w', encoding='utf-8') as f:
                        f.write(normalized_content)

def create_skills_registry(arms_root, project_root):
    """Create a skills registry file for CLI discovery."""
    print("📋 Creating Skills Registry...")
    skills_src = os.path.join(arms_root, "skills")
    registry_dest = os.path.join(project_root, ".agents/skills.yaml")
    index_dest = os.path.join(project_root, ".agents/skills-index.md")
    
    skills_data = {}
    if os.path.exists(skills_src):
        for skill_name in sorted(os.listdir(skills_src)):
            skill_path = os.path.join(skills_src, skill_name)
            skill_md_path = os.path.join(skill_path, "SKILL.md")
            
            if os.path.isdir(skill_path) and os.path.exists(skill_md_path):
                metadata = parse_skill_metadata(skill_md_path, skill_name)
                canonical_name = metadata["name"]
                skills_data[canonical_name] = {
                    "name": canonical_name,
                    "description": metadata["description"],
                    "source_directory": skill_name,
                }
    
    # Write YAML registry
    with open(registry_dest, 'w') as f:
        f.write("# ARMS Skills Registry\n")
        f.write("# Auto-generated by arms init\n\n")
        f.write("skills:\n")
        for skill_name, skill_info in sorted(skills_data.items()):
            f.write(f"  {skill_name}:\n")
            f.write(f"    name: {skill_info['name']}\n")
            f.write(f"    description: {skill_info['description']}\n")
            if skill_info["source_directory"] != skill_name:
                f.write(f"    source_directory: {skill_info['source_directory']}\n")
    
    # Write Markdown index for quick reference
    with open(index_dest, 'w') as f:
        f.write("# ARMS Skills Index\n\n")
        f.write("> **Quick reference:** All available skills for supported CLIs\n\n")
        f.write("## Available Skills\n\n")
        for skill_name, skill_info in sorted(skills_data.items()):
            f.write(f"### `{skill_name}/SKILL.md`\n")
            f.write(f"**{skill_info['name']}**\n\n")
            f.write(f"{skill_info['description']}\n\n")
            skill_file_dir = skill_info["source_directory"]
            f.write(f"**File:** `.agents/skills/{skill_file_dir}/SKILL.md`\n\n")
            if skill_info["source_directory"] != skill_name:
                f.write(f"**Source Directory:** `arms_engine/skills/{skill_info['source_directory']}`\n\n")
        
        f.write("## Usage\n\n")
        f.write("Reference a skill from the local `.agents/skills/` mirror:\n\n")
        f.write("```\n")
        f.write(".agents/skills/arms-orchestrator/SKILL.md\n")
        f.write("Describe your task here\n")
        f.write("```\n")

def sync_copilot_instructions(arms_root, project_root):
    """Deploy AGENTS.md to the project root for Copilot CLI instruction loading."""
    print("📄 Syncing AGENTS.md (Copilot Instructions)...")
    src = os.path.join(arms_root, "AGENTS.md")
    dest = os.path.join(project_root, "AGENTS.md")
    if os.path.exists(src):
        shutil.copy2(src, dest)

def sync_workflow(arms_root, project_root):
    print("📋 Syncing Workflow Protocols...")
    wf_src = os.path.join(arms_root, "workflow")
    wf_dest = os.path.join(project_root, ".arms/workflow")
    
    if os.path.exists(wf_src):
        for filename in os.listdir(wf_src):
            src = os.path.join(wf_src, filename)
            dest = os.path.join(wf_dest, filename)
            if os.path.isfile(src):
                shutil.copy(src, dest)

AGENT_SKILL_HINTS = {
    "arms-main-agent": {
        "orchestrator", "orchestration", "workflow", "session", "memory", "compressor", "docs",
    },
    "arms-product-agent": {
        "product", "requirements", "roadmap", "planning", "docs",
    },
    "arms-backend-agent": {
        "backend", "api", "server", "architecture", "architect", "microservices", "distributed",
    },
    "arms-frontend-agent": {
        "frontend", "ui", "design", "component", "styling", "css",
    },
    "arms-devops-agent": {
        "devops", "deployment", "deploy", "ci", "cd", "cicd", "infrastructure",
        "gitops", "terraform", "ansible", "pulumi", "kubernetes", "cloud", "drift",
    },
    "arms-seo-agent": {
        "seo", "search", "metadata", "web", "performance", "lighthouse", "vitals",
    },
    "arms-media-agent": {
        "media", "logo", "image", "images", "visual", "graphics", "banana",
    },
    "arms-data-agent": {
        "data", "schema", "migration", "query", "postgres", "database",
    },
    "arms-qa-agent": {
        "qa", "test", "tests", "testing", "playwright", "cypress", "jest",
    },
    "arms-security-agent": {
        "security", "owasp", "auth", "authentication", "rls", "vulnerability",
    },
}

def discover_skill_catalog(arms_root):
    skills_dir = os.path.join(arms_root, "skills")
    skills = []
    if os.path.exists(skills_dir):
        for directory_name in sorted(os.listdir(skills_dir)):
            path = os.path.join(skills_dir, directory_name)
            skill_md_path = os.path.join(path, "SKILL.md")
            if os.path.isdir(path) and os.path.exists(skill_md_path):
                metadata = parse_skill_metadata(skill_md_path, directory_name)
                skills.append(
                    {
                        "name": metadata["name"],
                        "description": metadata["description"],
                        "source_directory": directory_name,
                    }
                )
    return skills

def discover_skills(arms_root):
    print("🔍 Discovering Skills...")
    skills = []
    for skill in discover_skill_catalog(arms_root):
        skills.append(f"- {skill['name']} [Active]")
    return "\n".join(skills)

def load_agents_registry(arms_root):
    yaml_path = os.path.join(arms_root, "agents.yaml")
    if not os.path.exists(yaml_path):
        return []

    with open(yaml_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if yaml is not None:
        try:
            parsed = yaml.safe_load(content) or {}
        except yaml.YAMLError:
            parsed = {}
        raw_agents = parsed.get("agents", {})
        if isinstance(raw_agents, dict):
            agents = []
            for agent_name, info in raw_agents.items():
                if not isinstance(info, dict):
                    info = {}
                raw_skills = info.get("skills") or []
                if not isinstance(raw_skills, list):
                    raw_skills = []
                agents.append(
                    {
                        "name": str(agent_name).strip(),
                        "role": str(info.get("role", "")).strip(),
                        "scope": str(info.get("scope", "")).strip(),
                        "skills": [str(skill).strip() for skill in raw_skills if str(skill).strip()],
                    }
                )
            return agents

    agents = []
    current_agent = None
    in_skills = False

    for line in content.splitlines():
        agent_match = re.match(r'^\s\s([\w-]+):', line)
        if agent_match:
            if current_agent:
                agents.append(current_agent)
            current_agent = {
                "name": agent_match.group(1),
                "role": "",
                "scope": "",
                "skills": [],
            }
            in_skills = False
            continue

        if not current_agent:
            continue

        role_match = re.match(r'^\s\s\s\srole:\s*(.*)$', line)
        if role_match:
            current_agent["role"] = role_match.group(1).strip()
            in_skills = False
            continue

        scope_match = re.match(r'^\s\s\s\sscope:\s*(.*)$', line)
        if scope_match:
            current_agent["scope"] = scope_match.group(1).strip()
            in_skills = False
            continue

        if re.match(r'^\s\s\s\sskills:\s*$', line):
            in_skills = True
            continue

        if in_skills:
            skill_match = re.match(r'^\s\s\s\s\s\s-\s([\w-]+)', line)
            if skill_match:
                current_agent["skills"].append(skill_match.group(1))
                continue
            if line.strip() and not line.strip().startswith("-"):
                in_skills = False

    if current_agent:
        agents.append(current_agent)

    return agents

def score_agent_skill_match(agent, skill):
    skill_name = skill["name"].lower()
    description = skill["description"].lower()
    skill_text = f"{skill_name} {description}"
    agent_name = agent["name"]
    agent_text = f"{agent_name} {agent.get('role', '')} {agent.get('scope', '')}".lower()

    score = 0
    for hint in AGENT_SKILL_HINTS.get(agent_name, set()):
        if hint in skill_name:
            score += 4
        elif hint in skill_text:
            score += 2

    agent_tokens = {token for token in re.findall(r"[a-z0-9]+", agent_text) if len(token) >= 3}
    skill_name_tokens = {token for token in re.findall(r"[a-z0-9]+", skill_name) if len(token) >= 3}
    skill_tokens = {token for token in re.findall(r"[a-z0-9]+", skill_text) if len(token) >= 4}

    for token in skill_name_tokens & agent_tokens:
        score += 3
    for token in skill_tokens & agent_tokens:
        score += 1

    return score

def infer_agent_skill_bindings(agents, skills):
    bound_skills = {
        skill_name
        for agent in agents
        for skill_name in agent.get("skills", [])
    }
    inferred_bindings = []

    for skill in skills:
        skill_name = skill["name"]
        if skill_name in bound_skills:
            continue

        scored_agents = []
        for agent in agents:
            score = score_agent_skill_match(agent, skill)
            if score > 0:
                scored_agents.append((score, agent["name"], agent))

        if not scored_agents:
            continue

        scored_agents.sort(key=lambda item: (-item[0], item[1]))
        best_score, best_name, best_agent = scored_agents[0]
        if len(scored_agents) > 1 and best_score == scored_agents[1][0]:
            continue

        best_agent.setdefault("skills", []).append(skill_name)
        bound_skills.add(skill_name)
        inferred_bindings.append((skill_name, best_name))

    return inferred_bindings

def resolve_agents_with_skills(arms_root, announce=False):
    agents = load_agents_registry(arms_root)
    skill_catalog = discover_skill_catalog(arms_root)
    inferred_bindings = infer_agent_skill_bindings(agents, skill_catalog)
    if announce:
        for skill_name, agent_name in inferred_bindings:
            print(f"🧩 Auto-assigned skill '{skill_name}' to {agent_name}.")
    return agents, skill_catalog, inferred_bindings

def build_agent_skill_bindings(agents):
    return {
        agent["name"]: list(agent.get("skills", []))
        for agent in agents
    }

def discover_agents_and_skills(arms_root):
    print("👥 Discovering Agents & associated Skills...")
    agents, _, _ = resolve_agents_with_skills(arms_root, announce=True)

    agents_info = []
    for agent in agents:
        current_skills = agent.get("skills", [])
        skills_str = f" ({', '.join(current_skills)})" if current_skills else ""
        agents_info.append(f"- {agent['name']}{skills_str}")

    return "\n".join(agents_info)

PLACEHOLDER_BRAND_TOKENS = (
    "[Name]",
    "[Purpose]",
    "[Long-term goal]",
    "[Voice/Tone]",
    "[Approach]",
    "[Target]",
    "[Values]",
    "[Unique Factor]",
    "[HEX/OKLCH]",
    "[Google Fonts]",
    "[Generated/Pending]",
    "[Glassmorphism/Dark Mode/etc]",
    "[SaaS/Community/etc]",
    "[UX Factor]",
    "[Misc preferences]",
)

PROJECT_MARKER_FILES = (
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "poetry.lock",
    "go.mod",
    "Cargo.toml",
    "composer.json",
    "Gemfile",
    "pom.xml",
    "build.gradle",
    "README.md",
    "README.mdx",
    "index.html",
)

PROJECT_MARKER_DIRS = (
    "src",
    "app",
    "pages",
    "components",
    "lib",
    "server",
    "backend",
    "frontend",
    "api",
    "public",
    "docs",
)

IGNORED_PROJECT_ENTRIES = {
    ".git",
    ".github",
    ".gemini",
    ".arms",
    ".vscode",
    ".idea",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".DS_Store",
}

NEW_PROJECT_BRAND_QUESTIONS = [
    "1. Primary use case: SaaS · Content/Marketing · Mobile-First · Multi-Purpose",
    "2. Target audience",
    "3. Core features",
    "4. Goal / Monetization model",
    "5. Brand name (or working title if unnamed)",
    "6. Brand personality — pick up to 3 words:",
    "   Bold · Minimal · Playful · Premium · Technical · Warm · Rebellious · Trustworthy · Friendly · Sharp",
    "7. Closest competitor or reference brand? (URL or name)",
    "8. What should your brand feel like vs. that reference?",
    "   e.g. \"Like Notion but warmer\" · \"Like Stripe but more human\"",
    "9. Existing brand assets?",
    "   Logo (Y/N) · Color palette (Y/N) · Typography (Y/N) · Existing site (URL or N)",
    "10. Preferred visual direction: Light · Dark · System default · Undecided",
]

NEW_PROJECT_TECH_STACK_QUESTIONS = [
    "11. Preferred tech stack:",
    "    [A] Next.js + Supabase + shadcn (Latest)",
    "    [B] Nuxt 4 + Firebase + Nuxt UI (Latest)",
    "    [C] Astro + DaisyUI (Latest)",
    "    [D] Custom",
    "12. Preferred deployment target:",
    "    [1] Vercel",
    "    [2] Docker / VPS",
    "    [3] AWS / GCP",
    "13. Preferred backend / data layer if custom or undecided:",
    "    Supabase · Firebase · Postgres · MySQL · REST API · GraphQL · Custom · Unsure",
    "14. Authentication requirement:",
    "    Email/password · OAuth · Magic link · Anonymous/guest · None yet · Unsure",
    "15. Any hard technical constraints or must-use tools?",
    "    e.g. TypeScript only, Tailwind required, self-hosted only, no Firebase, mobile-first, CMS needed",
]

NEW_PROJECT_WEBSITE_BRIEF_QUESTIONS = [
    "16. If this project needs a website or landing page, what experience type is it?",
    "    Local service business · Marketing site · Portfolio · Ecommerce · Editorial · Other · N/A",
    "17. What industry or business niche should the site speak to?",
    "    e.g. classic car restoration, dental clinic, boutique hotel, law firm, SaaS",
    "18. What location or service area matters for local SEO, if any?",
    "    e.g. Austin, Texas · Metro Manila · Nationwide · N/A",
    "19. Which sections must be present on the page?",
    "    e.g. Header/Nav, Hero, Services, Gallery, About, Process, Testimonials, Contact Form, Footer",
    "20. What are the primary calls to action?",
    "    e.g. Request a Quote, Book a Consultation, Call Now, View Recent Work",
    "21. What icon system should the UI use?",
    "    Default to Font Awesome for marketing pages unless there is a stronger requirement",
    "22. What image coverage is needed?",
    "    e.g. 5+ images, hero image, detail shots, before/after work, finished showcase pieces",
    "23. What SEO priorities should the build emphasize?",
    "    e.g. local service keywords, visible contact info, trust signals, semantic headings, descriptive alt text",
    "24. Any content or visual non-negotiables?",
    "    e.g. no emoji, premium tone, visible phone number, dark theme, editorial typography",
]

QUESTION_FIELD_SPECS = (
    (1, "Primary use case", "Primary Use Case"),
    (2, "Target audience", "Primary Audience"),
    (3, "Core features", "Core Features"),
    (4, "Goal / Monetization model", "Goal / Monetization Model"),
    (5, "Brand name", "Project Name"),
    (6, "Brand personality", "Personality"),
    (7, "Closest competitor or reference brand", "Reference Brand"),
    (8, "What should your brand feel like vs. that reference", "Brand Comparison"),
    (9, "Existing brand assets", "Existing Brand Assets"),
    (10, "Preferred visual direction", "Visual Direction"),
    (11, "Preferred tech stack", "Preferred Tech Stack"),
    (12, "Preferred deployment target", "Deployment Target"),
    (13, "Preferred backend / data layer", "Backend / Data Layer"),
    (14, "Authentication requirement", "Authentication Requirement"),
    (15, "Any hard technical constraints or must-use tools", "Technical Constraints"),
    (16, "If this project needs a website or landing page, what experience type is it", "Experience Type"),
    (17, "What industry or business niche should the site speak to", "Industry / Business Niche"),
    (18, "What location or service area matters for local SEO", "Service Area / Local SEO Target"),
    (19, "Which sections must be present on the page", "Required Website Sections"),
    (20, "What are the primary calls to action", "Primary Calls to Action"),
    (21, "What icon system should the UI use", "Icon System"),
    (22, "What image coverage is needed", "Image Requirements"),
    (23, "What SEO priorities should the build emphasize", "SEO Focus"),
    (24, "Any content or visual non-negotiables", "Content / Visual Non-Negotiables"),
)

NOTE_DRIVEN_INTAKE_FIELDS = (
    "Primary Use Case",
    "Core Features",
    "Goal / Monetization Model",
    "Reference Brand",
    "Brand Comparison",
    "Existing Brand Assets",
    "Content / Visual Non-Negotiables",
)

PROJECT_PRESETS = {
    "local-business": {
        "description": "Local service business marketing site defaults with SEO, CTA, and contact visibility baked in.",
        "fields": {
            "Project Type": "Content / Marketing Site",
            "Design Priority": "Conversion-focused trust and local discoverability",
            "Voice & Tone": "Clear, trustworthy, and benefits-first for local buyers",
            "Typography": "Distinctive display typography paired with a highly readable body font",
            "Icon System": "Font Awesome",
            "Experience Type": "Local service business",
            "Required Website Sections": "Header/Nav, Hero, Services, Recent Work/Gallery, About/History, Our Process, Testimonials, Contact Info with Form, Footer",
            "Primary Calls to Action": "Request a Quote, Book a Consultation, Call Now",
            "Image Requirements": "At least 5 images including hero imagery, supporting detail shots, and showcase work",
            "SEO Focus": "Local search intent, visible contact information, trust signals, semantic headings, and descriptive alt text",
            "Technical Constraints": "Mobile-first, clear contact visibility, and no emoji unless explicitly requested",
        },
    },
    "saas": {
        "description": "Product-led SaaS website defaults for conversion, onboarding clarity, and feature communication.",
        "fields": {
            "Project Type": "Web Application",
            "Design Priority": "Conversion-focused product clarity and onboarding confidence",
            "Voice & Tone": "Clear, confident, and product-literate without sounding inflated",
            "Typography": "Modern display typography paired with a clean, highly legible interface body font",
            "Icon System": "Font Awesome",
            "Experience Type": "Marketing site",
            "Required Website Sections": "Header/Nav, Hero, Problem/Solution, Features, Integrations, Social Proof, Pricing, FAQ, CTA, Footer",
            "Primary Calls to Action": "Start Free, Book a Demo, View Product Tour",
            "Image Requirements": "Product UI screenshots, dashboard mockups, and supporting hero imagery",
            "SEO Focus": "Category keywords, product value propositions, semantic headings, metadata, and strong internal linking",
            "Technical Constraints": "Mobile-first, accessible interaction states, and performance-conscious media usage",
        },
    },
    "portfolio": {
        "description": "Portfolio-site defaults emphasizing featured work, case studies, and credibility.",
        "fields": {
            "Project Type": "Content / Marketing Site",
            "Design Priority": "Visual storytelling and clear proof of work",
            "Voice & Tone": "Confident, articulate, and craft-aware",
            "Typography": "Expressive display typography paired with a polished editorial body font",
            "Icon System": "Font Awesome",
            "Experience Type": "Portfolio",
            "Required Website Sections": "Header/Nav, Hero, Featured Work, Case Studies, About, Process, Testimonials, Contact, Footer",
            "Primary Calls to Action": "View Work, Start a Project, Contact",
            "Image Requirements": "Project hero imagery, gallery coverage, and detail shots for featured work",
            "SEO Focus": "Service keywords, portfolio discoverability, semantic case-study structure, and descriptive alt text",
            "Technical Constraints": "Strong mobile layout hierarchy and no decorative noise that obscures work samples",
        },
    },
    "ecommerce": {
        "description": "Ecommerce storefront defaults focused on trust, merchandising, and conversion.",
        "fields": {
            "Project Type": "Web Application",
            "Design Priority": "Merchandising clarity and purchase conversion",
            "Voice & Tone": "Clear, persuasive, and product-focused",
            "Typography": "Bold product-facing display typography with a clean commerce-friendly body font",
            "Icon System": "Font Awesome",
            "Experience Type": "Ecommerce",
            "Required Website Sections": "Header/Nav, Hero, Featured Collections, Product Highlights, Reviews, FAQ, Shipping/Returns, CTA, Footer",
            "Primary Calls to Action": "Shop Now, View Collection, Add to Cart",
            "Image Requirements": "Collection hero images, product closeups, and supporting merchandising visuals",
            "SEO Focus": "Transactional keywords, collection discoverability, structured product content, and strong metadata",
            "Technical Constraints": "Mobile-first commerce flows, clear pricing visibility, and performant product imagery",
        },
    },
    "content-site": {
        "description": "Editorial and content-marketing defaults with strong structure and discoverability.",
        "fields": {
            "Project Type": "Content / Marketing Site",
            "Design Priority": "Readable editorial hierarchy and search visibility",
            "Voice & Tone": "Authoritative, readable, and structured",
            "Typography": "Editorial display typography paired with a comfortable long-form reading font",
            "Icon System": "Font Awesome",
            "Experience Type": "Editorial",
            "Required Website Sections": "Header/Nav, Hero, Featured Content, Topic Sections, Newsletter CTA, About, FAQ, Footer",
            "Primary Calls to Action": "Read More, Subscribe, Explore Topics",
            "Image Requirements": "Hero artwork, article feature imagery, and section-supporting visuals",
            "SEO Focus": "Informational keywords, semantic content structure, internal linking, and metadata discipline",
            "Technical Constraints": "Readable typography scales, strong content hierarchy, and lightweight page performance",
        },
    },
}

def read_text_file(path, max_chars=40000):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(max_chars)

def is_new_project_brand_questionnaire(content):
    return NEW_PROJECT_BRAND_MARKER in content

def extract_brand_field(content, field_name):
    pattern = rf"(?m)^- \*\*{re.escape(field_name)}:\*\* (.*)$"
    match = re.search(pattern, content)
    return match.group(1).strip() if match else ""

def normalize_answer_key(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

def build_answer_field_aliases():
    aliases = {}
    direct_fields = ("Project Name",) + NEW_PROJECT_BRAND_FIELDS + NOTE_DRIVEN_INTAKE_FIELDS

    for field_name in direct_fields:
        aliases[normalize_answer_key(field_name)] = field_name

    for _, label, field_name in QUESTION_FIELD_SPECS:
        aliases[normalize_answer_key(label)] = field_name

    aliases.update(
        {
            "brand name": "Project Name",
            "working title": "Project Name",
            "mission": "Mission",
            "vision": "Vision",
            "voice tone": "Voice & Tone",
            "voice and tone": "Voice & Tone",
            "target audience": "Primary Audience",
            "goal monetization model": "Goal / Monetization Model",
            "closest competitor": "Reference Brand",
            "reference brand": "Reference Brand",
            "brand comparison": "Brand Comparison",
            "existing assets": "Existing Brand Assets",
            "non negotiables": "Content / Visual Non-Negotiables",
            "content visual non negotiables": "Content / Visual Non-Negotiables",
        }
    )
    return aliases

def update_brand_field(content, field_name, value, overwrite=False):
    pattern = rf"(?m)^- \*\*{re.escape(field_name)}:\*\* .*$"
    if not re.search(pattern, content):
        return content, False

    current_value = extract_brand_field(content, field_name)
    if current_value and not brand_field_is_unanswered(current_value) and not overwrite:
        return content, False

    updated_line = f"- **{field_name}:** {value}"
    return re.sub(pattern, updated_line, content, count=1), True

def extract_note_entry(content, label):
    pattern = rf"(?m)^- {re.escape(label)}: (.*)$"
    match = re.search(pattern, content)
    return match.group(1).strip() if match else ""

def upsert_note_entry(content, label, value):
    pattern = rf"(?m)^- {re.escape(label)}: .*$"
    note_line = f"- {label}: {value}"

    if re.search(pattern, content):
        return re.sub(pattern, note_line, content, count=1), True

    notes_header = "## Notes\n"
    if notes_header in content:
        return content.replace(notes_header, notes_header + note_line + "\n", 1), True

    return content.rstrip() + f"\n\n## Notes\n{note_line}\n", True

def brand_field_is_unanswered(value):
    normalized = value.strip().lower()
    return normalized in {"", "tbd", "unknown", "undecided", "unsure"}

def brand_field_is_not_applicable(value):
    normalized = value.strip().lower()
    return normalized in {"n/a", "na", "not applicable", "none"}

def normalize_brand_value(value, fallback):
    stripped = value.strip()
    if brand_field_is_unanswered(stripped):
        return fallback
    return stripped

def get_missing_new_project_brand_fields(content):
    missing_fields = []
    for field_name in NEW_PROJECT_BRAND_FIELDS:
        value = extract_brand_field(content, field_name)
        if brand_field_is_unanswered(value):
            missing_fields.append(field_name)
    return missing_fields

def collect_brand_context(content, project_root):
    field_names = ("Project Name",) + NEW_PROJECT_BRAND_FIELDS
    fields = {field_name: extract_brand_field(content, field_name) for field_name in field_names}
    for field_name in NOTE_DRIVEN_INTAKE_FIELDS:
        fields[field_name] = extract_note_entry(content, field_name)
    if brand_field_is_unanswered(fields.get("Project Name", "")):
        fields["Project Name"] = os.path.basename(os.path.abspath(project_root)) or "Project"
    return fields

def infer_build_surface(context):
    experience_value = context.get("Experience Type", "").strip()
    experience_type = experience_value.lower()
    project_type = context.get("Project Type", "").lower()
    required_sections = context.get("Required Website Sections", "").lower()

    if experience_type and not brand_field_is_not_applicable(experience_type):
        mapped_experiences = {
            "local service business": "local-service landing page",
            "marketing site": "marketing website",
            "portfolio": "portfolio site",
            "ecommerce": "ecommerce storefront",
            "editorial": "editorial website",
            "other": "website experience",
        }
        return mapped_experiences.get(experience_type, experience_value)
    if "content" in project_type or "marketing" in project_type:
        return "marketing website"
    if "hero" in required_sections or "footer" in required_sections or "testimonials" in required_sections:
        return "landing page"
    return "initial product experience"

def format_available_presets():
    return ", ".join(sorted(PROJECT_PRESETS))

def infer_project_type_from_primary_use_case(value):
    normalized = value.strip().lower()
    if "content" in normalized or "marketing" in normalized:
        return "Content / Marketing Site"
    if "saas" in normalized or "app" in normalized or "mobile" in normalized:
        return "Web Application"
    return value.strip()

def infer_logo_status_from_assets(value):
    normalized = value.strip().lower()
    if not normalized:
        return ""

    explicit_logo_flag = re.search(r"logo\s*\((y|n)\)", normalized)
    if explicit_logo_flag:
        return "Existing asset detected" if explicit_logo_flag.group(1) == "y" else "Not yet created"

    if re.search(r"logo\s*[:=-]?\s*(yes|y|existing|have|true)\b", normalized):
        return "Existing asset detected"
    if re.search(r"logo\s*[:=-]?\s*(no|n|none|false)\b", normalized):
        return "Not yet created"
    if any(token in normalized for token in ("logo", "palette", "typography", "existing site")):
        return "Existing assets provided"
    return ""

def read_answers_input(args):
    if args.answers_text:
        return args.answers_text
    if not args.answers_file:
        return ""
    if args.answers_file == "-":
        return sys.stdin.read()
    with open(args.answers_file, "r", encoding="utf-8") as f:
        return f.read()

def parse_structured_answers(text):
    if not text.strip():
        return {}

    aliases = build_answer_field_aliases()
    question_map = {number: field_name for number, _, field_name in QUESTION_FIELD_SPECS}
    question_labels = {number: label for number, label, _ in QUESTION_FIELD_SPECS}
    answers = {}
    current_field = None

    def commit_answer(field_name, value):
        if not field_name or not value:
            return
        answers[field_name] = value.strip()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            current_field = None
            continue

        markdown_match = re.match(r"^- \*\*(.+?)\:\*\*\s*(.*)$", line)
        if markdown_match:
            label = markdown_match.group(1).strip()
            value = markdown_match.group(2).strip()
            field_name = aliases.get(normalize_answer_key(label))
            if field_name:
                if value:
                    commit_answer(field_name, value)
                current_field = field_name
                continue

        numbered_match = re.match(r"^(\d{1,2})[\).\:-]\s*(.*)$", line)
        if numbered_match:
            question_number = int(numbered_match.group(1))
            remainder = numbered_match.group(2).strip()
            field_name = question_map.get(question_number)
            if not field_name:
                current_field = None
                continue

            label = question_labels[question_number]
            if normalize_answer_key(remainder).startswith(normalize_answer_key(label)):
                remainder = re.sub(r"^[^:]+:\s*", "", remainder, count=1).strip()

            if remainder:
                commit_answer(field_name, remainder)
            current_field = field_name
            continue

        key_value_match = re.match(r"^([^:]+):\s*(.*)$", line)
        if key_value_match:
            label = key_value_match.group(1).strip().lstrip("-").strip()
            value = key_value_match.group(2).strip()
            field_name = aliases.get(normalize_answer_key(label))
            if field_name:
                if value:
                    commit_answer(field_name, value)
                current_field = field_name
                continue

        if current_field:
            combined = f"{answers.get(current_field, '')} {line}".strip()
            commit_answer(current_field, combined)

    return answers

def apply_project_preset(content, preset_name):
    preset = PROJECT_PRESETS[preset_name]
    changed_fields = []

    for field_name, value in preset["fields"].items():
        content, changed = update_brand_field(content, field_name, value, overwrite=False)
        if changed:
            changed_fields.append(field_name)

    return content, changed_fields

def apply_answers_to_brand_content(content, answers):
    if not answers:
        return content, {"fields": [], "notes": []}

    direct_field_names = {"Project Name", *NEW_PROJECT_BRAND_FIELDS}
    note_fields = set(NOTE_DRIVEN_INTAKE_FIELDS)
    changed_fields = []
    changed_notes = []

    explicit_direct_updates = {}
    derived_updates = {}
    note_updates = {}

    for field_name, value in answers.items():
        if field_name in direct_field_names:
            explicit_direct_updates[field_name] = value
        elif field_name in note_fields:
            note_updates[field_name] = value

    primary_use_case = answers.get("Primary Use Case", "")
    if primary_use_case and brand_field_is_unanswered(extract_brand_field(content, "Project Type")):
        derived_updates["Project Type"] = infer_project_type_from_primary_use_case(primary_use_case)

    brand_comparison = answers.get("Brand Comparison", "")
    if brand_comparison and brand_field_is_unanswered(extract_brand_field(content, "Differentiation")):
        derived_updates["Differentiation"] = brand_comparison

    existing_assets = answers.get("Existing Brand Assets", "")
    if existing_assets and brand_field_is_unanswered(extract_brand_field(content, "Logo Status")):
        inferred_logo_status = infer_logo_status_from_assets(existing_assets)
        if inferred_logo_status:
            derived_updates["Logo Status"] = inferred_logo_status

    non_negotiables = answers.get("Content / Visual Non-Negotiables", "")
    if non_negotiables and brand_field_is_unanswered(extract_brand_field(content, "Technical Constraints")):
        derived_updates["Technical Constraints"] = non_negotiables

    for field_name, value in explicit_direct_updates.items():
        content, changed = update_brand_field(content, field_name, value, overwrite=True)
        if changed:
            changed_fields.append(field_name)

    for field_name, value in derived_updates.items():
        content, changed = update_brand_field(content, field_name, value, overwrite=False)
        if changed:
            changed_fields.append(field_name)

    for label, value in note_updates.items():
        content, changed = upsert_note_entry(content, label, value)
        if changed:
            changed_notes.append(label)

    return content, {"fields": changed_fields, "notes": changed_notes}

def render_generated_prompts(project_root):
    brand_path = os.path.join(project_root, ".arms/BRAND.md")
    brand_content = read_text_file(brand_path)
    if not brand_content.strip() or brand_file_requires_bootstrap(brand_content):
        return None

    context = collect_brand_context(brand_content, project_root)
    project_name = normalize_brand_value(context.get("Project Name", ""), "Project")
    mission = normalize_brand_value(context.get("Mission", ""), "Clarify the project's primary purpose.")
    vision = normalize_brand_value(context.get("Vision", ""), "Clarify the long-term direction.")
    personality = normalize_brand_value(context.get("Personality", ""), "Distinctive and cohesive")
    voice_tone = normalize_brand_value(context.get("Voice & Tone", ""), "Clear, confident, and audience-appropriate")
    primary_audience = normalize_brand_value(context.get("Primary Audience", ""), "Target audience not yet specified")
    core_values = normalize_brand_value(context.get("Core Values", ""), "Trust, clarity, and quality")
    differentiation = normalize_brand_value(context.get("Differentiation", ""), "Differentiate clearly from adjacent alternatives")
    color_palette = normalize_brand_value(context.get("Color Palette", ""), "Define from the approved brand direction")
    typography = normalize_brand_value(context.get("Typography", ""), "Choose typography that matches the approved brand")
    logo_status = normalize_brand_value(context.get("Logo Status", ""), "Pending / unspecified")
    visual_direction = normalize_brand_value(context.get("Visual Direction", ""), "Undecided")
    project_type = normalize_brand_value(context.get("Project Type", ""), "Project type not yet specified")
    design_priority = normalize_brand_value(context.get("Design Priority", ""), "Clear hierarchy and execution quality")
    tech_stack = normalize_brand_value(context.get("Preferred Tech Stack", ""), "Choose the most appropriate stack from the approved options")
    deployment_target = normalize_brand_value(context.get("Deployment Target", ""), "Deployment target not yet specified")
    data_layer = normalize_brand_value(context.get("Backend / Data Layer", ""), "Data layer not yet specified")
    auth_requirement = normalize_brand_value(context.get("Authentication Requirement", ""), "No explicit auth requirement yet")
    technical_constraints = normalize_brand_value(context.get("Technical Constraints", ""), "No hard constraints captured")
    primary_use_case = normalize_brand_value(context.get("Primary Use Case", ""), "Primary use case not yet captured")
    core_features = normalize_brand_value(context.get("Core Features", ""), "Core features not yet captured")
    monetization_model = normalize_brand_value(context.get("Goal / Monetization Model", ""), "Goal / monetization model not yet captured")
    reference_brand = normalize_brand_value(context.get("Reference Brand", ""), "No explicit reference brand provided")
    brand_comparison = normalize_brand_value(context.get("Brand Comparison", ""), "No explicit brand comparison provided")
    existing_brand_assets = normalize_brand_value(context.get("Existing Brand Assets", ""), "No explicit asset inventory provided")
    experience_type = normalize_brand_value(context.get("Experience Type", ""), "N/A")
    business_niche = normalize_brand_value(context.get("Industry / Business Niche", ""), "Industry not yet specified")
    service_area = normalize_brand_value(context.get("Service Area / Local SEO Target", ""), "No explicit service area captured")
    required_sections = normalize_brand_value(context.get("Required Website Sections", ""), "Use the most suitable structure for the project type")
    primary_ctas = normalize_brand_value(context.get("Primary Calls to Action", ""), "Define the primary conversion actions")
    image_requirements = normalize_brand_value(context.get("Image Requirements", ""), "Create the minimum viable supporting image set")
    seo_focus = normalize_brand_value(context.get("SEO Focus", ""), "Use semantic HTML, metadata, and descriptive copy")
    content_non_negotiables = normalize_brand_value(
        context.get("Content / Visual Non-Negotiables", ""),
        "No additional content or visual non-negotiables captured",
    )
    icon_system_value = context.get("Icon System", "")
    if brand_field_is_unanswered(icon_system_value):
        icon_system = "Font Awesome" if not brand_field_is_not_applicable(experience_type) else "Use the icon system that best fits the stack"
    else:
        icon_system = icon_system_value.strip()

    build_surface = infer_build_surface(context)
    local_seo_guidance = (
        f"Prioritize local SEO for {service_area}."
        if not brand_field_is_not_applicable(service_area) and service_area.lower() != "no explicit service area captured"
        else "Prioritize the strongest discoverability strategy for the stated audience."
    )

    source_context = textwrap.dedent(
        f"""\
        ## Source Context
        - **Project Name:** {project_name}
        - **Mission:** {mission}
        - **Vision:** {vision}
        - **Personality:** {personality}
        - **Voice & Tone:** {voice_tone}
        - **Primary Audience:** {primary_audience}
        - **Core Values:** {core_values}
        - **Differentiation:** {differentiation}
        - **Color Palette:** {color_palette}
        - **Typography:** {typography}
        - **Logo Status:** {logo_status}
        - **Visual Direction:** {visual_direction}
        - **Project Type:** {project_type}
        - **Design Priority:** {design_priority}
        - **Preferred Tech Stack:** {tech_stack}
        - **Deployment Target:** {deployment_target}
        - **Backend / Data Layer:** {data_layer}
        - **Authentication Requirement:** {auth_requirement}
        - **Technical Constraints:** {technical_constraints}
        - **Primary Use Case:** {primary_use_case}
        - **Core Features:** {core_features}
        - **Goal / Monetization Model:** {monetization_model}
        - **Reference Brand:** {reference_brand}
        - **Brand Comparison:** {brand_comparison}
        - **Existing Brand Assets:** {existing_brand_assets}
        - **Experience Type:** {experience_type}
        - **Industry / Business Niche:** {business_niche}
        - **Service Area / Local SEO Target:** {service_area}
        - **Required Website Sections:** {required_sections}
        - **Primary Calls to Action:** {primary_ctas}
        - **Icon System:** {icon_system}
        - **Image Requirements:** {image_requirements}
        - **SEO Focus:** {seo_focus}
        - **Content / Visual Non-Negotiables:** {content_non_negotiables}
        """
    ).strip()

    master_prompt = textwrap.dedent(
        f"""\
        Using the approved ARMS brand brief, create the first production-quality {build_surface.lower()} for {project_name}.

        Brand direction:
        - Mission: {mission}
        - Vision: {vision}
        - Personality: {personality}
        - Voice and tone: {voice_tone}
        - Core values: {core_values}
        - Differentiation: {differentiation}
        - Visual direction: {visual_direction}
        - Typography guidance: {typography}
        - Color guidance: {color_palette}

        Audience and market:
        - Primary audience: {primary_audience}
        - Primary use case: {primary_use_case}
        - Industry / niche: {business_niche}
        - Service area / SEO target: {service_area}
        - SEO focus: {seo_focus}
        - Core features: {core_features}
        - Goal / monetization model: {monetization_model}
        - Reference brand: {reference_brand}
        - Brand comparison: {brand_comparison}

        Product and build context:
        - Project type: {project_type}
        - Design priority: {design_priority}
        - Preferred tech stack: {tech_stack}
        - Deployment target: {deployment_target}
        - Backend / data layer: {data_layer}
        - Authentication requirement: {auth_requirement}
        - Technical constraints: {technical_constraints}

        Experience requirements:
        - Experience type: {experience_type}
        - Required sections: {required_sections}
        - Primary calls to action: {primary_ctas}
        - Icon system: {icon_system}
        - Image requirements: {image_requirements}
        - Logo status: {logo_status}
        - Existing brand assets: {existing_brand_assets}
        - Content / visual non-negotiables: {content_non_negotiables}

        Execution expectations:
        - Match the brand precisely; avoid generic defaults.
        - Make the experience responsive, production-quality, and believable for a real business or product.
        - {local_seo_guidance}
        - Keep the information architecture aligned with the stated audience and goals.
        - If this is a marketing or local-service site, keep contact information and trust signals highly visible.
        """
    ).strip()

    devops_prompt = textwrap.dedent(
        f"""\
        Scaffold the project foundation for {project_name} using {tech_stack}.

        Requirements:
        - Deployment target: {deployment_target}
        - Backend / data layer: {data_layer}
        - Authentication requirement: {auth_requirement}
        - Technical constraints: {technical_constraints}
        - Project type: {project_type}

        Deliver an initial project setup that matches the chosen stack, keeps the repository production-ready, and leaves clear extension points for frontend, content, and asset workflows.
        """
    ).strip()

    frontend_prompt = textwrap.dedent(
        f"""\
        Create the initial responsive {build_surface.lower()} for {project_name} using {tech_stack}.

        Design and UX direction:
        - Personality: {personality}
        - Voice and tone: {voice_tone}
        - Visual direction: {visual_direction}
        - Typography: {typography}
        - Color palette: {color_palette}
        - Design priority: {design_priority}
        - Differentiation: {differentiation}

        Content and structure:
        - Primary audience: {primary_audience}
        - Primary use case: {primary_use_case}
        - Industry / niche: {business_niche}
        - Required sections: {required_sections}
        - Primary CTAs: {primary_ctas}
        - Core features: {core_features}
        - Keep the content hierarchy aligned to: {mission}

        Implementation constraints:
        - Deployment target: {deployment_target}
        - Backend / data layer: {data_layer}
        - Authentication requirement: {auth_requirement}
        - Technical constraints: {technical_constraints}
        - Use {icon_system} for icons and do not use emoji unless explicitly requested later.
        - Design around this image coverage: {image_requirements}
        """
    ).strip()

    media_prompt = textwrap.dedent(
        f"""\
        Generate the initial visual asset set for {project_name}.

        Brand inputs:
        - Personality: {personality}
        - Voice and tone: {voice_tone}
        - Visual direction: {visual_direction}
        - Typography cues: {typography}
        - Color palette: {color_palette}
        - Differentiation: {differentiation}
        - Logo status: {logo_status}

        Asset requirements:
        - Experience type: {experience_type}
        - Industry / niche: {business_niche}
        - Required sections: {required_sections}
        - Image requirements: {image_requirements}
        - Existing brand assets: {existing_brand_assets}
        - Ensure the asset set supports the primary CTAs: {primary_ctas}

        Generate assets that feel tailored to the niche, support the intended layout, and can be dropped directly into the first frontend pass.
        """
    ).strip()

    seo_prompt = textwrap.dedent(
        f"""\
        Create the initial SEO and content brief for {project_name}.

        Search intent and audience:
        - Primary audience: {primary_audience}
        - Industry / niche: {business_niche}
        - Service area / local SEO target: {service_area}
        - Mission: {mission}
        - SEO focus: {seo_focus}

        Content requirements:
        - Required sections: {required_sections}
        - Primary CTAs: {primary_ctas}
        - Voice and tone: {voice_tone}
        - Core values: {core_values}
        - Differentiation: {differentiation}
        - Primary use case: {primary_use_case}
        - Core features: {core_features}
        - Goal / monetization model: {monetization_model}

        SEO expectations:
        - Recommend title and meta description direction.
        - Preserve semantic heading structure.
        - Ensure visible conversion paths and contact information where relevant.
        - Provide structured, crawlable copy and descriptive image alt-text guidance.
        - {local_seo_guidance}
        """
    ).strip()

    return (
        GENERATED_PROMPTS_HEADER.strip()
        + "\n\n"
        + source_context
        + "\n\n## Master Build Prompt\n```text\n"
        + master_prompt
        + "\n```\n\n## DevOps Scaffold Prompt\n```text\n"
        + devops_prompt
        + "\n```\n\n## Frontend Prompt\n```text\n"
        + frontend_prompt
        + "\n```\n\n## Media Prompt\n```text\n"
        + media_prompt
        + "\n```\n\n## SEO / Content Prompt\n```text\n"
        + seo_prompt
        + "\n```\n"
    )

def sync_generated_prompts(project_root):
    prompts_path = os.path.join(project_root, ".arms/GENERATED_PROMPTS.md")
    prompts_content = render_generated_prompts(project_root)

    if prompts_content is None:
        if os.path.exists(prompts_path):
            os.remove(prompts_path)
            print("🧹 Removed stale .arms/GENERATED_PROMPTS.md because the brand brief is incomplete.")
        return False

    with open(prompts_path, "w", encoding="utf-8") as f:
        f.write(prompts_content)
    print("🧠 Generated .arms/GENERATED_PROMPTS.md from the approved brand and stack context.")
    return True

def brand_file_requires_bootstrap(content):
    if not content.strip():
        return True
    if any(token in content for token in PLACEHOLDER_BRAND_TOKENS):
        return True
    if is_new_project_brand_questionnaire(content):
        return bool(get_missing_new_project_brand_fields(content))
    return False

def extract_first_meaningful_paragraph(text):
    lines = text.splitlines()
    paragraph = []
    in_code_block = False

    for raw_line in lines:
        line = raw_line.strip()

        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        if not line:
            if paragraph:
                break
            continue

        if (
            line.startswith("#")
            or line.startswith("|")
            or line.startswith("- ")
            or line.startswith("* ")
            or line.startswith("> ")
        ):
            if paragraph:
                break
            continue

        paragraph.append(line)

    return " ".join(paragraph).strip()

def detect_existing_project(project_root):
    substantive_markers = [marker for marker in PROJECT_MARKER_FILES if marker not in {"README.md", "README.mdx"}]
    for marker in substantive_markers:
        if os.path.exists(os.path.join(project_root, marker)):
            return True

    for marker_dir in PROJECT_MARKER_DIRS:
        path = os.path.join(project_root, marker_dir)
        if os.path.isdir(path):
            try:
                with os.scandir(path) as entries:
                    if next(entries, None) is not None:
                        return True
            except OSError:
                continue

    meaningful_entries = [
        name
        for name in os.listdir(project_root)
        if name not in IGNORED_PROJECT_ENTRIES and not name.startswith(".")
    ]
    source_like_entries = [
        name for name in meaningful_entries
        if os.path.splitext(name)[1].lower() in SOURCE_FILE_EXTENSIONS
    ]
    if source_like_entries:
        return True

    substantive_entries = [name for name in meaningful_entries if name not in BOOTSTRAP_ONLY_FILES]
    return len(substantive_entries) >= 2

def detect_logo_status(project_root):
    candidate_dirs = (
        project_root,
        os.path.join(project_root, "public"),
        os.path.join(project_root, "assets"),
        os.path.join(project_root, "static"),
        os.path.join(project_root, "src", "assets"),
    )

    for directory in candidate_dirs:
        if not os.path.isdir(directory):
            continue
        for root, _, files in os.walk(directory):
            for filename in files:
                lower = filename.lower()
                if lower.endswith((".svg", ".png", ".jpg", ".jpeg", ".webp", ".ico")) and (
                    "logo" in lower or "brand" in lower or "favicon" in lower
                ):
                    return "Existing asset detected"
    return "Pending / no explicit logo asset found"

def parse_pyproject_metadata(content):
    name_match = re.search(r'(?m)^name\s*=\s*["\']([^"\']+)["\']', content)
    description_match = re.search(r'(?m)^description\s*=\s*["\']([^"\']+)["\']', content)
    scripts_match = re.search(r'(?m)^\[project\.scripts\]', content)
    return {
        "name": name_match.group(1).strip() if name_match else "",
        "description": description_match.group(1).strip() if description_match else "",
        "has_scripts": bool(scripts_match),
    }

def classify_project_type(description_blob, frameworks, has_project_scripts):
    blob = description_blob.lower()
    framework_set = {framework.lower() for framework in frameworks}

    if has_project_scripts or any(
        keyword in blob for keyword in ("cli", "engine", "tool", "tooling", "framework", "sdk", "library", "orchestration")
    ):
        return "Developer Tooling"
    if "next.js" in framework_set or "react" in framework_set or "vue" in framework_set or "svelte" in framework_set or "astro" in framework_set:
        if any(keyword in blob for keyword in ("marketing", "landing page", "brand site", "content", "blog", "seo")):
            return "Content / Marketing Site"
        return "Web Application"
    if any(framework in framework_set for framework in ("fastapi", "flask", "django", "express", "nest")):
        return "Backend Service"
    return "Software Project"

def infer_personality(project_type):
    if project_type == "Developer Tooling":
        return "Technical, precise, efficient"
    if project_type == "Content / Marketing Site":
        return "Clear, confident, polished"
    if project_type == "Backend Service":
        return "Reliable, secure, deliberate"
    if project_type == "Web Application":
        return "Clear, modern, trustworthy"
    return "Focused, practical, adaptable"

def infer_voice_tone(project_type):
    if project_type == "Developer Tooling":
        return "Direct, technical, low-fluff communication for builders."
    if project_type == "Content / Marketing Site":
        return "Concise, persuasive, and benefits-first without sounding generic."
    if project_type == "Backend Service":
        return "Professional, calm, and confidence-building with clear technical detail."
    if project_type == "Web Application":
        return "Friendly and clear, with emphasis on usability and trust."
    return "Plainspoken and pragmatic."

def infer_primary_audience(project_type):
    if project_type == "Developer Tooling":
        return "Developers, technical operators, and engineering teams"
    if project_type == "Content / Marketing Site":
        return "Prospective customers, buyers, and evaluators"
    if project_type == "Backend Service":
        return "Internal engineering teams and API consumers"
    if project_type == "Web Application":
        return "End users interacting with the application on web or mobile"
    return "Project stakeholders and end users"

def infer_core_values(project_type):
    if project_type == "Developer Tooling":
        return "Automation, consistency, maintainability"
    if project_type == "Content / Marketing Site":
        return "Clarity, credibility, conversion"
    if project_type == "Backend Service":
        return "Reliability, security, scalability"
    if project_type == "Web Application":
        return "Usability, clarity, performance"
    return "Pragmatism, quality, adaptability"

def infer_design_priority(project_type):
    if project_type == "Developer Tooling":
        return "Clarity for technical workflows"
    if project_type == "Content / Marketing Site":
        return "Conversion-focused communication"
    if project_type == "Backend Service":
        return "Operational clarity and trust"
    if project_type == "Web Application":
        return "App-like usability"
    return "Clear information hierarchy"

def infer_brand_context_from_project(project_root):
    evidence = []
    frameworks = []
    package_name = ""
    description = ""
    keywords = []
    has_project_scripts = False

    package_json_path = os.path.join(project_root, "package.json")
    if os.path.exists(package_json_path):
        evidence.append("package.json")
        try:
            with open(package_json_path, "r", encoding="utf-8") as f:
                package_data = json.load(f)
            package_name = str(package_data.get("name", "")).strip()
            description = str(package_data.get("description", "")).strip()
            keywords = [str(keyword).strip() for keyword in package_data.get("keywords", []) if str(keyword).strip()]
            deps = set((package_data.get("dependencies") or {}).keys()) | set((package_data.get("devDependencies") or {}).keys())
            if "next" in deps:
                frameworks.append("Next.js")
            if "react" in deps:
                frameworks.append("React")
            if "vue" in deps:
                frameworks.append("Vue")
            if "@angular/core" in deps:
                frameworks.append("Angular")
            if "svelte" in deps or "@sveltejs/kit" in deps:
                frameworks.append("Svelte")
            if "astro" in deps:
                frameworks.append("Astro")
            if "express" in deps:
                frameworks.append("Express")
            if "@nestjs/core" in deps:
                frameworks.append("Nest")
        except (json.JSONDecodeError, OSError):
            evidence.append("package.json (unparsed)")

    pyproject_path = os.path.join(project_root, "pyproject.toml")
    pyproject_content = read_text_file(pyproject_path)
    if pyproject_content:
        evidence.append("pyproject.toml")
        pyproject_metadata = parse_pyproject_metadata(pyproject_content)
        package_name = package_name or pyproject_metadata["name"]
        description = description or pyproject_metadata["description"]
        has_project_scripts = has_project_scripts or pyproject_metadata["has_scripts"]
        lowered = pyproject_content.lower()
        if "fastapi" in lowered:
            frameworks.append("FastAPI")
        if "flask" in lowered:
            frameworks.append("Flask")
        if "django" in lowered:
            frameworks.append("Django")
        if "typer" in lowered or "click" in lowered:
            frameworks.append("Python CLI")

    cargo_toml_path = os.path.join(project_root, "Cargo.toml")
    cargo_content = read_text_file(cargo_toml_path)
    if cargo_content:
        evidence.append("Cargo.toml")
        cargo_name_match = re.search(r'(?m)^name\s*=\s*"([^"]+)"', cargo_content)
        cargo_description_match = re.search(r'(?m)^description\s*=\s*"([^"]+)"', cargo_content)
        if cargo_name_match and not package_name:
            package_name = cargo_name_match.group(1).strip()
        if cargo_description_match and not description:
            description = cargo_description_match.group(1).strip()
        frameworks.append("Rust")

    go_mod_path = os.path.join(project_root, "go.mod")
    go_mod_content = read_text_file(go_mod_path)
    if go_mod_content:
        evidence.append("go.mod")
        module_match = re.search(r'(?m)^module\s+(.+)$', go_mod_content)
        if module_match and not package_name:
            package_name = module_match.group(1).strip().split("/")[-1]
        frameworks.append("Go")

    readme_path = os.path.join(project_root, "README.md")
    readme_content = read_text_file(readme_path)
    readme_summary = ""
    if readme_content:
        evidence.append("README.md")
        readme_summary = extract_first_meaningful_paragraph(readme_content)

    if os.path.isdir(os.path.join(project_root, "src")):
        evidence.append("src/")
    if os.path.isdir(os.path.join(project_root, "app")):
        evidence.append("app/")
    if os.path.isdir(os.path.join(project_root, "pages")):
        evidence.append("pages/")

    frameworks = list(dict.fromkeys(frameworks))
    directory_name = os.path.basename(os.path.abspath(project_root))
    project_name = package_name or directory_name
    description_blob = " ".join(filter(None, [description, readme_summary, " ".join(keywords)]))
    project_type = classify_project_type(description_blob, frameworks, has_project_scripts)

    if description:
        mission = description.rstrip(".") + "."
    elif readme_summary:
        mission = readme_summary.rstrip(".") + "."
    else:
        mission = f"{project_name} is an existing {project_type.lower()} repository."

    if readme_summary and readme_summary.lower() != mission.lower():
        differentiation = readme_summary.rstrip(".") + "."
    elif description:
        differentiation = description.rstrip(".") + "."
    else:
        differentiation = f"Repository signals suggest a {project_type.lower()} focused on practical delivery."

    stack_summary = ", ".join(frameworks) if frameworks else "No dominant framework detected"

    return {
        "project_name": project_name,
        "mission": mission,
        "vision": "TBD - confirm the long-term product direction with the project owner.",
        "personality": infer_personality(project_type),
        "voice_tone": infer_voice_tone(project_type),
        "primary_audience": infer_primary_audience(project_type),
        "core_values": infer_core_values(project_type),
        "differentiation": differentiation,
        "color_palette": "TBD - no explicit palette found in repository files",
        "typography": "TBD - no explicit font system found in repository files",
        "logo_status": detect_logo_status(project_root),
        "visual_direction": "Undecided - confirm preferred light/dark direction",
        "project_type": project_type,
        "design_priority": infer_design_priority(project_type),
        "notes": [
            "Auto-generated from existing repository signals. Review and correct inferred fields.",
            f"Evidence reviewed: {', '.join(dict.fromkeys(evidence)) or 'directory structure only'}",
            f"Detected stack: {stack_summary}",
        ],
    }

def render_inferred_brand_context(project_root):
    context = infer_brand_context_from_project(project_root)
    notes = "\n".join(f"- {note}" for note in context["notes"])
    return f"""# Brand Context
> Managed by ARMS Engine. Auto-generated from an existing project repository.
> Review inferred fields before relying on this as final brand truth.

---

## Identity
- **Project Name:** {context["project_name"]}
- **Mission:** {context["mission"]}
- **Vision:** {context["vision"]}
- **Personality:** {context["personality"]}
- **Voice & Tone:** {context["voice_tone"]}

## Positioning
- **Primary Audience:** {context["primary_audience"]}
- **Core Values:** {context["core_values"]}
- **Differentiation:** {context["differentiation"]}

## Visual Identity
- **Color Palette:** {context["color_palette"]}
- **Typography:** {context["typography"]}
- **Logo Status:** {context["logo_status"]}
- **Visual Direction:** {context["visual_direction"]}

## Use Case Implications
- **Project Type:** {context["project_type"]}
- **Design Priority:** {context["design_priority"]}

## Notes
{notes}
"""

def render_new_project_brand_questionnaire(project_root):
    project_name = os.path.basename(os.path.abspath(project_root)) or "TBD"
    return f"""# Brand Context
> Managed by ARMS Engine. Referenced by: Frontend, SEO, and Media agents.
> New project detected. Fill in the questions below before design-oriented work begins.

---

## Identity
- **Project Name:** {project_name}
- **Mission:** TBD
- **Vision:** TBD
- **Personality:** TBD
- **Voice & Tone:** TBD

## Positioning
- **Primary Audience:** TBD
- **Core Values:** TBD
- **Differentiation:** TBD

## Visual Identity
- **Color Palette:** TBD
- **Typography:** TBD
- **Logo Status:** TBD
- **Visual Direction:** TBD

## Use Case Implications
- **Project Type:** TBD
- **Design Priority:** TBD

## Initial Technical Direction
- **Preferred Tech Stack:** TBD
- **Deployment Target:** TBD
- **Backend / Data Layer:** TBD
- **Authentication Requirement:** TBD
- **Technical Constraints:** TBD

## Initial Website / Landing Page Brief
- **Experience Type:** TBD
- **Industry / Business Niche:** TBD
- **Service Area / Local SEO Target:** TBD
- **Required Website Sections:** TBD
- **Primary Calls to Action:** TBD
- **Icon System:** TBD
- **Image Requirements:** TBD
- **SEO Focus:** TBD

## Notes
- Answer these before approving design or marketing work:
- What is the exact project name or working title?
- What problem does the project solve, and for whom?
- What is the long-term vision?
- Pick up to 3 brand personality words.
- What should the voice sound like?
- Who is the primary audience?
- What core values should the brand signal?
- What makes it meaningfully different from alternatives?
- Do you already have a logo, color palette, typography, or an existing site?
- Should the visual direction default to light, dark, system, or something else?
- What stack, deployment target, auth approach, and hard technical constraints should ARMS plan around?
- If this is a website or landing page, what type of experience is it and what industry does it serve?
- Which sections, CTAs, icons, images, and SEO priorities are mandatory?
- If a website brief item does not apply, explicitly write N/A so ARMS can treat the questionnaire as complete.
"""

def render_new_project_brand_prompt(missing_fields=None):
    brand_questions = "\n".join(NEW_PROJECT_BRAND_QUESTIONS)
    tech_stack_questions = "\n".join(NEW_PROJECT_TECH_STACK_QUESTIONS)
    website_brief_questions = "\n".join(NEW_PROJECT_WEBSITE_BRIEF_QUESTIONS)
    preset_block = (
        "Fast paths:\n"
        f"- Apply a preset: `arms init --preset <name>` (available: {format_available_presets()})\n"
        "- Apply structured answers: `arms init --answers-file path/to/answers.md`\n"
        "- Or pass a short block inline: `arms init --answers-text \"Mission: ...\"`\n"
        "- Supported answer formats: `Field: value`, `- **Field:** value`, or numbered questionnaire responses.\n\n"
    )
    missing_block = ""
    if missing_fields:
        missing_block = (
            "Still incomplete in `.arms/BRAND.md`:\n"
            + "\n".join(f"- {field}" for field in missing_fields)
            + "\n\n"
        )
    return (
        "📝 Brand Context is required for a new / empty project.\n"
        "Fill the unanswered fields in `.arms/BRAND.md` or answer these in one block, then re-run `arms init` to resume:\n\n"
        f"{preset_block}"
        f"{missing_block}"
        f"{brand_questions}\n\n"
        "After Brand Context, confirm the initial tech stack:\n\n"
        f"{tech_stack_questions}\n\n"
        "If this project includes a website or landing page, also answer this brief. Use `N/A` where it does not apply:\n\n"
        f"{website_brief_questions}\n\n"
        "The Brand Context and technical-direction questionnaire is stored in `.arms/BRAND.md`."
    )

def initialize_brand_context(project_root):
    brand_path = os.path.join(project_root, ".arms/BRAND.md")

    existing_content = read_text_file(brand_path)
    if existing_content:
        if is_new_project_brand_questionnaire(existing_content):
            missing_fields = get_missing_new_project_brand_fields(existing_content)
            if missing_fields:
                print("📝 New-project BRAND.md is still incomplete. Reusing saved questionnaire.")
                return {
                    "status": "questions_required",
                    "prompt": render_new_project_brand_prompt(missing_fields),
                }
            print("✅ New-project BRAND.md is complete. Continuing initialization from saved answers.")
            return {"status": "existing"}
        if not brand_file_requires_bootstrap(existing_content):
            return {"status": "existing"}

    if detect_existing_project(project_root):
        print("🎨 Generating BRAND.md from existing project context...")
        with open(brand_path, "w", encoding="utf-8") as f:
            f.write(render_inferred_brand_context(project_root))
        print("📢 BRAND.md generated from repository signals. Review inferred fields and refine where needed.")
        return {"status": "inferred"}

    print("🎨 Initializing new-project BRAND.md questionnaire...")
    with open(brand_path, "w", encoding="utf-8") as f:
        f.write(render_new_project_brand_questionnaire(project_root))
    print("📢 BRAND.md created for a new project. User answers are required before high-fidelity brand work begins.")
    return {
        "status": "questions_required",
        "prompt": render_new_project_brand_prompt(),
    }

def apply_brand_inputs(project_root, preset_name="", answers_text=""):
    brand_path = os.path.join(project_root, ".arms/BRAND.md")
    content = read_text_file(brand_path)
    if not content:
        return False

    updated_content = content
    changed = False

    if preset_name:
        updated_content, changed_fields = apply_project_preset(updated_content, preset_name)
        if changed_fields:
            changed = True
            print(
                f"🧩 Applied preset '{preset_name}' to .arms/BRAND.md "
                f"({', '.join(changed_fields)})."
            )
        else:
            print(f"ℹ️  Preset '{preset_name}' had no unanswered fields left to fill.")

    if answers_text.strip():
        answers = parse_structured_answers(answers_text)
        if answers:
            updated_content, change_summary = apply_answers_to_brand_content(updated_content, answers)
            changed_fields = change_summary["fields"]
            changed_notes = change_summary["notes"]
            if changed_fields or changed_notes:
                changed = True
                summary_bits = []
                if changed_fields:
                    summary_bits.append(f"fields: {', '.join(changed_fields)}")
                if changed_notes:
                    summary_bits.append(f"notes: {', '.join(changed_notes)}")
                print(f"🧾 Applied structured answers to .arms/BRAND.md ({'; '.join(summary_bits)}).")
            else:
                print("ℹ️  Structured answers were recognized, but they did not change .arms/BRAND.md.")
        else:
            print("⚠️  No recognizable structured answers found. Use `Field: value` or numbered responses.")

    if changed and updated_content != content:
        with open(brand_path, "w", encoding="utf-8") as f:
            f.write(updated_content)

    return changed

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

def capture_file_signature(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return None

def wait_for_brand_change(project_root, previous_signature):
    brand_path = os.path.join(project_root, ".arms/BRAND.md")
    print()
    print(f"👀 Watch mode active. Waiting for changes to {brand_path} ...")
    print("   Press Ctrl+C to stop watching.")
    while True:
        time.sleep(WATCH_POLL_INTERVAL_SECONDS)
        current_signature = capture_file_signature(brand_path)
        if current_signature != previous_signature:
            print("🔄 Detected BRAND.md change. Re-running init...")
            return

def extract_session_engine_version(session_content):
    match = re.search(r'- Engine Version: (.*)', session_content)
    return match.group(1).strip() if match else ""

def version_sort_key(value):
    cleaned = value.strip().lstrip("v")
    match = re.match(r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?(.*)$', cleaned)
    if not match:
        return None

    major = int(match.group(1) or 0)
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    suffix = (match.group(4) or "").strip().lower()

    stage_rank = 0
    stage_number = 0
    if suffix:
        stage_match = re.search(r'(dev|a|alpha|b|beta|rc)[\.-]?(\d+)?', suffix)
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
    root = os.path.abspath(arms_root)
    engine_repo_root = os.path.dirname(root)
    version_text = (__version__ or "").lower()
    return (
        "dev" in version_text
        or os.path.isdir(os.path.join(engine_repo_root, ".git"))
    )

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
            f"development engine reports {__version__}. Continuing because a development checkout is in use."
        )
        return

    print("❌ ERROR: This project was last synced by a newer ARMS Engine.")
    print(f"   Project engine version: {existing_engine_version}")
    print(f"   Current engine version: {__version__}")
    print("   To avoid downgrading project state, update the engine and rerun `arms init`.")
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
    sys.exit(1)

def update_session(project_root, arms_root, skills_list, agents_list, yolo=False):
    print("📄 Updating session log...")
    session_path = os.path.join(project_root, ".arms/SESSION.md")
    
    existing_content = ""
    existing_root = None
    existing_name = None
    if os.path.exists(session_path):
        with open(session_path, 'r') as f:
            existing_content = f.read()
            # Detect existing project context
            root_match = re.search(r'- Project Root: (.*)', existing_content)
            if root_match:
                existing_root = root_match.group(1).strip()
            
            name_match = re.search(r'- Project Name: (.*)', existing_content)
            if name_match:
                existing_name = name_match.group(1).strip()

    # Get current project name from BRAND.md if available
    current_name = "Unknown"
    brand_path = os.path.join(project_root, ".arms/BRAND.md")
    if os.path.exists(brand_path):
        with open(brand_path, 'r') as f:
            brand_content = f.read()
            name_match = re.search(r'- \*\*Project Name:\*\* (.*)', brand_content)
            if name_match:
                current_name = name_match.group(1).strip().strip('[]')

    # Validate Context
    if existing_root and os.path.abspath(existing_root) != os.path.abspath(project_root):
        print(f"⚠️  Context Mismatch: Session file points to '{existing_root}'")
        print(f"   Current root: {project_root}")
        if yolo:
            print("🤖 [YOLO] Auto-accepting: Overwriting session with current project context.")
        else:
            confirm = input("Overwrite session with current context? (y/n): ")
            if confirm.lower() != 'y':
                print("Aborting to preserve session state.")
                return

    resolved_agents, skill_catalog, _ = resolve_agents_with_skills(arms_root, announce=False)
    agent_skill_bindings = build_agent_skill_bindings(resolved_agents)
    skill_catalog_by_name = {
        skill["name"]: skill
        for skill in skill_catalog
    }

    # Extract tasks section to preserve it
    tasks_match = re.search(r'(## Active Tasks.*)', existing_content, re.DOTALL)
    if tasks_match:
        tasks_content_raw = tasks_match.group(1)
        # De-duplicate sections (Active Tasks, Completed Tasks, Blockers)
        header_pattern = r'## (Active Tasks|Completed Tasks|Blockers)'
        parts = re.split(header_pattern, tasks_content_raw)
        seen_headers = set()
        new_tasks_content = []
        for i in range(1, len(parts), 2):
            header = parts[i]
            content = parts[i+1].strip()
            if header not in seen_headers:
                if content:
                    if header == "Active Tasks":
                        content = normalize_active_tasks_table(
                            content,
                            agent_skill_bindings=agent_skill_bindings,
                            skill_catalog_by_name=skill_catalog_by_name,
                        )
                    new_tasks_content.append(f"## {header}\n{content}")
                else:
                    # Provide default content for empty sections
                    if header == "Active Tasks":
                        new_tasks_content.append(f"## {header}\n| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n|---|------|----------------|--------------|--------------|--------|")
                    elif header == "Completed Tasks":
                        new_tasks_content.append(f"## {header}\n- None")
                    elif header == "Blockers":
                        new_tasks_content.append(f"## {header}\nNone")
                seen_headers.add(header)
        
        # Ensure all required sections are present even if not in original
        for req in ["Active Tasks", "Completed Tasks", "Blockers"]:
            if req not in seen_headers:
                if req == "Active Tasks":
                    new_tasks_content.append(f"## {req}\n| # | Task | Assigned Agent | Active Skill | Dependencies | Status |\n|---|------|----------------|--------------|--------------|--------|")
                elif req == "Completed Tasks":
                    new_tasks_content.append(f"## {req}\n- None")
                elif req == "Blockers":
                    new_tasks_content.append(f"## {req}\nNone")

        tasks_content = "\n\n".join(new_tasks_content)
    else:
        # Default fresh task table
        tasks_content = """## Active Tasks
| # | Task | Assigned Agent | Active Skill | Dependencies | Status |
|---|------|----------------|--------------|--------------|--------|

## Completed Tasks
- None

## Blockers
None"""

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Environment detection
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

    with open(session_path, 'w') as f:
        f.write(content)


def run_init_once(project_root, arms_root, full_command, is_yolo, preset_name="", answers_text="", allow_engine_downgrade=False, show_banner=True):
    if show_banner:
        print(f"🚀 Initializing ARMS Engine...")
        print(f"📂 Project: {project_root}")
        print(f"🛡️  Engine:  {arms_root}")
        if is_yolo:
            print("⚡ Mode:    YOLO (Full Automation)")

    setup_folders(project_root)
    migrate_legacy_state(project_root)
    enforce_engine_version_guard(
        project_root,
        arms_root,
        allow_engine_downgrade=allow_engine_downgrade,
    )
    bootstrap_runtime_files(project_root)
    clean_legacy_gemini_skill_mirror(project_root)
    sync_agents(arms_root, project_root)
    sync_agents_copilot(arms_root, project_root)

    sync_skills_copilot(arms_root, project_root)
    create_skills_registry(arms_root, project_root)
    sync_workflow(arms_root, project_root)
    brand_context_state = initialize_brand_context(project_root)
    if preset_name or answers_text:
        inputs_applied = apply_brand_inputs(
            project_root,
            preset_name=preset_name,
            answers_text=answers_text,
        )
        if inputs_applied:
            brand_context_state = initialize_brand_context(project_root)
    generated_prompts_ready = False
    if brand_context_state and brand_context_state.get("status") == "questions_required":
        sync_generated_prompts(project_root)
    else:
        generated_prompts_ready = sync_generated_prompts(project_root)
    
    skills_list = discover_skills(arms_root)
    agents_list = discover_agents_and_skills(arms_root)
    update_session(project_root, arms_root, skills_list, agents_list, yolo=is_yolo)
    
    # Sync GEMINI.md
    gemini_src = os.path.join(arms_root, "GEMINI.md")
    gemini_dest = os.path.join(project_root, ".gemini/GEMINI.md")
    if os.path.exists(gemini_src):
        shutil.copy2(gemini_src, gemini_dest)
        print("📄 Core Directives (GEMINI.md) synced.")

    # Sync AGENTS.md for Copilot CLI
    sync_copilot_instructions(arms_root, project_root)

    if "compress" in full_command.lower():
        print("🗜️  Optimization mode triggered. (Caveman skill stub activated)")
        # In the future, this would invoke the actual caveman-compressor logic
        # For now, we just acknowledge the command to avoid the discrepancy.

    brand_signature = capture_file_signature(os.path.join(project_root, ".arms/BRAND.md"))
    if brand_context_state and brand_context_state.get("status") == "questions_required":
        print()
        print(brand_context_state["prompt"])
        print("\n✅ ARMS Engine sequence complete. Awaiting Brand Context answers. → HALT")
        return {
            "status": "questions_required",
            "brand_signature": brand_signature,
        }
    elif is_yolo:
        if generated_prompts_ready:
            print("🧠 Agent-ready prompts refreshed at .arms/GENERATED_PROMPTS.md")
        print("\n✅ ARMS Engine ready. Fleet mode activated.")
    else:
        if generated_prompts_ready:
            print("🧠 Agent-ready prompts refreshed at .arms/GENERATED_PROMPTS.md")
        print("\n✅ ARMS Engine sequence complete. → HALT")
    return {
        "status": "complete",
        "brand_signature": brand_signature,
    }

def main():
    parser = argparse.ArgumentParser(description="ARMS Engine Activator")
    parser.add_argument("command", nargs="*", default=["init"], help="Command to run (e.g., init, init yolo, start)")
    parser.add_argument("--root", help="Override arms root path")
    parser.add_argument(
        "--preset",
        help=f"Apply a new-project preset before resuming init (available: {format_available_presets()})",
    )
    parser.add_argument(
        "--answers-file",
        help="Apply structured intake answers from a file. Use '-' to read from stdin.",
    )
    parser.add_argument(
        "--answers-text",
        help="Apply structured intake answers inline. Supports 'Field: value' and numbered answers.",
    )
    parser.add_argument(
        "--allow-engine-downgrade",
        action="store_true",
        help="Allow init to continue even if the project was last synced by a newer engine version.",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch .arms/BRAND.md and auto-rerun init while the project is waiting on brand context.",
    )
    parser.add_argument("--version", action="version", version=f"ARMS Engine {__version__}")
    args = parser.parse_args()

    # Normalize command
    full_command = " ".join(args.command)
    is_yolo = "yolo" in full_command.lower()
    
    project_root = get_project_root()
    
    # Safety Check: Prevent initializing in home directory
    home_dir = os.path.expanduser("~")
    if os.path.abspath(project_root) == home_dir:
        print("❌ ERROR: Cannot initialize ARMS in the home directory.")
        print("   Please navigate to a specific project folder first.")
        sys.exit(1)

    arms_root = args.root or get_arms_root()
    if args.preset and args.preset not in PROJECT_PRESETS:
        print(f"❌ ERROR: Unknown preset '{args.preset}'.")
        print(f"   Available presets: {format_available_presets()}")
        sys.exit(1)
    try:
        answers_text = read_answers_input(args)
    except OSError as exc:
        print(f"❌ ERROR: Unable to read answers input: {exc}")
        sys.exit(1)

    pending_preset = (args.preset or "").strip()
    pending_answers_text = answers_text
    show_banner = True

    while True:
        result = run_init_once(
            project_root,
            arms_root,
            full_command,
            is_yolo,
            preset_name=pending_preset,
            answers_text=pending_answers_text,
            allow_engine_downgrade=args.allow_engine_downgrade,
            show_banner=show_banner,
        )
        if not args.watch or result["status"] != "questions_required":
            break
        pending_preset = ""
        pending_answers_text = ""
        show_banner = False
        try:
            wait_for_brand_change(project_root, result["brand_signature"])
        except KeyboardInterrupt:
            print("\n⏹️  Watch mode stopped.")
            sys.exit(130)

if __name__ == "__main__":
    main()
