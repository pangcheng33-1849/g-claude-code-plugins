# g-claude-code-plugins

A Claude Code plugins marketplace.

This repository can be used in two ways:

- Install full plugins with `/plugin install`
- Install raw skills directly with `npx skills`

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
/plugin install example-plugin@g-claude-code-plugins
```

Use `/plugin install` when you want the full plugin package, including plugin metadata and any bundled agents or hooks.

### Install skills with `npx skills`

If you only want the raw `SKILL.md` content, you can install skills directly with `npx skills`.

Recommended: use the repository URL directly with `npx skills add` for interactive installation. The CLI will discover nested skills in this repo and let you choose what to install.

```bash
# Recommended: interactive installation
npx skills add https://github.com/pangcheng1849/g-claude-code-plugins

# Install one skill to Codex
npx skills add https://github.com/pangcheng1849/g-claude-code-plugins -a codex -s feishu-doc-workflow

# Install all repository skills to Claude Code
npx skills add https://github.com/pangcheng1849/g-claude-code-plugins -a claude-code -s '*'

# List available skills without installing
npx skills add https://github.com/pangcheng1849/g-claude-code-plugins --list
```

## Available Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| [example-plugin](./plugins/example-plugin) | An example plugin with skill, agent, and hook | 1.0.0 |
| [g-feishu](./plugins/g-feishu) | Feishu (Lark) integration skills for Claude Code | 1.3.0 |
| [feishu-channel](./plugins/feishu-channel) | Connect Claude Code to Feishu via WebSocket — chat, access control, pairing auth | 1.0.0 |
| [feishu-channel-sandbox](./plugins/feishu-channel-sandbox) | Optional security sandbox for feishu-channel — file/command whitelisting with glob patterns | 1.0.0 |
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
