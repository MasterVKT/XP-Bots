#!/bin/sh
# POSIX launcher for agent_lifecycle.py (Linux, macOS, Git Bash on Windows).
# Usage: sh .agents/hooks/invoke-agent-hook.sh <event>-<tool>
# Standard input is inherited unchanged by the engine (bytes, no text conversion).
# Interpreter order: $XPBOTS_PYTHON, repository or parent venv, python3.13, python3, python.
# Fails open: without a compatible Python 3.13+, prints a neutral {} and exits 0.

mode="$1"
hooks_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$hooks_dir/../.." && pwd)
engine="$hooks_dir/agent_lifecycle.py"

compatible() {
    "$@" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)' >/dev/null 2>&1 </dev/null
}

for candidate in "${XPBOTS_PYTHON:-}" "$root/.venv/bin/python" "$root/.venv/Scripts/python.exe" \
                 "$root/../.venv/bin/python" "$root/../.venv/Scripts/python.exe" python3.13 python3 python; do
    [ -n "$candidate" ] || continue
    case "$candidate" in
        */*) [ -x "$candidate" ] || continue ;;
        *) command -v "$candidate" >/dev/null 2>&1 || continue ;;
    esac
    if compatible "$candidate"; then
        exec "$candidate" -B "$engine" --mode "$mode"
    fi
done

state_dir="${XPBOTS_LIFECYCLE_STATE_DIR:-${TMPDIR:-/tmp}/xp-bots-agent-lifecycle}"
mkdir -p "$state_dir" 2>/dev/null && \
    printf '%s launcher: no Python 3.13+ interpreter found (mode %s)\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$mode" \
    >> "$state_dir/xp-bots-lifecycle-errors.log" 2>/dev/null
printf '{}'
exit 0
