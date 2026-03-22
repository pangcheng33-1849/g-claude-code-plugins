# feishu-channel-sandbox

可选的安全配置插件，配合 [feishu-channel](../feishu-channel) 使用。通过 Claude Code 内置的 OS 级 sandbox（macOS Seatbelt / Linux bubblewrap）实现文件系统和网络隔离。

## 安装

```bash
/plugin install feishu-channel-sandbox@g-claude-code-plugins
```

## 快速开始

安装后使用 skill 应用配置模板：

```
/sandbox-profile apply default     # 安全模式
/sandbox-profile apply dev         # 开发模式
/sandbox-profile apply dangerously-open  # 无限制
```

配置写入 `.claude/settings.local.json`（个人、gitignored），立即生效。

## 预置模板

### `default` — 安全模式

适合飞书频道日常使用。sandbox 开启，bash 自动放行（无弹窗），文件系统和网络严格限制。

- **文件写入**：仅允许工作目录 + `~/.claude/channels/feishu` + `~/.claude/plugins` + `/tmp`
- **文件读取**：禁止 `~/.ssh`、`~/.aws`、`~/.gnupg`
- **网络**：飞书域名自动放行，其他域名首次弹窗批准后记住
- **命令**：仅允许只读命令 + skill 脚本执行 + git 只读
- **逃逸口**：关闭（`allowUnsandboxedCommands: false`）

### `dev` — 开发模式

适合开发调试。sandbox 开启但限制放宽。

- **文件写入**：额外允许 `/usr/local`、包管理器缓存（npm/bun/cargo）、git/ssh 配置
- **网络**：全部域名放开
- **命令**：允许所有常见开发工具（git/npm/pip/cargo/curl/docker/make 等）
- **逃逸口**：开启；docker/docker-compose 排除在 sandbox 外

### `dangerously-open` — 无限制模式

完全关闭 sandbox 和权限检查。等同 `--dangerously-skip-permissions`。

> **警告**：仅在信任环境（如容器、VM）中使用。

## 技能命令

```
/sandbox-profile                   # 查看可用模板和当前配置
/sandbox-profile show default      # 查看模板内容
/sandbox-profile show current      # 查看当前 sandbox 配置
/sandbox-profile apply <name>      # 应用模板到 settings.local.json
/sandbox-profile apply <name> --shared  # 应用到 settings.json（团队共享）
/sandbox-profile reset             # 移除 sandbox 配置
/sandbox-profile create <name> dev # 基于 dev 创建自定义模板
/sandbox-profile delete <name>     # 删除自定义模板
```

## 工作原理

本插件不使用 hook 拦截。它只是管理 Claude Code 原生 sandbox 的 `settings.json` 配置：

1. **文件系统隔离**：OS 级（macOS Seatbelt / Linux bubblewrap），子进程也无法逃逸
2. **网络隔离**：通过代理限制域名访问
3. **权限规则**：`permissions.allow`/`deny` 控制 Claude 可用的命令
4. **自动放行**：sandbox 内的 bash 命令自动执行，无需手动批准（`autoAllowBashIfSandboxed: true`）

### 与旧版本的区别

| | v0.x（旧） | v1.0（新） |
|---|---|---|
| 实现方式 | PreToolUse hook（bash 脚本） | Claude Code 原生 sandbox |
| 隔离级别 | 应用层（可被子进程绕过） | OS 级（子进程也隔离） |
| 网络隔离 | 无 | 有（域名白名单） |
| 权限弹窗 | 不减少 | 减少 84% |
| 维护方 | 自行维护 | Anthropic 维护 |

## 自定义模板

```
/sandbox-profile create my-profile dev
```

然后编辑 `skills/sandbox-profile/profiles/my-profile.json`。预置模板（default/dev/dangerously-open）不可删除。

## 禁用

```
/sandbox-profile reset              # 移除配置
/plugin disable feishu-channel-sandbox  # 或直接禁用插件
```

## Linux 前置依赖

```bash
# Ubuntu/Debian
sudo apt-get install bubblewrap socat

# Fedora
sudo dnf install bubblewrap socat
```

macOS 无需额外安装（使用系统内置 Seatbelt）。

## 许可

MIT
