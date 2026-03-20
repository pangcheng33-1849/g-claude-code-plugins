# g-claude-code-plugins

A Claude Code plugins marketplace.

## Usage

### Add this marketplace

```bash
/plugin marketplace add pangcheng1849/g-claude-code-plugins
```

Or via local path (for development):

```bash
/plugin marketplace add ./
```

### Install a plugin

```bash
/plugin install xhs-research@g-claude-code-plugins
```

### Install only one skill

If you only want a single skill instead of the whole plugin, you can also use the Agent Skills CLI:

```bash
# Install only the xhs-research skill
npx skills add pangcheng1849/g-claude-code-plugins --skill xhs-research

# Install only the xhs-research skill into Claude Code
npx skills add pangcheng1849/g-claude-code-plugins --skill xhs-research -a claude-code
```

## Available Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| [example-plugin](./plugins/example-plugin) | An example plugin with skill, agent, and hook | 1.0.0 |
| [g-feishu](./plugins/g-feishu) | Feishu (Lark) integration skills for Claude Code | 1.3.0 |
| [xhs-research](./plugins/xhs-research) | Xiaohongshu reputation research workflow for Claude Code | 1.0.0 |

## Plugin Structure

```
plugins/
└── my-plugin/
    ├── .claude-plugin/
    │   └── plugin.json       # Plugin manifest
    ├── skills/
    │   └── my-skill/
    │       └── SKILL.md      # Skill definition
    ├── agents/
    │   └── my-agent.md       # Agent definition
    └── hooks/
        └── hooks.json        # Event hooks
```

## Adding a New Plugin

1. Create a directory under `plugins/`
2. Add `.claude-plugin/plugin.json`
3. Add skills, agents, hooks as needed
4. Register it in `.claude-plugin/marketplace.json`

## Local Development

Load a single plugin directly for development:

```bash
claude --plugin-dir ./plugins/my-plugin
```

After editing files, reload without restarting:

```bash
/reload-plugins
```

## Contributing

Submit a PR with your plugin following the structure above.
