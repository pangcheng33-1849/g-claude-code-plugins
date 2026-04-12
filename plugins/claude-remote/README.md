# claude-remote

Manage Claude Code `--remote-control` sessions in Terminal.app. Designed for mobile access via remote desktop clients.

## Requirements

- macOS (uses AppleScript to control Terminal.app)
- python3

## Usage

```
/claude-remote start    # Launch a new remote session
/claude-remote stop     # Stop a running session
/claude-remote list     # List active sessions
```

Also supports natural language: "open a claude for remote in my-app", "stop all sessions", etc.

## State

Session state is stored in `~/.claude-remote/sessions/` as individual JSON files. Stale sessions are automatically cleaned up on each invocation.
