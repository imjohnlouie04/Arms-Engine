#!/bin/bash
# Global ARMS Linker (Plug-in ARMS to any project)

# Dynamically resolve ARMS_ROOT as the directory where this script is located
ARMS_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(pwd)

echo "🚀 Plugging ARMS Engine into: $PROJECT_ROOT"

# 1. Create local session folders
mkdir -p .gemini/agent-outputs .gemini/reports .gemini/agents

# 2. Sync Agents
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

# 3. Discover Skills (COMPLETE ROSTER MANDATE)
echo "🔍 Discovering Skills..."
SKILLS_LIST=""
# Sort skills alphabetically to ensure consistent diffs
for d in $(ls -d "$ARMS_ROOT/skills"/*/ | sort); do
    if [ -d "$d" ]; then
        skill_name=$(basename "$d")
        if [ "$skill_name" == "arms-orchestrator" ]; then
            SKILLS_LIST="${SKILLS_LIST}- ${skill_name} [Active]\n"
        else
            SKILLS_LIST="${SKILLS_LIST}- ${skill_name}\n"
        fi
    fi
done

# 4. Update SESSION.md
echo "📄 Updating session log..."
# Preserve existing tasks and blockers if SESSION.md exists
if [ -f ".gemini/SESSION.md" ]; then
    echo "ℹ️ SESSION.md exists. Preserving tasks and blockers..."
    # We use sed to extract from ## Active Tasks to the end of the file
    TASKS_CONTENT=$(sed -n '/## Active Tasks/,$p' .gemini/SESSION.md)
else
    echo "📄 Creating new SESSION.md..."
    TASKS_CONTENT=$(cat <<EOF
## Active Tasks
| # | Task | Assigned Agent | Active Skill | Status |
|---|------|----------------|--------------|--------|

## Completed Tasks
- None

## Blockers
None
EOF
)
fi

# Write the new SESSION.md (Hardened environmental metadata)
cat <<EOF > .gemini/SESSION.md
# ARMS Session Log
Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Environment
- ARMS Root: $ARMS_ROOT
- Project Root: $PROJECT_ROOT
- Execution Mode: Parallel

## Active Skills
$(printf "%b" "$SKILLS_LIST")

$TASKS_CONTENT
EOF

# 5. Write a base GEMINI.md to .gemini/ if not present
if [ ! -f ".gemini/GEMINI.md" ]; then
    cp "$ARMS_ROOT/GEMINI.md" ".gemini/GEMINI.md"
fi

# 6. Force-link the skills to the CLI
echo "🔗 Linking Skills..."
for d in "$ARMS_ROOT/skills"/*/; do 
  if [ -d "$d" ]; then
    gemini skills link "$d" --consent 2>/dev/null
  fi
done

# 7. Success message
echo "✅ ARMS is now connected. Path set to $ARMS_ROOT"
echo "👉 Refreshing skills context. You can now use sub-agents and ARMS skills."