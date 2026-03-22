# g-feishu

Feishu (Lark) integration — 9 self-contained skills under `skills/<skill-name>/`.

## Skills

| Skill | Purpose |
|---|---|
| `feishu-auth-and-scopes` | Get/refresh tokens, diagnose scope issues |
| `feishu-im-workflow` | Send/reply/edit messages, upload images/files, manage chats & reactions |
| `feishu-doc-workflow` | Read/create/update/export docs and wikis |
| `feishu-bitable-workflow` | Manage Bitable apps, tables, fields, records |
| `feishu-sheets-workflow` | Create/read/write spreadsheets, find/replace cells |
| `feishu-calendar-workflow` | Create/query/update events, manage attendees, check free/busy |
| `feishu-task-workflow` | Create/update/complete tasks |
| `feishu-search-and-locate` | Search users, docs, chats, messages; resolve stable IDs |
| `feishu-api-diagnose` | Diagnose API errors, invalid IDs, permission failures |

## Skill Internals

- `SKILL.md` — skill prompt with frontmatter
- `scripts/feishu_*_helper.py` — CLI entry point (argparse subcommands)
- `scripts/feishu_*_runtime/` — split modules (e.g. `common.py`, `message_ops.py`)
- `references/` — reference docs loaded by skill prompt
- All scripts use **Python stdlib only** (no third-party deps)

## Cross-Skill Rule

Skills call each other by name only — never via code-level imports across skill directories.

## Environment Variables

```bash
export MY_LARK_APP_ID="..."
export MY_LARK_APP_SECRET="..."
export MY_LARK_EMAIL="..."                                    # default identity
export MY_LARK_WEB_BASE_URL="https://<tenant>.larkoffice.com" # optional, enables doc links
```

Token handling: all workflow scripts require explicit `--user-access-token` or `--tenant-access-token`. Use skill `feishu-auth-and-scopes` (`resolve-token`) to obtain tokens — do not rely on environment variables for token passing.

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with frontmatter
2. Add `scripts/` with `feishu_*_helper.py` CLI entry
3. Use only `MY_LARK_*` env variable names
4. Bump version in `plugin.json` and root `marketplace.json`
