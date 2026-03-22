# @ben1849/feishu-channel

CLI tools for [feishu-channel](../plugins/feishu-channel) — 管理 Claude Code 内置 sandbox 的安全配置。

## 安装

```bash
# 从 npm（发布后）
npx @ben1849/feishu-channel sandbox apply default

# 本地使用
npx ./@ben1849/feishu-channel sandbox apply default
```

## Sandbox Profile 管理

在启动 feishu-channel 前配置 sandbox，控制文件系统访问和命令权限。

```bash
# 应用安全模式（推荐飞书频道日常使用）
npx @ben1849/feishu-channel sandbox apply default

# 应用开发模式
npx @ben1849/feishu-channel sandbox apply dev

# 无限制模式（仅在信任环境使用）
npx @ben1849/feishu-channel sandbox apply dangerously-open

# 查看当前配置
npx @ben1849/feishu-channel sandbox show

# 移除 sandbox 配置
npx @ben1849/feishu-channel sandbox reset
```

配置写入 `.claude/settings.local.json`（个人、gitignored），Claude Code 自动重载。

## 预置模板

### `default` — 安全模式

| 项目 | 配置 |
|------|------|
| Sandbox | 开启，关闭逃逸口 |
| 权限模式 | `dontAsk`（allow 列表外静默拒绝） |
| 文件写入 | 仅 CWD + `~/.claude/channels/feishu` + `~/.feishu-auth-cache` + `/tmp` |
| 文件读取 | 禁止 `~/.ssh`、`~/.aws`、`~/.gnupg` |
| 网络 | 飞书域名自动放行，其他首次弹窗 |
| 命令 | 只读命令 + skill 脚本 + git 只读 |
| 保护 | 禁止修改 `.claude/settings*` |

### `dev` — 开发模式

| 项目 | 配置 |
|------|------|
| Sandbox | 开启，允许逃逸口 |
| 权限模式 | `dontAsk` |
| 文件写入 | CWD + 包管理器缓存 + 开发工具目录 |
| 网络 | 全部放开 |
| 命令 | git/npm/pip/cargo/curl/docker/make 等全开 |
| 保护 | 禁止修改 `.claude/settings*` |

### `dangerously-open` — 无限制

关闭 sandbox + `bypassPermissions`。等同 `--dangerously-skip-permissions`。

## 自定义模板

```bash
# 基于 dev 创建
npx @ben1849/feishu-channel sandbox create myprofile dev

# 编辑（文件在 ~/.claude/channels/feishu/sandbox-profile/profiles/myprofile.json）

# 应用
npx @ben1849/feishu-channel sandbox apply myprofile

# 删除
npx @ben1849/feishu-channel sandbox delete myprofile
```

预置模板（default/dev/dangerously-open）不可删除。

## 工作原理

- 配置写入 `.claude/settings.local.json`，利用 Claude Code 内置 OS 级 sandbox（macOS Seatbelt / Linux bubblewrap）
- 切换 profile 时**先删后加**：精确删除旧 profile 的规则，保留用户手动添加的规则
- 当前激活的 profile 记录在 `~/.claude/channels/feishu/sandbox-profile/active`

## 许可

MIT
