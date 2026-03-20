# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A Claude Code **plugin marketplace**. It hosts plugins that users install into Claude Code via:

```bash
/plugin marketplace add pangcheng1849/g-claude-code-plugins
/plugin install g-feishu@g-claude-code-plugins
```

For local development of a single plugin:

```bash
claude --plugin-dir ./plugins/my-plugin
/reload-plugins   # hot-reload after editing, no restart needed
```

## Plugin Structure

Every plugin lives under `plugins/<name>/` and follows this layout:

```
plugins/my-plugin/
├── .claude-plugin/
│   └── plugin.json        # manifest: name, version, skills/agents/hooks paths
├── skills/
│   └── my-skill/
│       └── SKILL.md       # frontmatter (name, description) + skill prompt
├── agents/
│   └── my-agent.md        # frontmatter (name, description) + agent system prompt
└── hooks/
    └── hooks.json         # PostToolUse / other event hooks
```

Registering a new plugin also requires adding an entry to `.claude-plugin/marketplace.json` at the repo root.

## Versioning

Version is stored in two places — both must be updated together when bumping:

- `plugins/<name>/.claude-plugin/plugin.json` → `"version"`
- `.claude-plugin/marketplace.json` → the matching plugin entry's `"version"`

Current versions: `g-feishu` = 1.3.0, `example-plugin` = 1.0.0, `xhs-research` = 1.0.0.

## g-feishu Plugin Architecture

The main plugin. Eight skills, each self-contained under `plugins/g-feishu/skills/<skill-name>/`:

| Skill | Purpose |
|---|---|
| `feishu-auth-and-scopes` | Get/refresh tokens, diagnose scope issues |
| `feishu-im-workflow` | Send/reply/edit messages, upload images/files, manage chats & reactions |
| `feishu-doc-workflow` | Read/create/update/export docs and wikis |
| `feishu-bitable-workflow` | Manage Bitable apps, tables, fields, records |
| `feishu-calendar-workflow` | Create/query/update events, check free/busy |
| `feishu-task-workflow` | Create/update/complete tasks |
| `feishu-search-and-locate` | Search users, docs, chats; resolve stable IDs |
| `feishu-api-diagnose` | Diagnose API errors, invalid IDs, permission failures |

**Skill internals pattern** (used by `feishu-im-workflow`, others similar):

- `SKILL.md` — skill prompt loaded by Claude Code; contains the full workflow guide
- `scripts/feishu_*_helper.py` — CLI entry point, registers argparse subcommands
- `scripts/feishu_*_runtime/` — split modules (e.g. `common.py`, `message_ops.py`, `media_ops.py`)
- `references/` — reference docs loaded by the skill prompt
- `examples/sample-prompts.md` — example user prompts

All scripts use **Python stdlib only** (no third-party deps). HTTP calls go through `urllib.request`; multipart uploads are built manually.

**Cross-skill collaboration rule**: skills call each other by name only (`feishu-auth-and-scopes`, `feishu-search-and-locate`, etc.) — never via code-level imports across skill directories.

## Environment Variables (g-feishu)

Minimum required (set by the user):

```bash
export MY_LARK_APP_ID="..."
export MY_LARK_APP_SECRET="..."
export MY_LARK_EMAIL="..."          # used as default identity for sharing/members
```

Optional:

```bash
export MY_LARK_WEB_BASE_URL="https://<tenant>.larkoffice.com"  # enables clickable doc links
```

Internal runtime variables (passed between skills, not set by users): `MY_LARK_TENANT_ACCESS_TOKEN`, `MY_LARK_USER_ACCESS_TOKEN`, `FEISHU_AUTH_CACHE_DIR`, `FEISHU_DOC_TASK_DIR`.

## Adding a New Skill to g-feishu

1. Create `plugins/g-feishu/skills/<skill-name>/SKILL.md` with frontmatter (`name`, `description`) and the skill prompt.
2. Add a `scripts/` directory with a `feishu_*_helper.py` CLI entry and a `feishu_*_runtime/` module package if needed.
3. Use only `MY_LARK_*` env variable names — never the legacy `FEISHU_EMAIL` / `LARK_EMAIL` aliases.
4. Bump `version` in both `plugin.json` and `marketplace.json`.
