#!/bin/bash
# Claude Remote Session Manager
# Manages Claude Code --remote-control sessions in Terminal.app
# State: ~/.claude-remote/sessions/<id>.json
# Dependencies: osascript (macOS), python3 (for JSON handling)

set -euo pipefail

STATE_DIR="$HOME/.claude-remote/sessions"
mkdir -p "$STATE_DIR"

# Verify python3 is available
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required but not found"; exit 1; }

# Generate short random ID (8 hex chars)
gen_id() {
  head -c 4 /dev/urandom | xxd -p
}

# Get all Terminal window IDs
get_terminal_windows() {
  osascript -e 'tell application "Terminal" to get id of every window' 2>/dev/null | tr ',' '\n' | tr -d ' ' || echo ""
}

# Check if a specific window ID still exists
window_exists() {
  local wid="$1"
  get_terminal_windows | grep -q "^${wid}$"
}

# Read a field from a session JSON file safely (no string interpolation)
read_json_field() {
  local file="$1" field="$2"
  python3 -c "import json,sys; print(json.load(sys.stdin)['$field'])" < "$file"
}

# Write session JSON safely with proper escaping
write_session_json() {
  local file="$1" sid="$2" wid="$3" dir="$4" started="$5"
  python3 -c "
import json, sys
json.dump({
    'id': sys.argv[1],
    'window_id': int(sys.argv[2]),
    'directory': sys.argv[3],
    'started_at': sys.argv[4]
}, open(sys.argv[5], 'w'), indent=2)
" "$sid" "$wid" "$dir" "$started" "$file"
}

cmd_create() {
  local dir="${1:?Usage: session-manager.sh create <directory> [extra-flags...]}"
  dir=$(cd "$dir" 2>/dev/null && pwd) || { echo "ERROR: Directory not found: $dir"; exit 1; }
  shift

  # Collect extra flags as an array to preserve argument boundaries
  local -a flags=("$@")

  # Default to bypassPermissions if user didn't specify --permission-mode
  local has_perm=0
  for f in "${flags[@]+"${flags[@]}"}"; do
    [[ "$f" == "--permission-mode" ]] && has_perm=1
  done
  if [ "$has_perm" -eq 0 ]; then
    flags=("--permission-mode" "bypassPermissions" "${flags[@]+"${flags[@]}"}")
  fi

  # Build the command string safely: escape single quotes in dir and flags
  local escaped_dir="${dir//\'/\'\\\'\'}"
  local cmd="cd '${escaped_dir}' && claude --remote-control"
  for f in "${flags[@]+"${flags[@]}"}"; do
    local escaped_f="${f//\'/\'\\\'\'}"
    cmd="$cmd '${escaped_f}'"
  done

  # Open Terminal with default profile
  local wid
  wid=$(osascript -e "tell application \"Terminal\" to do script \"$cmd\"" 2>&1)
  # Extract window ID from "tab 1 of window id NNNNN"
  wid=$(echo "$wid" | grep -o 'window id [0-9]*' | grep -o '[0-9]*')

  if [ -z "$wid" ]; then
    echo "ERROR: Failed to open Terminal window"
    exit 1
  fi

  local sid
  sid=$(gen_id)
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  write_session_json "$STATE_DIR/${sid}.json" "$sid" "$wid" "$dir" "$now"

  # Output result as JSON (via python3 for safe escaping)
  python3 -c "
import json, sys
print(json.dumps({
    'id': sys.argv[1],
    'window_id': int(sys.argv[2]),
    'directory': sys.argv[3],
    'started_at': sys.argv[4]
}))
" "$sid" "$wid" "$dir" "$now"
}

cmd_list() {
  python3 -c "
import json, glob, sys, os
sessions = []
for f in sorted(glob.glob(os.path.join(sys.argv[1], '*.json'))):
    try:
        sessions.append(json.load(open(f)))
    except (json.JSONDecodeError, KeyError):
        pass
print(json.dumps(sessions, indent=2))
" "$STATE_DIR"
}

cmd_list_dirs() {
  local i=1
  for d in "$HOME"/Workspace/*/; do
    [ -d "$d" ] || continue
    local name
    name=$(basename "$d")
    echo "$i) $name"
    i=$((i + 1))
  done
  echo "$i) [Create new directory]"
}

cmd_cleanup() {
  local windows
  windows=$(get_terminal_windows)
  local removed=0
  for f in "$STATE_DIR"/*.json; do
    [ -f "$f" ] || continue
    local wid
    wid=$(read_json_field "$f" "window_id" 2>/dev/null) || { rm -f "$f"; removed=$((removed + 1)); continue; }
    if ! echo "$windows" | grep -q "^${wid}$"; then
      rm -f "$f"
      removed=$((removed + 1))
    fi
  done
  echo "Cleaned up $removed stale session(s)"
}

cmd_stop() {
  local sid="${1:?Usage: session-manager.sh stop <session-id>}"
  local f="$STATE_DIR/${sid}.json"
  [ -f "$f" ] || { echo "ERROR: Session $sid not found"; exit 1; }

  local wid
  wid=$(read_json_field "$f" "window_id")

  # Check if window is already gone
  if ! window_exists "$wid"; then
    rm -f "$f"
    echo "Session $sid was already terminated (window closed)"
    return 0
  fi

  # Close the window. Terminal shows a "terminate process?" dialog if a process
  # is running. We click the destructive button on the sheet (locale-independent
  # via button index). After the process is killed, the window may linger in
  # "[Process completed]" state — we send a second close to handle that.
  osascript <<APPLESCRIPT
    tell application "Terminal"
      activate
      set index of window id $wid to 1
      close window id $wid
    end tell
    delay 0.8
    tell application "System Events"
      tell process "Terminal"
        try
          click button 2 of sheet 1 of window 1
        end try
      end tell
    end tell
    -- Wait for process termination, then close the lingering window
    delay 1.5
    tell application "Terminal"
      try
        close window id $wid
      end try
    end tell
    delay 0.5
    tell application "System Events"
      tell process "Terminal"
        try
          click button 2 of sheet 1 of window 1
        end try
      end tell
    end tell
APPLESCRIPT

  rm -f "$f"
  echo "Stopped session $sid (window $wid)"
}

cmd_stop_all() {
  local stopped=0
  for f in "$STATE_DIR"/*.json; do
    [ -f "$f" ] || continue
    local sid
    sid=$(read_json_field "$f" "id")
    cmd_stop "$sid" 2>/dev/null || true
    stopped=$((stopped + 1))
  done
  echo "Stopped $stopped session(s)"
}

# Main dispatch
case "${1:-help}" in
  create)    shift; cmd_create "$@" ;;
  list)      cmd_list ;;
  list-dirs) cmd_list_dirs ;;
  cleanup)   cmd_cleanup ;;
  stop)      cmd_stop "${2:-}" ;;
  stop-all)  cmd_stop_all ;;
  help)
    echo "Usage: session-manager.sh <command> [args]"
    echo "Commands: create <dir> [flags...], list, list-dirs, cleanup, stop <id>, stop-all"
    ;;
  *)
    echo "Unknown command: $1"
    exit 1
    ;;
esac
