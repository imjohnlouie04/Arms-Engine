import json
import os
import re
import shutil

try:
    import yaml
except ImportError as import_error:
    yaml = None
    YAML_IMPORT_ERROR = import_error
else:
    YAML_IMPORT_ERROR = None


REFERENCE_ONLY_SKILL_DIRS = {
    "ui-ux-pro-max": ("data",),
}

PROJECT_INSTRUCTION_SHARED_SECTION = """### ARMS Orchestration & Intake
- **Workflow:** This project uses the ARMS (Architectural Runtime Management System). Follow the protocols in `.arms/RULES.md`.
- **Durable Tasks:** Every net-new issue, bug report, or feature request arriving through chat must be logged to `.arms/SESSION.md` using `arms task log` or `arms task update` before substantive execution begins. Use the standard task-table schema for all handoffs.
- **Routing Syntax:** When routing must be explicit, use `--assigned-agent` / `--active-skill` on task commands. `--agent` / `--skill` are accepted aliases.
- **Agent Handoff:** Updating `.arms/SESSION.md` does not itself switch Copilot into the specialist. After the row is assigned, invoke `/agent <assigned-agent>` for the implementation turn.
- **Verification:** No task is "Done" until validated by `arms-qa-agent` and pre-flight checks (lint, build, unit tests) pass.
"""

LEGACY_GEMINI_BRIDGE_TEMPLATE = """# Gemini Instructions

> Managed bridge created by ARMS so Gemini CLI normal chat follows the shared task-intake protocol.
> If `./GEMINI.md` exists, read it as additional project context and preserve it as project-owned instructions.

{shared_section}

---
"""

ROOT_GEMINI_TEMPLATE = """# Gemini Instructions

> Project-owned Gemini instructions scaffolded by ARMS. Customize this file with repository-specific guidance as the project evolves.

{shared_section}

---
"""

COPILOT_INSTRUCTIONS_TEMPLATE = """# Copilot Instructions

> Project-owned Copilot instructions scaffolded by ARMS. Customize this file with repository-specific guidance as the project evolves.

{shared_section}

---
"""

ROOT_CLAUDE_TEMPLATE = """# Claude Instructions

> Project-owned Claude instructions scaffolded by ARMS. Customize this file with repository-specific guidance as the project evolves.

{shared_section}

---
"""


def require_yaml_dependency():
    if yaml is None:
        raise ImportError(
            "PyYAML is required by arms-engine but could not be imported. "
            "Reinstall dependencies with `pip install -e .` or `pip install pyyaml`."
        ) from YAML_IMPORT_ERROR
    return yaml


def build_skill_mirror_ignore(skill_name):
    ignored_entries = [".DS_Store", "__pycache__"]
    ignored_entries.extend(REFERENCE_ONLY_SKILL_DIRS.get(skill_name, ()))
    return shutil.ignore_patterns(*ignored_entries)


def remove_obsolete_gemini_skill_artifacts(project_root):
    obsolete_paths = (
        os.path.join(project_root, ".gemini/skills"),
        os.path.join(project_root, ".gemini/skills.yaml"),
        os.path.join(project_root, ".gemini/skills-index.md"),
    )
    removed_paths = []
    for obsolete_path in obsolete_paths:
        if os.path.isdir(obsolete_path):
            shutil.rmtree(obsolete_path)
            removed_paths.append(os.path.relpath(obsolete_path, project_root))
        elif os.path.isfile(obsolete_path):
            os.remove(obsolete_path)
            removed_paths.append(os.path.relpath(obsolete_path, project_root))

    if removed_paths:
        print(
            "🧹 Removed obsolete Gemini skill artifacts: {}.".format(
                ", ".join(f"`{path}`" for path in removed_paths)
            )
        )
    return removed_paths


def scaffold_project_instruction_files(project_root):
    scaffold_targets = (
        (
            os.path.join(project_root, "GEMINI.md"),
            ROOT_GEMINI_TEMPLATE.format(shared_section=PROJECT_INSTRUCTION_SHARED_SECTION),
            "GEMINI.md",
        ),
        (
            os.path.join(project_root, ".github", "copilot-instructions.md"),
            COPILOT_INSTRUCTIONS_TEMPLATE.format(shared_section=PROJECT_INSTRUCTION_SHARED_SECTION),
            ".github/copilot-instructions.md",
        ),
        (
            os.path.join(project_root, "CLAUDE.md"),
            ROOT_CLAUDE_TEMPLATE.format(shared_section=PROJECT_INSTRUCTION_SHARED_SECTION),
            "CLAUDE.md",
        ),
    )
    created = []
    for path, content, relative_path in scaffold_targets:
        if os.path.exists(path):
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        created.append(relative_path)

    if created:
        print(
            "🧾 Scaffolded project instruction files: {}.".format(
                ", ".join(f"`{path}`" for path in created)
            )
        )
    return created


def remove_obsolete_instruction_bridges(project_root):
    legacy_gemini_path = os.path.join(project_root, ".gemini", "GEMINI.md")
    if not os.path.isfile(legacy_gemini_path):
        return []

    with open(legacy_gemini_path, "r", encoding="utf-8") as handle:
        existing_content = handle.read().strip()
    if (
        "Managed bridge created by ARMS so Gemini CLI normal chat follows the shared task-intake protocol."
        not in existing_content
        or PROJECT_INSTRUCTION_SHARED_SECTION.strip() not in existing_content
    ):
        return []

    os.remove(legacy_gemini_path)
    removed = [".gemini/GEMINI.md"]
    print(
        "🧹 Removed obsolete managed instruction bridge: {}.".format(
            ", ".join(f"`{path}`" for path in removed)
        )
    )
    return removed


def ensure_agent_tools_frontmatter(content):
    if "tools:" in content:
        return content

    parts = content.split("---", 2)
    if len(parts) >= 3:
        return "---\ntools: [\"*\"]" + parts[1] + "---" + parts[2]
    return content


def split_agent_rules_text(rules_text):
    collapsed = " ".join((rules_text or "").split()).strip()
    if not collapsed:
        return []
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z\"`])", collapsed)
        if part.strip()
    ]


def inject_agent_runtime_rules(content, rules_text):
    rule_lines = split_agent_rules_text(rules_text)
    missing_rules = [rule for rule in rule_lines if rule not in content]
    if not missing_rules:
        return content

    rendered_rules = "\n".join(f"- {rule}" for rule in missing_rules)
    if "## Runtime Rules" in content:
        return content.rstrip() + "\n" + rendered_rules + "\n"
    return content.rstrip() + "\n\n## Runtime Rules\n" + rendered_rules + "\n"


def build_agent_sync_content(content, agent_info):
    content = ensure_agent_tools_frontmatter(content)
    return inject_agent_runtime_rules(content, agent_info.get("rules", ""))


def sync_agent_markdowns(arms_root, target_dir):
    agents_dir = os.path.join(arms_root, "agents")
    registry = {
        agent["name"]: agent
        for agent in load_agents_registry(arms_root)
    }

    if not os.path.exists(agents_dir):
        return

    os.makedirs(target_dir, exist_ok=True)
    source_agent_files = {
        filename
        for filename in os.listdir(agents_dir)
        if filename.endswith(".md")
    }
    for entry in os.listdir(target_dir):
        entry_path = os.path.join(target_dir, entry)
        if os.path.isfile(entry_path) and entry.endswith(".md") and entry not in source_agent_files:
            os.remove(entry_path)

    for filename in source_agent_files:
        src = os.path.join(agents_dir, filename)
        dest = os.path.join(target_dir, filename)
        agent_name = os.path.splitext(filename)[0]

        with open(src, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        normalized_content = build_agent_sync_content(content, registry.get(agent_name, {}))

        with open(dest, "w", encoding="utf-8") as f:
            f.write(normalized_content)


def sync_agents(arms_root, project_root):
    print("🤖 Syncing Agents...")
    target_dir = os.path.join(project_root, ".gemini/agents")
    sync_agent_markdowns(arms_root, target_dir)

    yaml_src = os.path.join(arms_root, "agents.yaml")
    yaml_dest = os.path.join(project_root, ".gemini/agents.yaml")
    if os.path.exists(yaml_src):
        print("📄 Syncing agents.yaml...")
        shutil.copy2(yaml_src, yaml_dest)


def sync_agents_copilot(arms_root, project_root):
    print("🤖 Syncing Agents for Copilot CLI...")
    target_dir = os.path.join(project_root, ".github/agents")
    os.makedirs(target_dir, exist_ok=True)
    sync_agent_markdowns(arms_root, target_dir)


def sync_agents_claude(arms_root, project_root):
    print("🤖 Syncing Agents for Claude Code...")
    target_dir = os.path.join(project_root, ".claude", "agents")
    os.makedirs(target_dir, exist_ok=True)
    sync_agent_markdowns(arms_root, target_dir)


def sync_skills_claude(arms_root, project_root):
    print("🔌 Syncing Skills for Claude Code...")
    skills_src = os.path.join(arms_root, "skills")
    target_dir = os.path.join(project_root, ".claude", "commands")
    os.makedirs(target_dir, exist_ok=True)

    if not os.path.exists(skills_src):
        return

    current_skill_dir_names = {
        name
        for name in os.listdir(skills_src)
        if os.path.isdir(os.path.join(skills_src, name))
        and os.path.exists(os.path.join(skills_src, name, "SKILL.md"))
    }

    # Remove stale ARMS-managed skill command files (only those matching known skill names)
    for entry in os.listdir(target_dir):
        if entry.endswith(".md") and entry[:-3] in current_skill_dir_names:
            os.remove(os.path.join(target_dir, entry))

    for skill_dir_name in current_skill_dir_names:
        skill_md_path = os.path.join(skills_src, skill_dir_name, "SKILL.md")
        try:
            metadata = parse_skill_metadata(skill_md_path, skill_dir_name)
        except ValueError as exc:
            print(f"⚠️  Skipping skill '{skill_dir_name}': invalid SKILL.md ({exc})")
            continue

        with open(skill_md_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        normalized_content = ensure_skill_frontmatter(content, metadata["name"])
        dest_path = os.path.join(target_dir, f"{skill_dir_name}.md")
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(normalized_content)


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
        if not line or line == "---" or line.startswith("#") or line.startswith("**ID"):
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
            yaml_module = require_yaml_dependency()
            try:
                parsed_frontmatter = yaml_module.safe_load(frontmatter) or {}
            except yaml_module.YAMLError as error:
                raise ValueError(
                    "Invalid YAML frontmatter in `{}`: {}".format(skill_md_path, error)
                ) from error
            if not isinstance(parsed_frontmatter, dict):
                raise ValueError(
                    "YAML frontmatter in `{}` must parse to a mapping.".format(skill_md_path)
                )
            if isinstance(parsed_frontmatter, dict):
                for key, value in parsed_frontmatter.items():
                    normalized_key = str(key).strip().lower()
                    if isinstance(value, str):
                        metadata[normalized_key] = " ".join(value.split()).strip()
                    elif isinstance(value, (list, tuple)):
                        metadata[normalized_key] = [
                            str(item).strip()
                            for item in value
                            if str(item).strip()
                        ]
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
    print("🔌 Syncing Skills for CLI discovery...")
    skills_src = os.path.join(arms_root, "skills")
    remove_obsolete_gemini_skill_artifacts(project_root)
    target_dirs = [
        os.path.join(project_root, ".agents/skills"),
        os.path.join(project_root, ".github/skills"),
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
                try:
                    metadata = parse_skill_metadata(skill_md_path, skill_name)
                except ValueError as exc:
                    print(f"⚠️  Skipping skill '{skill_name}': invalid SKILL.md ({exc})")
                    continue
                for target_dir in target_dirs:
                    legacy_dest = os.path.join(target_dir, f"{skill_name}.md")
                    if os.path.isfile(legacy_dest):
                        os.remove(legacy_dest)

                    dest_dir = os.path.join(target_dir, skill_name)
                    shutil.copytree(
                        skill_path,
                        dest_dir,
                        ignore=build_skill_mirror_ignore(skill_name),
                    )

                    dest_skill_md_path = os.path.join(dest_dir, "SKILL.md")
                    with open(dest_skill_md_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    normalized_content = ensure_skill_frontmatter(content, metadata["name"])

                    with open(dest_skill_md_path, "w", encoding="utf-8") as f:
                        f.write(normalized_content)


def create_skills_registry(arms_root, project_root):
    print("📋 Creating Skills Registry...")
    skills_data = build_skills_data(arms_root)
    remove_obsolete_gemini_skill_artifacts(project_root)
    write_skills_registry_files(
        os.path.join(project_root, ".agents"),
        ".agents/skills",
        skills_data,
    )
    write_skills_registry_files(
        os.path.join(project_root, ".github"),
        ".github/skills",
        skills_data,
    )
    claude_dir = os.path.join(project_root, ".claude")
    os.makedirs(claude_dir, exist_ok=True)
    write_skills_registry_files(
        claude_dir,
        ".claude/commands",
        skills_data,
    )


def build_skills_data(arms_root):
    skills_src = os.path.join(arms_root, "skills")
    skills_data = {}
    if os.path.exists(skills_src):
        for skill_name in sorted(os.listdir(skills_src)):
            skill_path = os.path.join(skills_src, skill_name)
            skill_md_path = os.path.join(skill_path, "SKILL.md")

            if os.path.isdir(skill_path) and os.path.exists(skill_md_path):
                try:
                    metadata = parse_skill_metadata(skill_md_path, skill_name)
                except ValueError as exc:
                    print(f"⚠️  Skipping skill '{skill_name}': invalid SKILL.md ({exc})")
                    continue
                canonical_name = metadata["name"]
                skills_data[canonical_name] = {
                    "name": canonical_name,
                    "description": metadata["description"],
                    "source_directory": skill_name,
                }
    return skills_data


def write_skills_registry_files(target_root, skill_mirror_path, skills_data):
    registry_dest = os.path.join(target_root, "skills.yaml")
    index_dest = os.path.join(target_root, "skills-index.md")

    with open(registry_dest, "w", encoding="utf-8") as f:
        f.write("# ARMS Skills Registry\n")
        f.write("# Auto-generated by arms init\n\n")
        f.write("skills:\n")
        for skill_name, skill_info in sorted(skills_data.items()):
            f.write(f"  {skill_name}:\n")
            f.write(f"    name: {skill_info['name']}\n")
            f.write(f"    description: {skill_info['description']}\n")
            if skill_info["source_directory"] != skill_name:
                f.write(f"    source_directory: {skill_info['source_directory']}\n")

    with open(index_dest, "w", encoding="utf-8") as f:
        f.write("# ARMS Skills Index\n\n")
        f.write("> **Quick reference:** All available skills for supported CLIs\n\n")
        f.write("## Available Skills\n\n")
        for skill_name, skill_info in sorted(skills_data.items()):
            f.write(f"### `{skill_name}/SKILL.md`\n")
            f.write(f"**{skill_info['name']}**\n\n")
            f.write(f"{skill_info['description']}\n\n")
            skill_file_dir = skill_info["source_directory"]
            f.write(f"**File:** `{skill_mirror_path}/{skill_file_dir}/SKILL.md`\n\n")
            if skill_info["source_directory"] != skill_name:
                f.write(f"**Source Directory:** `arms_engine/skills/{skill_info['source_directory']}`\n\n")

        f.write("## Usage\n\n")
        f.write("Reference a skill from the local skill mirror:\n\n")
        f.write("```\n")
        f.write(f"{skill_mirror_path}/arms-orchestrator/SKILL.md\n")
        f.write("Describe your task here\n")
        f.write("```\n")


def sync_root_agents_guide(arms_root, project_root):
    print("📄 Syncing AGENTS.md (root agent guide)...")
    src = os.path.join(arms_root, "AGENTS.md")
    dest = os.path.join(project_root, "AGENTS.md")
    if os.path.exists(src):
        shutil.copy2(src, dest)


def sync_engine_instructions(arms_root, project_root):
    print("📄 Syncing ENGINE.md (ARMS Engine Instructions)...")
    src = os.path.join(arms_root, "ENGINE.md")
    if not os.path.exists(src):
        return

    dest = os.path.join(project_root, ".arms/ENGINE.md")
    shutil.copy2(src, dest)


def sync_workflow(arms_root, project_root):
    print("📋 Syncing Workflow Protocols...")
    wf_src = os.path.join(arms_root, "workflow")
    wf_dest = os.path.join(project_root, ".arms/workflow")
    os.makedirs(wf_dest, exist_ok=True)

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
        suffix = " [Active]" if skill["name"] == "arms-orchestrator" else ""
        skills.append(f"- {skill['name']}{suffix}")
    return "\n".join(skills)


def load_agents_registry(arms_root):
    yaml_path = os.path.join(arms_root, "agents.yaml")
    if not os.path.exists(yaml_path):
        return []

    with open(yaml_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    yaml_module = require_yaml_dependency()
    try:
        parsed = yaml_module.safe_load(content) or {}
    except yaml_module.YAMLError as error:
        raise ValueError("Invalid YAML in `{}`: {}".format(yaml_path, error)) from error
    if not isinstance(parsed, dict):
        raise ValueError("Top-level YAML in `{}` must parse to a mapping.".format(yaml_path))

    raw_agents = parsed.get("agents", {})
    if not isinstance(raw_agents, dict):
        return []

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
                "rules": str(info.get("rules", "")).strip(),
            }
        )
    return agents


def resolve_agents_with_skills(arms_root, announce=False):
    agents = load_agents_registry(arms_root)
    skill_catalog = discover_skill_catalog(arms_root)
    return agents, skill_catalog, []


def build_agent_skill_bindings(agents):
    return {
        agent["name"]: list(agent.get("skills", []))
        for agent in agents
    }


def _patch_agents_yaml_add_skill(text, agent_name, skill_name):
    """Surgically insert *skill_name* into *agent_name*'s skills list in
    the raw YAML text, preserving all surrounding formatting.

    Returns the modified text, or the original text unchanged if the skill
    is already present or the agent cannot be found.
    """
    lines = text.splitlines(keepends=True)
    agent_header = f"  {agent_name}:\n"

    agent_start = next(
        (i for i, line in enumerate(lines) if line == agent_header), None
    )
    if agent_start is None:
        return text

    # Locate the end of this agent's block (next 2-space-indented key or EOF).
    agent_end = len(lines)
    for i in range(agent_start + 1, len(lines)):
        line = lines[i]
        if (
            line.startswith("  ")
            and not line.startswith("   ")
            and not line.startswith("  #")
        ):
            agent_end = i
            break

    agent_block = "".join(lines[agent_start:agent_end])
    if f"- {skill_name}" in agent_block:
        return text  # already bound

    # Try to find an existing `    skills:` section.
    skills_line = next(
        (i for i in range(agent_start + 1, agent_end) if lines[i].rstrip() == "    skills:"),
        None,
    )

    if skills_line is not None:
        # Append after the last existing `      - ...` item in the list.
        skills_end = skills_line + 1
        while skills_end < agent_end and lines[skills_end].startswith("      - "):
            skills_end += 1
        lines.insert(skills_end, f"      - {skill_name}\n")
    else:
        # No skills section yet — insert one.  Place it before `rules:` when
        # present, otherwise before the next agent block.
        insert_at = agent_end
        for i in range(agent_start + 1, agent_end):
            if lines[i].startswith("    rules:"):
                insert_at = i
                break
        lines.insert(insert_at, f"    skills:\n      - {skill_name}\n")

    return "".join(lines)


def reconcile_skill_agent_bindings(arms_root):
    """Read every SKILL.md and, for any that declare an ``agents:`` frontmatter
    field, ensure those agents have the skill listed in ``agents.yaml``.

    Returns a mapping of ``{agent_name: [newly_added_skills]}`` for all changes
    written.  The function is additive-only: it never removes existing bindings.
    The original file format and key ordering are preserved via surgical text
    patching — no YAML round-trip dump is performed.
    """
    yaml_path = os.path.join(arms_root, "agents.yaml")
    if not os.path.exists(yaml_path):
        return {}

    yaml_module = require_yaml_dependency()

    with open(yaml_path, "r", encoding="utf-8", errors="ignore") as fh:
        raw_content = fh.read()

    try:
        registry = yaml_module.safe_load(raw_content) or {}
    except yaml_module.YAMLError:
        return {}

    if not isinstance(registry, dict):
        return {}

    agents_map = registry.get("agents") or {}
    if not isinstance(agents_map, dict):
        return {}

    skills_dir = os.path.join(arms_root, "skills")
    if not os.path.exists(skills_dir):
        return {}

    added = {}
    patched_text = raw_content

    for skill_dir_name in sorted(os.listdir(skills_dir)):
        skill_path = os.path.join(skills_dir, skill_dir_name)
        skill_md_path = os.path.join(skill_path, "SKILL.md")
        if not (os.path.isdir(skill_path) and os.path.exists(skill_md_path)):
            continue

        try:
            metadata = parse_skill_metadata(skill_md_path, skill_dir_name)
        except ValueError:
            continue

        declared_agents = metadata.get("agents") or []
        if isinstance(declared_agents, str):
            declared_agents = [declared_agents]
        declared_agents = [str(a).strip() for a in declared_agents if str(a).strip()]
        if not declared_agents:
            continue

        skill_name = metadata["name"]

        for agent_name in declared_agents:
            if agent_name not in agents_map:
                continue
            new_text = _patch_agents_yaml_add_skill(patched_text, agent_name, skill_name)
            if new_text != patched_text:
                patched_text = new_text
                added.setdefault(agent_name, []).append(skill_name)

    if added:
        with open(yaml_path, "w", encoding="utf-8") as fh:
            fh.write(patched_text)
        for agent_name, skills in added.items():
            print(
                "🔗 Auto-bound skill(s) {} → {}".format(
                    ", ".join(f"`{s}`" for s in skills), agent_name
                )
            )

    return added


def discover_agents_and_skills(arms_root):
    print("👥 Discovering Agents & associated Skills...")
    agents, _, _ = resolve_agents_with_skills(arms_root, announce=True)

    agents_info = []
    for agent in agents:
        current_skills = agent.get("skills", [])
        skills_str = f" ({', '.join(current_skills)})" if current_skills else ""
        agents_info.append(f"- {agent['name']}{skills_str}")

    return "\n".join(agents_info)
