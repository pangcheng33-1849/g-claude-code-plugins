# g-claude-code-plugins

A Claude Code plugins marketplace.

## Usage

### Add this marketplace

```bash
/plugin marketplace add pangcheng33-1849/g-claude-code-plugins
```

Or via local path (for development):

```bash
/plugin marketplace add ./
```

### Install a plugin

```bash
/plugin install example-plugin@g-claude-code-plugins
```

## Available Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| [example-plugin](./plugins/example-plugin) | An example plugin with skill, agent, and hook | 1.0.0 |

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
