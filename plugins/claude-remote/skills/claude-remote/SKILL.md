---
name: claude-remote
description: Manage **remote-control** Claude Code sessions (i.e. `claude --remote-control`, NOT regular local sessions) running in Terminal.app — start, stop, list, or resume them for mobile / remote desktop access. Triggers on "start/open/launch a remote claude", "stop/kill remote session", "list remote sessions", "continue last remote conversation in <dir>".
---

# Claude Remote Session Manager

Manage Claude Code `--remote-control` sessions running in Terminal.app. Designed for remote desktop clients that let users control Claude Code from mobile devices.

## State Directory

All session state lives in `~/.claude-remote/`. On every skill invocation, always run the cleanup script first to sync state with reality.

## Scripts

This skill bundles a session manager script. All paths below are relative to the skill directory:

- `scripts/session-manager.sh` — handles create, list, remove, cleanup, and stop operations

Get the script path:
```bash
SKILL_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
# Or just use the known absolute path after reading it from the skill location
```

## Workflow

### On Every Invocation

Before doing anything else, run cleanup to remove stale entries:

```bash
bash <skill-dir>/scripts/session-manager.sh cleanup
```

This checks each recorded session's Terminal window still exists and removes dead entries. If any sessions were cleaned up, tell the user (e.g., "2 stale sessions were cleaned up — their Terminal windows were closed outside this tool").

### Determine Intent

Parse what the user wants:

| Intent | Triggers |
|--------|----------|
| **start** | "start", "open", "launch", "new session", "remote control" |
| **stop** | "stop", "close", "kill", "shut down", "exit" |
| **list** | "list", "status", "show", "which sessions", "what's running" |

If ambiguous, ask.

### Start Flow

1. **Try to infer from context first.** If the user's message already contains a directory name or path (e.g., "launch claude in ~/Workspace/my-app"), use it directly — skip the directory picker. Also detect any options mentioned naturally (e.g., "with opus model" → `--model opus`).

2. Only if the directory is unclear, list directories under `~/Workspace`:
   ```bash
   bash <skill-dir>/scripts/session-manager.sh list-dirs
   ```
   Present as a numbered list via `AskUserQuestion`. Include an option to create a new directory. Note: `~/Workspace` is the default root; if it doesn't exist, ask the user for their workspace path.

3. If creating new:
   ```bash
   mkdir -p ~/Workspace/<new-dir-name>
   ```

4. Common options (only ask if not already inferred from context):

   | Option | Flag | Default | Example |
   |--------|------|---------|---------|
   | Permission mode | `--permission-mode <mode>` | `bypassPermissions` | `--permission-mode auto` |
   | Model | `--model <model>` | (user default) | `--model sonnet` or `--model opus` |
   | Session name | `-n <name>` | (auto) | `-n "mobile-debug"` |
   | Effort level | `--effort <level>` | (user default) | `--effort high` |
   | Worktree | `-w, --worktree [name]` | — | Create a git worktree for the session |
   If the user doesn't specify any, use defaults (no extra flags).

5. Launch the session:
   ```bash
   RESULT=$(bash <skill-dir>/scripts/session-manager.sh create <directory-path> [extra-flags...])
   ```
   This opens Terminal.app via AppleScript, runs `claude --permission-mode bypassPermissions --remote-control [extra-flags]` in the chosen directory, and records the session.

6. Report the session ID, directory, and window ID to the user. Mention they can now connect via their remote control client.

### Continue (Resume Last Conversation)

When the user wants to pick up where they left off in a directory (triggers: "continue", "resume", "接着上次", "继续上次的对话"), pass the `-c` flag to the start flow. It tells `claude` to continue the most recent conversation in that directory instead of starting a fresh one.

```bash
bash <skill-dir>/scripts/session-manager.sh create <directory-path> -c [other-flags...]
```

Notes:
- `-c` only resumes the **most recent** conversation in the chosen directory. If the user wants a specific older conversation, they'll need to use `claude --resume` interactively instead.
- Combine freely with other flags (`--model`, `-n`, `-w`, etc.).
- If no prior conversation exists in that directory, `claude` will fall back to a new session.

### Stop Flow

1. Get active sessions:
   ```bash
   bash <skill-dir>/scripts/session-manager.sh list
   ```

2. If no sessions: tell the user there's nothing to stop.

3. If one session: confirm with user, then stop it.

4. If multiple: present numbered list via `AskUserQuestion`, let user pick one or "all".

5. Stop the selected session(s):
   ```bash
   bash <skill-dir>/scripts/session-manager.sh stop <session-id>
   # or stop all:
   bash <skill-dir>/scripts/session-manager.sh stop-all
   ```

6. Report what was stopped.

### List Flow

1. Run:
   ```bash
   bash <skill-dir>/scripts/session-manager.sh list
   ```

2. Present a formatted table:
   ```
   #  Session ID   Directory              Started        Window
   1  a1b2c3d4   ~/Workspace/my-app     10:30 today    98905
   2  e5f6a7b8   ~/Workspace/api-work   09:15 today    98820
   ```

3. If no sessions: "No active remote sessions."

## Examples

| User says | Resolved action |
|-----------|-----------------|
| "start a remote claude in my-app" | `create ~/Workspace/my-app` |
| "launch claude in ~/code/api with opus" | `create ~/code/api --model opus` |
| "接着上次的 my-app 继续" | `create ~/Workspace/my-app -c` |
| "open a remote session in a worktree of api-work" | `create ~/Workspace/api-work -w` |
| "stop the my-app session" | `list` → match by directory → `stop <id>` |
| "kill all remote sessions" | `stop-all` |
| "what's running?" | `list` → render as table |

## Important Notes

- The script uses `osascript` (AppleScript) to control Terminal.app — this only works on macOS.
- Each session opens a **new Terminal window** (not a tab) for isolation.
- Stop uses Terminal's native "terminate process" dialog to shut down Claude Code, then closes the window.
- Session state is stored as individual JSON files in `~/.claude-remote/sessions/` — one file per session for atomicity.
