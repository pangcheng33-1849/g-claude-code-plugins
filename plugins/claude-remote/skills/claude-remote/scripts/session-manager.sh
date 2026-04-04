#!/bin/bash
# Claude Remote Session Manager
# Manages Claude Code --remote-control sessions in Terminal.app
# State: ~/.claude-remote/sessions/<id>.json

set -euo pipefail

STATE_DIR="$HOME/.claude-remote/sessions"
mkdir -p "$STATE_DIR"

# Generate short random ID
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

cmd_create() {
  local dir="${1:?Usage: session-manager.sh create <directory> [extra-flags...]}"
  dir=$(cd "$dir" 2>/dev/null && pwd) || { echo "ERROR: Directory not found: $dir"; exit 1; }
  shift
  local extra_flags="$*"

  # Default to bypassPermissions if user didn't specify --permission-mode
  if ! echo "$extra_flags" | grep -q "\-\-permission-mode"; then
    extra_flags="--permission-mode bypassPermissions $extra_flags"
  fi

  # Open Terminal and run claude
  local wid
  wid=$(osascript -e "tell application \"Terminal\" to do script \"cd '$dir' && claude --remote-control $extra_flags\"" 2>&1)
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

  cat > "$STATE_DIR/${sid}.json" <<EOF
{
  "id": "$sid",
  "window_id": $wid,
  "directory": "$dir",
  "started_at": "$now"
}
EOF

  echo "{\"id\":\"$sid\",\"window_id\":$wid,\"directory\":\"$dir\",\"started_at\":\"$now\"}"
}

cmd_list() {
  local found=0
  echo "["
  local first=1
  for f in "$STATE_DIR"/*.json; do
    [ -f "$f" ] || continue
    if [ $first -eq 1 ]; then
      first=0
    else
      echo ","
    fi
    cat "$f"
    found=1
  done
  echo "]"
  if [ $found -eq 0 ]; then
    # Output was already "[]"
    :
  fi
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
    wid=$(python3 -c "import json; print(json.load(open('$f'))['window_id'])" 2>/dev/null) || { rm -f "$f"; removed=$((removed + 1)); continue; }
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
  wid=$(python3 -c "import json; print(json.load(open('$f'))['window_id'])")

  # Close the window. Terminal shows a "terminate process?" dialog if claude
  # is still running — we click "终止" (Terminate) via System Events.
  osascript <<APPLESCRIPT
    tell application "Terminal"
      activate
      set index of window id $wid to 1
      close window id $wid
    end tell
    delay 0.5
    tell application "System Events"
      tell process "Terminal"
        try
          -- Click "终止" (Terminate) button on the confirmation sheet
          click button "终止" of sheet 1 of window 1
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
    sid=$(python3 -c "import json; print(json.load(open('$f'))['id'])")
    cmd_stop "$sid" 2>/dev/null || true
    stopped=$((stopped + 1))
  done
  echo "Stopped $stopped session(s)"
}

# Main dispatch
case "${1:-help}" in
  create)    cmd_create "${2:-}" ;;
  list)      cmd_list ;;
  list-dirs) cmd_list_dirs ;;
  cleanup)   cmd_cleanup ;;
  stop)      cmd_stop "${2:-}" ;;
  stop-all)  cmd_stop_all ;;
  help)
    echo "Usage: session-manager.sh <command> [args]"
    echo "Commands: create <dir>, list, list-dirs, cleanup, stop <id>, stop-all"
    ;;
  *)
    echo "Unknown command: $1"
    exit 1
    ;;
esac
