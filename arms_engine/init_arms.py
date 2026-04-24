import os
import sys
import shutil
import datetime
import argparse
import re

try:
    from ._version import version as __version__
except (ImportError, ValueError):
    __version__ = "1.0.0-dev" # Fallback for local development

def get_arms_root():
    # When installed as a package, this is the arms_engine directory
    return os.path.dirname(os.path.abspath(__file__))

def get_project_root():
    return os.getcwd()

def setup_folders(project_root):
    folders = [
        ".gemini/agent-outputs",
        ".gemini/reports",
        ".gemini/agents",
        ".gemini/skills",
        ".gemini/workflow"
    ]
    for folder in folders:
        path = os.path.join(project_root, folder)
        os.makedirs(path, exist_ok=True)

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
                with open(dest, 'w') as f:
                    f.write(content)

def sync_skills_copilot(arms_root, project_root):
    """Sync skill SKILL.md files to .github/skills/ for Copilot CLI discovery."""
    print("🔌 Syncing Skills for Copilot CLI...")
    skills_src = os.path.join(arms_root, "skills")
    target_dir = os.path.join(project_root, ".github/skills")
    os.makedirs(target_dir, exist_ok=True)

    if os.path.exists(skills_src):
        for skill_name in os.listdir(skills_src):
            skill_path = os.path.join(skills_src, skill_name)
            skill_md_path = os.path.join(skill_path, "SKILL.md")
            
            if os.path.isdir(skill_path) and os.path.exists(skill_md_path):
                dest = os.path.join(target_dir, f"{skill_name}.md")
                with open(skill_md_path, 'r') as f:
                    content = f.read()
                with open(dest, 'w') as f:
                    f.write(content)

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

def initialize_brand_context(project_root):
    brand_path = os.path.join(project_root, ".gemini/BRAND.md")
    legacy_paths = [
        os.path.join(project_root, "brand-context.md"),
        os.path.join(project_root, ".gemini/brand-context.md")
    ]
    
    # 1. Check for existing BRAND.md
    if os.path.exists(brand_path):
        with open(brand_path, 'r') as f:
            if "[Name]" in f.read():
                print("⚠️  BRAND.md is currently a template. Please fill it out to provide agents with design context!")
        return

    # 2. Migration check
    for legacy in legacy_paths:
        if os.path.exists(legacy):
            print(f"📦 Migrating legacy brand context from {os.path.basename(legacy)}...")
            shutil.move(legacy, brand_path)
            return

    # 3. Create new template
    print("🎨 Initializing new BRAND.md...")
    template = """# Brand Context
> Managed by ARMS Engine. Referenced by: Frontend, SEO, and Media agents.

---

## Identity
- **Project Name:** [Name]
- **Mission:** [Purpose]
- **Vision:** [Long-term goal]
- **Personality:** [Voice/Tone]
- **Voice & Tone:** [Approach]

## Positioning
- **Primary Audience:** [Target]
- **Core Values:** [Values]
- **Differentiation:** [Unique Factor]

## Visual Identity
- **Color Palette:** [HEX/OKLCH]
- **Typography:** [Google Fonts]
- **Logo Status:** [Generated/Pending]
- **Visual Direction:** [Glassmorphism/Dark Mode/etc]

## Use Case Implications
- **Project Type:** [SaaS/Community/etc]
- **Design Priority:** [UX Factor]

## Notes
- [Misc preferences]
"""
    with open(brand_path, 'w') as f:
        f.write(template)
    print("📢 BRAND.md created. ACTION REQUIRED: Please fill out the identity and vision to enable high-fidelity orchestration.")

def update_session(project_root, arms_root, skills_list, agents_list):
    print("📄 Updating session log...")
    session_path = os.path.join(project_root, ".gemini/SESSION.md")
    
    existing_content = ""
    if os.path.exists(session_path):
        with open(session_path, 'r') as f:
            existing_content = f.read()
    
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
                    new_tasks_content.append(f"## {header}\n{content}")
                else:
                    # Provide default content for empty sections
                    if header == "Active Tasks":
                        new_tasks_content.append(f"## {header}\n| # | Task | Assigned Agent | Active Skill | Status |\n|---|------|----------------|--------------|--------|")
                    elif header == "Completed Tasks":
                        new_tasks_content.append(f"## {header}\n- None")
                    elif header == "Blockers":
                        new_tasks_content.append(f"## {header}\nNone")
                seen_headers.add(header)
        
        # Ensure all required sections are present even if not in original
        for req in ["Active Tasks", "Completed Tasks", "Blockers"]:
            if req not in seen_headers:
                if req == "Active Tasks":
                    new_tasks_content.append(f"## {req}\n| # | Task | Assigned Agent | Active Skill | Status |\n|---|------|----------------|--------------|--------|")
                elif req == "Completed Tasks":
                    new_tasks_content.append(f"## {req}\n- None")
                elif req == "Blockers":
                    new_tasks_content.append(f"## {req}\nNone")

        tasks_content = "\n\n".join(new_tasks_content)
    else:
        tasks_content = """## Active Tasks
| # | Task | Assigned Agent | Active Skill | Status |
|---|------|----------------|--------------|--------|

## Completed Tasks
- None

## Blockers
None"""

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    content = f"""# ARMS Session Log
Generated: {now}

## Environment
- ARMS Root: {arms_root}
- Project Root: {project_root}
- Execution Mode: Parallel

## Active Agents
{agents_list}

## Active Skills
{skills_list}

{tasks_content}"""

    with open(session_path, 'w') as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(description="ARMS Engine Activator")
    parser.add_argument("command", nargs="?", default="init", help="Command to run (default: init)")
    parser.add_argument("--root", help="Override arms root path")
    parser.add_argument("--version", action="version", version=f"ARMS Engine {__version__}")
    args = parser.parse_args()

    project_root = get_project_root()
    arms_root = args.root or get_arms_root()
    
    print(f"🚀 Initializing ARMS Engine...")
    print(f"📂 Project: {project_root}")
    print(f"🛡️  Engine:  {arms_root}")
    
    setup_folders(project_root)
    sync_agents(arms_root, project_root)
    sync_agents_copilot(arms_root, project_root)

    sync_skills(arms_root, project_root)
    sync_skills_copilot(arms_root, project_root)
    sync_workflow(arms_root, project_root)
    initialize_brand_context(project_root)
    
    skills_list = discover_skills(arms_root)
    agents_list = discover_agents_and_skills(arms_root)
    update_session(project_root, arms_root, skills_list, agents_list)
    
    # Sync GEMINI.md
    gemini_src = os.path.join(arms_root, "GEMINI.md")
    gemini_dest = os.path.join(project_root, ".gemini/GEMINI.md")
    if os.path.exists(gemini_src):
        shutil.copy2(gemini_src, gemini_dest)
        print("📄 Core Directives (GEMINI.md) synced.")

    # Sync AGENTS.md for Copilot CLI
    sync_copilot_instructions(arms_root, project_root)

    print("\n✅ ARMS Engine sequence complete. → HALT")

if __name__ == "__main__":
    main()

