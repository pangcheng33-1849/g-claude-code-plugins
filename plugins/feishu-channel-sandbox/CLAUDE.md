# feishu-channel-sandbox

Sandbox profile templates for [feishu-channel](../feishu-channel). Manages Claude Code's native OS-level sandbox via settings.json.

## Architecture

**No hooks.** This plugin provides a single skill (`sandbox-profile`) that reads/writes `.claude/settings.local.json` to configure Claude Code's built-in sandbox (macOS Seatbelt / Linux bubblewrap).

## Profiles

Three presets in `skills/sandbox-profile/profiles/`:

| Profile | Sandbox | Network | Filesystem |
|---------|---------|---------|------------|
| `default.json` | On, no escape | Feishu domains only | CWD + feishu + /tmp |
| `dev.json` | On, escape ok | All domains | CWD + dev tools |
| `dangerously-open.json` | Off | All | All |

Users can create custom profiles via the skill.

## Key Files

- `skills/sandbox-profile/SKILL.md` — profile management skill
- `skills/sandbox-profile/profiles/*.json` — profile templates
- `skills/sandbox-profile/profiles/*.conf` — legacy hook configs (retained for reference)
