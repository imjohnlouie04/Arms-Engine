#!/bin/bash
# Global ARMS Linker (Plug-in ARMS to any project)

# Dynamically resolve ARMS_ROOT as the directory where this script is located
ARMS_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(pwd)

echo "🚀 Plugging ARMS Engine into: $PROJECT_ROOT"

# 1. Create local session folder
mkdir -p .gemini/agent-outputs .gemini/reports .gemini/agents

# 2. Migrate Agents
echo "🤖 Syncing Agents..."
for f in "$ARMS_ROOT/agents"/*.md; do
    if [ -f "$f" ]; then
        name=$(basename "$f")
        # Copy agent file and ensure tools: ["*"] is in frontmatter if missing
        if grep -q "tools:" "$f"; then
            cp "$f" ".gemini/agents/$name"
        else
            # Insert tools: ["*"] after the first ---
            sed '1s/^---$/---\ntools: ["*"]/' "$f" > ".gemini/agents/$name"
        fi
    fi
done

# 3. Write the Environment path so agents find it immediately
cat <<EOF > .gemini/SESSION.md
# ARMS Session Log
Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Environment
- ARMS Root: $ARMS_ROOT
- Project Root: $PROJECT_ROOT
- Execution Mode: Parallel

## Active Skills
- arms-orchestrator (Active)
- ... (Linking skills from Global Engine)

## Active Tasks
| # | Task | Assigned Agent | Active Skill | Status |
|---|------|----------------|--------------|--------|

## Blockers
None
EOF

# 4. Write a base GEMINI.md to .gemini/ if not present
if [ ! -f ".gemini/GEMINI.md" ]; then
    cp "$ARMS_ROOT/GEMINI.md" ".gemini/GEMINI.md"
fi

# 5. Force-link the skills to the CLI
echo "🔗 Linking Skills..."
for d in "$ARMS_ROOT/skills"/*/; do 
  if [ -d "$d" ]; then
    gemini skills link "$d" --consent 2>/dev/null
  fi
done

# 6. Success message
echo "✅ ARMS is now connected. Path set to $ARMS_ROOT"
echo "👉 Refreshing skills context. You can now use sub-agents and ARMS skills."
