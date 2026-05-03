#!/bin/bash
# Global ARMS Linker (Plug-in ARMS to any project)

CALLER_PWD=$PWD
ARMS_ROOT=${BASH_SOURCE[0]}
case "$ARMS_ROOT" in
    */*)
        ARMS_ROOT=${ARMS_ROOT%/*}
        ;;
    *)
        ARMS_ROOT=.
        ;;
esac
cd "$ARMS_ROOT" || exit 1
ARMS_ROOT=$PWD
cd "$CALLER_PWD" || exit 1

# Check if python3 is available
if command -v python3 >/dev/null 2>&1; then
    if [ -n "${PYTHONPATH:-}" ]; then
        export PYTHONPATH="$ARMS_ROOT:$PYTHONPATH"
    else
        export PYTHONPATH="$ARMS_ROOT"
    fi
    exec python3 -m arms_engine.init_arms "$@"
else
    echo "⚠️ Python 3 not found. Falling back to legacy shell initialization..."
    # Legacy logic (simplified or preserved)
    # [Rest of the old script logic could go here if we wanted true fallback, 
    # but for this task we are migrating]
    echo "❌ Initialization failed. Please install Python 3."
    exit 1
fi
