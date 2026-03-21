# feishu-channel-sandbox

Optional security sandbox for [feishu-channel](../feishu-channel). Three-layer defense via PreToolUse hooks.

## Architecture

**Bash command check** (`hooks/sandbox-bash.sh`):
1. Subshell detection — block `$()`, `` ` ``, `<()`, `>()`
2. Glob pattern whitelist — each pipe/chain segment checked against `sandbox-bash.conf`
3. Path whitelist — file paths in commands checked against `sandbox.conf`

**File access check** (`hooks/sandbox-file.sh`): path validated against `sandbox.conf`.

**Config syntax**: lines without glob chars (`*`, `?`, `[`) → prefix match; with glob chars → bash `[[ == $PATTERN ]]` glob match. `~` expanded to `$HOME`.

## Key Files

- `hooks/sandbox-bash.sh` — command validation
- `hooks/sandbox-file.sh` — file path validation
- `hooks/setup.sh` — SessionStart initialization
- `skills/sandbox-profile/` — profile management (default/dev/custom)
- `skills/sandbox-profile/profiles/` — config files (`{name}-bash.conf` + `{name}-sandbox.conf`)

## Testing

```bash
bash tests/test-sandbox.sh   # 227 automated tests
```

See `tests/CLAUDE.md` for test structure and how to add cases.
