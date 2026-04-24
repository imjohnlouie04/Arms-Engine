import os
import sys
import shutil
import datetime
import argparse
import json
import re

try:
    from ._version import version as __version__
except (ImportError, ValueError):
    __version__ = "1.3.4-dev" # Fallback for local development

def get_arms_root():
    # When installed as a package, this is the arms_engine directory
    return os.path.dirname(os.path.abspath(__file__))

def get_project_root():
    """Climb up from CWD to find the nearest project root (marked by .git, .arms, or .gemini)."""
    curr = os.getcwd()
    while curr != os.path.dirname(curr):
        if any(os.path.exists(os.path.join(curr, m)) for m in [".git", ".arms", ".gemini", "package.json"]):
            return curr
        curr = os.path.dirname(curr)
    return os.getcwd() # Fallback to CWD if no marker found

def setup_folders(project_root):
    # .gemini/ — Gemini AI assistant config (GEMINI.md, MEMORY.md, synced assets)
    gemini_folders = [
        ".gemini/agent-outputs",
        ".gemini/reports",
        ".gemini/agents",
        ".gemini/skills",
        ".gemini/workflow"
    ]
    # .arms/ — ARMS engine state (SESSION.md, SESSION_ARCHIVE.md, BRAND.md)
    arms_folders = [
        ".arms",
    ]
    for folder in gemini_folders + arms_folders:
        path = os.path.join(project_root, folder)
        os.makedirs(path, exist_ok=True)

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
    ]

    for label, legacy_path, target_path in migrations:
        if not os.path.exists(legacy_path):
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

def normalize_active_tasks_table(content):
    """Upgrade legacy Active Tasks tables to the current schema."""
    new_header = "| # | Task | Assigned Agent | Active Skill | Dependencies | Status |"
    new_divider = "|---|------|----------------|--------------|--------------|--------|"
    legacy_header = "| # | Task | Assigned Agent | Active Skill | Status |"
    legacy_divider = "|---|------|----------------|--------------|--------|"

    stripped = content.strip()
    if not stripped:
        return f"{new_header}\n{new_divider}"

    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].strip() == legacy_header and lines[1].strip() == legacy_divider:
        normalized = [new_header, new_divider]
        for line in lines[2:]:
            row = line.strip()
            if row.startswith("|") and row.endswith("|"):
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                if len(cells) == 5:
                    cells.insert(4, "None")
                    normalized.append("| " + " | ".join(cells) + " |")
                    continue
            normalized.append(line)
        return "\n".join(normalized)

    return stripped

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

def sync_skills(arms_root, project_root):
    print("🔌 Installing Skills...")
    skills_src = os.path.join(arms_root, "skills")
    skills_dest = os.path.join(project_root, ".gemini/skills")
    
    if os.path.exists(skills_src):
        for name in os.listdir(skills_src):
            src_path = os.path.join(skills_src, name)
            dest_path = os.path.join(skills_dest, name)
            
            if os.path.isdir(src_path) and os.path.exists(os.path.join(src_path, "SKILL.md")):
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                shutil.copytree(src_path, dest_path)

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
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("**ID"):
            continue
        if line.startswith("**Role"):
            return re.sub(r"^\*\*Role:?\*\*:?\s*", "", line).strip().strip(".")
        return line[:240]
    return f"Specialized guidance for {skill_name.replace('-', ' ')}."

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
    """Sync skill directories to .github/skills/<skill-name>/SKILL.md for Copilot discovery."""
    print("🔌 Syncing Skills for Copilot CLI...")
    skills_src = os.path.join(arms_root, "skills")
    target_dir = os.path.join(project_root, ".github/skills")
    os.makedirs(target_dir, exist_ok=True)

    if os.path.exists(skills_src):
        for skill_name in os.listdir(skills_src):
            skill_path = os.path.join(skills_src, skill_name)
            skill_md_path = os.path.join(skill_path, "SKILL.md")
            
            if os.path.isdir(skill_path) and os.path.exists(skill_md_path):
                legacy_dest = os.path.join(target_dir, f"{skill_name}.md")
                if os.path.isfile(legacy_dest):
                    os.remove(legacy_dest)

                dest_dir = os.path.join(target_dir, skill_name)
                if os.path.exists(dest_dir):
                    shutil.rmtree(dest_dir)
                shutil.copytree(
                    skill_path,
                    dest_dir,
                    ignore=shutil.ignore_patterns(".DS_Store", "__pycache__"),
                )

                dest_skill_md_path = os.path.join(dest_dir, "SKILL.md")
                with open(dest_skill_md_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                normalized_content = ensure_skill_frontmatter(content, skill_name)

                with open(dest_skill_md_path, 'w', encoding='utf-8') as f:
                    f.write(normalized_content)

def create_skills_registry(arms_root, project_root):
    """Create a skills registry file for Copilot CLI discovery."""
    print("📋 Creating Skills Registry...")
    skills_src = os.path.join(arms_root, "skills")
    registry_dest = os.path.join(project_root, ".github/skills.yaml")
    index_dest = os.path.join(project_root, ".github/skills-index.md")
    
    skills_data = {}
    if os.path.exists(skills_src):
        for skill_name in sorted(os.listdir(skills_src)):
            skill_path = os.path.join(skills_src, skill_name)
            skill_md_path = os.path.join(skill_path, "SKILL.md")
            
            if os.path.isdir(skill_path) and os.path.exists(skill_md_path):
                # Extract metadata from SKILL.md frontmatter
                with open(skill_md_path, 'r') as f:
                    lines = f.readlines()
                
                # Parse YAML frontmatter
                metadata = {}
                in_frontmatter = False
                for i, line in enumerate(lines):
                    if line.strip() == "---":
                        if not in_frontmatter:
                            in_frontmatter = True
                        else:
                            break
                    elif in_frontmatter and i > 0:
                        if ":" in line:
                            key, value = line.split(":", 1)
                            metadata[key.strip().lower()] = value.strip()
                
                skills_data[skill_name] = {
                    "name": metadata.get("name", skill_name),
                    "description": metadata.get("description", ""),
                }
    
    # Write YAML registry
    with open(registry_dest, 'w') as f:
        f.write("# ARMS Skills Registry\n")
        f.write("# Auto-generated by arms init\n\n")
        f.write("skills:\n")
        for skill_name, skill_info in skills_data.items():
            f.write(f"  {skill_name}:\n")
            f.write(f"    name: {skill_info['name']}\n")
            f.write(f"    description: {skill_info['description']}\n")
    
    # Write Markdown index for quick reference
    with open(index_dest, 'w') as f:
        f.write("# ARMS Skills Index\n\n")
        f.write("> **Quick reference:** All available skills for Copilot CLI\n\n")
        f.write("## Available Skills\n\n")
        for skill_name, skill_info in skills_data.items():
            f.write(f"### `{skill_name}/SKILL.md`\n")
            f.write(f"**{skill_info['name']}**\n\n")
            f.write(f"{skill_info['description']}\n\n")
            f.write(f"**File:** `.github/skills/{skill_name}/SKILL.md`\n\n")
        
        f.write("## Usage\n\n")
        f.write("Reference a skill in Copilot CLI:\n\n")
        f.write("```\n")
        f.write("@skills/arms-orchestrator/SKILL.md\n")
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
    wf_dest = os.path.join(project_root, ".gemini/workflow")
    
    if os.path.exists(wf_src):
        for filename in os.listdir(wf_src):
            src = os.path.join(wf_src, filename)
            dest = os.path.join(wf_dest, filename)
            if os.path.isfile(src):
                shutil.copy(src, dest)

def discover_skills(arms_root):
    print("🔍 Discovering Skills...")
    skills_dir = os.path.join(arms_root, "skills")
    skills = []
    if os.path.exists(skills_dir):
        for name in sorted(os.listdir(skills_dir)):
            path = os.path.join(skills_dir, name)
            if os.path.isdir(path) and os.path.exists(os.path.join(path, "SKILL.md")):
                if name == "arms-orchestrator":
                    skills.append(f"- {name} [Active]")
                else:
                    skills.append(f"- {name}")
    return "\n".join(skills)

def discover_agents_and_skills(arms_root):
    print("👥 Discovering Agents & associated Skills...")
    yaml_path = os.path.join(arms_root, "agents.yaml")
    agents_info = []
    if os.path.exists(yaml_path):
        with open(yaml_path, 'r') as f:
            lines = f.readlines()
        
        current_agent = None
        current_skills = []
        in_skills = False
        
        for line in lines:
            # Match agent name: ^  agent-name:
            agent_match = re.match(r'^\s\s([\w-]+):', line)
            if agent_match:
                if current_agent:
                    skills_str = f" ({', '.join(current_skills)})" if current_skills else ""
                    agents_info.append(f"- {current_agent}{skills_str}")
                current_agent = agent_match.group(1)
                current_skills = []
                in_skills = False
                continue
            
            # Match skills header: ^    skills:
            if current_agent and re.match(r'^\s\s\s\sskills:', line):
                in_skills = True
                continue
            
            # Match skill item: ^      - skill-name
            if in_skills:
                skill_match = re.match(r'^\s\s\s\s\s\s-\s([\w-]+)', line)
                if skill_match:
                    current_skills.append(skill_match.group(1))
                else:
                    # If it's not a skill item and we were in skills, we might be out
                    if line.strip() and not line.strip().startswith("-"):
                        in_skills = False
        
        # Add last agent
        if current_agent:
            skills_str = f" ({', '.join(current_skills)})" if current_skills else ""
            agents_info.append(f"- {current_agent}{skills_str}")
            
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

def read_text_file(path, max_chars=40000):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read(max_chars)

def brand_file_requires_bootstrap(content):
    if not content.strip():
        return True
    return any(token in content for token in PLACEHOLDER_BRAND_TOKENS)

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
    for marker in PROJECT_MARKER_FILES:
        if os.path.exists(os.path.join(project_root, marker)):
            return True

    for marker_dir in PROJECT_MARKER_DIRS:
        path = os.path.join(project_root, marker_dir)
        if os.path.isdir(path):
            with os.scandir(path) as entries:
                if next(entries, None) is not None:
                    return True

    meaningful_entries = [
        name
        for name in os.listdir(project_root)
        if name not in IGNORED_PROJECT_ENTRIES and not name.startswith(".")
    ]
    return bool(meaningful_entries)

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
"""

def initialize_brand_context(project_root):
    brand_path = os.path.join(project_root, ".arms/BRAND.md")

    existing_content = read_text_file(brand_path)
    if existing_content and not brand_file_requires_bootstrap(existing_content):
        return

    if detect_existing_project(project_root):
        print("🎨 Generating BRAND.md from existing project context...")
        with open(brand_path, "w", encoding="utf-8") as f:
            f.write(render_inferred_brand_context(project_root))
        print("📢 BRAND.md generated from repository signals. Review inferred fields and refine where needed.")
        return

    print("🎨 Initializing new-project BRAND.md questionnaire...")
    with open(brand_path, "w", encoding="utf-8") as f:
        f.write(render_new_project_brand_questionnaire(project_root))
    print("📢 BRAND.md created for a new project. User answers are required before high-fidelity brand work begins.")

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
                        content = normalize_active_tasks_table(content)
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
    exec_mode = "Parallel" 
    yolo_status = "Enabled" if yolo else "Disabled"
    
    content = f"""# ARMS Session Log
Generated: {now}

## Environment
- ARMS Root: {arms_root}
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


def main():
    parser = argparse.ArgumentParser(description="ARMS Engine Activator")
    parser.add_argument("command", nargs="*", default=["init"], help="Command to run (e.g., init, init yolo, start)")
    parser.add_argument("--root", help="Override arms root path")
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
    
    print(f"🚀 Initializing ARMS Engine...")
    print(f"📂 Project: {project_root}")
    print(f"🛡️  Engine:  {arms_root}")
    if is_yolo:
        print("⚡ Mode:    YOLO (Full Automation)")
    
    setup_folders(project_root)
    migrate_legacy_state(project_root)
    sync_agents(arms_root, project_root)
    sync_agents_copilot(arms_root, project_root)

    sync_skills(arms_root, project_root)
    sync_skills_copilot(arms_root, project_root)
    create_skills_registry(arms_root, project_root)
    sync_workflow(arms_root, project_root)
    initialize_brand_context(project_root)
    
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

    if is_yolo:
        print("\n✅ ARMS Engine ready. Fleet mode activated.")
    else:
        print("\n✅ ARMS Engine sequence complete. → HALT")

if __name__ == "__main__":
    main()
