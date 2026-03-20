# G-Feishu Plugin

A collection of distributable Feishu/Lark Agent Skills for Claude Code.

## Installation

```bash
# Step 1: Add the marketplace
/plugin marketplace add pangcheng1849/g-claude-code-plugins

# Step 2: Install the plugin
/plugin install g-feishu@g-claude-code-plugins
```

For local development:

```bash
claude --plugin-dir ./plugins/g-feishu
```

## Skills

- `feishu-api-diagnose`
  Diagnose Feishu/Lark API errors, permission issues, object ID problems, and request parameter errors.
- `feishu-auth-and-scopes`
  Obtain tokens, initiate authorization, refresh tokens, and validate whether scopes meet requirements.
- `feishu-bitable-workflow`
  Create and manage Bitable apps, data tables, fields, records, and views.
- `feishu-calendar-workflow`
  Create, query, update, and delete calendar events, and check free/busy time.
- `feishu-doc-workflow`
  Read, create, update, and import Feishu Docs and Wiki, including images, whiteboards, and attachments.
- `feishu-im-workflow`
  Create group chats, send messages, reply, edit/recall messages, manage reactions, and read topics and threads.
- `feishu-search-and-locate`
  Search for users, documents, wikis, and group chats, and locate stable identifiers for downstream workflows.
- `feishu-task-workflow`
  Create, update, query, complete, restore, and delete tasks, and manage task members and reminders.

## Environment Variables

Only 3 environment variables are required:

- `MY_LARK_APP_ID`
- `MY_LARK_APP_SECRET`
- `MY_LARK_EMAIL`

### Quick Setup

Temporary (current shell session):

```bash
export MY_LARK_APP_ID="your App ID"
export MY_LARK_APP_SECRET="your App Secret"
export MY_LARK_EMAIL="your Feishu email"
```

Optional — enables clickable web links for docs and Bitable:

```bash
export MY_LARK_WEB_BASE_URL="https://your-tenant.larkoffice.com"
```

Persistent (add to `~/.zshrc`):

```bash
echo export MY_LARK_APP_ID=your_app_id >> ~/.zshrc
echo export MY_LARK_APP_SECRET=your_app_secret >> ~/.zshrc
echo export MY_LARK_EMAIL=your_email >> ~/.zshrc
source ~/.zshrc
```

**Notes:**
- `MY_LARK_EMAIL` is used for default sharing, meeting attendees, and member authorization.
- `MY_LARK_WEB_BASE_URL` is optional. Without it, doc and Bitable workflows still return stable IDs but won't generate web links.
- `MY_LARK_USER_ACCESS_TOKEN`, `MY_LARK_TENANT_ACCESS_TOKEN`, `FEISHU_AUTH_CACHE_DIR`, and `FEISHU_DOC_TASK_DIR` are internal runtime variables and do not need to be set manually.
- For full variable reference and CLI permission matrix, see:
  - `feishu-auth-and-scopes/references/env-standards.md`
  - `feishu-auth-and-scopes/references/cli-scope-matrix.md`

## Design Principles

- Planning, candidate comparison, and ambiguity resolution are handled by the agent's natural language capabilities.
- Real API execution, structured I/O, and stable command entry points are handled by `scripts/`.
- Cross-skill collaboration is done by skill name — no code-level imports across skills.

## Publishing

- Include this directory as-is when publishing.
- Do not bundle `__pycache__`, `.pyc`, local temp files, or environment-bound IDs.
