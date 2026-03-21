# g-claude-code-plugins

A Claude Code **plugin marketplace**. Each plugin lives under `plugins/<name>/`.

## Development

```bash
# Install from marketplace
/plugin marketplace add pangcheng1849/g-claude-code-plugins
/plugin install <name>@g-claude-code-plugins

# Local development
claude --plugin-dir ./plugins/my-plugin
/reload-plugins   # hot-reload after editing
```

## Plugin Structure

```
plugins/my-plugin/
├── .claude-plugin/
│   └── plugin.json        # manifest: name, version, skills/agents/hooks paths
├── skills/
│   └── my-skill/
│       └── SKILL.md       # frontmatter (name, description) + skill prompt
├── agents/
│   └── my-agent.md        # agent system prompt
├── hooks/
│   └── hooks.json         # event hooks
└── CLAUDE.md              # plugin-specific context (optional)
```

Registering a new plugin also requires adding an entry to `.claude-plugin/marketplace.json` at the repo root.

## Versioning

Version is stored in two places — both must be updated together:

- `plugins/<name>/.claude-plugin/plugin.json` → `"version"`
- `.claude-plugin/marketplace.json` → the matching plugin entry's `"version"`

## Adding a New Plugin

1. Create `plugins/<name>/` with the structure above
2. Add entry to `.claude-plugin/marketplace.json`
3. Plugin-specific architecture docs go in the plugin's own `CLAUDE.md`, not here
