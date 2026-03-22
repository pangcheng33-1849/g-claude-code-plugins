# @ben1849/feishu-channel

[feishu-channel](https://github.com/pangcheng1849/g-claude-code-plugins/tree/main/plugins/feishu-channel) 的配套 CLI 工具 — 管理 Claude Code 内置 sandbox 的安全配置。

## 快速开始

```bash
npx @ben1849/feishu-channel sandbox
```

交互式菜单，箭头键选择，回车确认：

```
┌  🔒 Sandbox Profile Manager
│
◇  Current status
│  Profile:  (none)
│  Settings: .claude/settings.local.json
│
◆  Select action
│  ● Apply profile
│  ○ Show current config
│  ○ Show a profile template
│  ○ Reset
│  ○ Create custom profile
│  ○ Delete custom profile
└
```

也支持直接执行：

```bash
npx @ben1849/feishu-channel sandbox apply default   # 应用安全模式
npx @ben1849/feishu-channel sandbox apply dev       # 应用开发模式
npx @ben1849/feishu-channel sandbox reset           # 移除配置
npx @ben1849/feishu-channel sandbox show            # 查看当前配置
npx @ben1849/feishu-channel sandbox list            # 列出可用 profile
```

配置写入当前项目的 `.claude/settings.local.json`（个人、gitignored），Claude Code 自动重载。

**注意**：必须在启动 Claude Code 的同一目录下执行。

## 预置模板

### `default` — 安全模式

推荐飞书频道日常使用。

| 项目 | 配置 |
|------|------|
| Sandbox | 开启，关闭逃逸口 |
| 权限模式 | `dontAsk`（allow 列表外静默拒绝） |
| 文件写入 | 仅 CWD + `~/.claude/channels/feishu` + `~/.feishu-auth-cache` + `/tmp` |
| 文件读取 | 禁止 `~/.ssh`、`~/.aws`、`~/.gnupg` |
| 网络 | 常见 TLD 放行（`*.com`、`*.cn` 等） |
| 命令 | 只读命令 + skill 脚本 + git 只读 + MCP 工具 |
| 禁止 | `curl`/`wget`/`rm -rf`/`git push`/修改 settings |

### `dev` — 开发模式

开发调试使用，权限更宽松。

| 项目 | 配置 |
|------|------|
| Sandbox | 开启，允许逃逸口 |
| 权限模式 | `dontAsk` |
| 文件写入 | CWD + 包管理器缓存 + 开发工具目录 |
| 网络 | 常见 TLD 放行 |
| 命令 | git/npm/pip/cargo/curl/docker/make 等全开 + MCP 工具 |
| 禁止 | `rm -rf /`/修改 settings |

### `dangerously-open` — 无限制

关闭 sandbox + `bypassPermissions`。等同 `--dangerously-skip-permissions`。仅在信任环境使用。

## 自定义模板

```bash
# 基于 dev 创建
npx @ben1849/feishu-channel sandbox create myprofile dev

# 编辑 ~/.claude/channels/feishu/sandbox-profile/profiles/myprofile.json

# 应用
npx @ben1849/feishu-channel sandbox apply myprofile

# 删除（如有项目在用，需 --force）
npx @ben1849/feishu-channel sandbox delete myprofile
```

预置模板（default/dev/dangerously-open）不可删除。

## 工作原理

- 利用 Claude Code 内置 OS 级 sandbox（macOS Seatbelt / Linux bubblewrap）
- 配置写入 `.claude/settings.local.json`，包含 `sandbox` + `permissions` 规则
- 切换 profile 时**先删后加**：精确删除旧 profile 的规则，保留用户手动添加的规则
- 每个项目独立追踪当前 profile（`~/.claude/channels/feishu/sandbox-profile/active/`）
- reset 时兜底清理：无 active 记录也能清除 sandbox 配置

## 许可

MIT
