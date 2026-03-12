# example-plugin

An example plugin demonstrating skills, agents, and hooks.

## Installation

```bash
/plugin install example-plugin@g-claude-code-plugins
```

## Features

### Skills

- `/example-plugin:hello` — Greet the user
- `/example-plugin:code-review` — Review code for bugs, security, and performance

### Agents

- `reviewer` — Expert code reviewer, automatically invoked during code review tasks

### Hooks

- `PostToolUse` — Logs a message whenever a file is written or edited

## License

MIT
