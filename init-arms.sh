#!/bin/bash
# Global ARMS Linker (Plug-in ARMS to any project)

ARMS_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# Check if python3 is available
if command -v python3 >/dev/null 2>&1; then
    python3 "$ARMS_ROOT/init-arms.py" "$@"
else
    echo "⚠️ Python 3 not found. Falling back to legacy shell initialization..."
    # Legacy logic (simplified or preserved)
    # [Rest of the old script logic could go here if we wanted true fallback, 
    # but for this task we are migrating]
    echo "❌ Initialization failed. Please install Python 3."
    exit 1
fi