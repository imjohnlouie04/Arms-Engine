import os
import re
import argparse

try:
    from ._version import version as __version__
except (ImportError, ValueError):
    __version__ = "1.3.3-dev"

def get_arms_root():
    return os.path.dirname(os.path.abspath(__file__))

def get_agent_docs(arms_root):
    yaml_path = os.path.join(arms_root, "agents.yaml")
    agent_docs = []
    if os.path.exists(yaml_path):
        with open(yaml_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_agent = None
        current_role = ""
        current_scope = ""
        
        for line in lines:
            agent_match = re.match(r'^\s\s([\w-]+):', line)
            if agent_match:
                if current_agent:
                    role_str = f" ({current_role})" if current_role else ""
                    scope_str = f": {current_scope}" if current_scope else "."
                    agent_docs.append(f"- **`{current_agent}`**{role_str}{scope_str}")
                current_agent = agent_match.group(1)
                current_role = ""
                current_scope = ""
                continue
            
            role_match = re.match(r'^\s\s\s\srole:\s*(.*)', line)
            if role_match:
                current_role = role_match.group(1).strip()
                continue
                
            scope_match = re.match(r'^\s\s\s\sscope:\s*(.*)', line)
            if scope_match:
                current_scope = scope_match.group(1).strip()
                continue

        if current_agent:
            role_str = f" ({current_role})" if current_role else ""
            scope_str = f": {current_scope}" if current_scope else "."
            agent_docs.append(f"- **`{current_agent}`**{role_str}{scope_str}")
            
    return "\n".join(agent_docs)

def update_readme(arms_root, agent_docs):
    readme_path = os.path.join(arms_root, "README.md")
    if not os.path.exists(readme_path):
        print(f"⚠️ README.md not found at {readme_path}")
        return
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    start_marker = "<!-- AGENT_ROSTER_START -->"
    end_marker = "<!-- AGENT_ROSTER_END -->"
    
    if start_marker in content and end_marker in content:
        print("📝 Automating README.md updates...")
        pattern = f"{start_marker}.*?{end_marker}"
        replacement = f"{start_marker}\n{agent_docs}\n{end_marker}"
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        if new_content != content:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("✅ README.md updated with latest agent roster.")
        else:
            print("ℹ️ README.md is already up to date.")
    else:
        print("⚠️ Markers not found in README.md. Please add <!-- AGENT_ROSTER_START --> and <!-- AGENT_ROSTER_END -->.")

def main():
    parser = argparse.ArgumentParser(description="ARMS Documentation Automator")
    parser.add_argument("--version", action="version", version=f"ARMS Docs {__version__}")
    args = parser.parse_args()

    arms_root = get_arms_root()
    print("🤖 ARMS Documentation Automator")
    agent_docs = get_agent_docs(arms_root)
    update_readme(arms_root, agent_docs)

if __name__ == "__main__":
    main()
