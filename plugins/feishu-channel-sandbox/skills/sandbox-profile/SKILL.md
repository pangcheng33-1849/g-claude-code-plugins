---
name: sandbox-profile
description: 当用户提出"切换沙盒模式""应用安全配置""查看沙盒配置""管理 sandbox profile"时使用此 skill。管理 Claude Code 内置 sandbox 的 settings.json 配置模板。
---

# Sandbox Profile 管理

管理 Claude Code 内置 sandbox 的配置模板。通过脚本读写 `.claude/settings.local.json`，精确增删 sandbox 和 permissions 规则。

## 使用方式

所有操作通过 `scripts/sandbox_profile.py` 脚本执行：

```bash
python3 scripts/sandbox_profile.py <command> [args]
```

## 命令

| 命令 | 作用 |
|------|------|
| `list` | 列出可用模板，显示当前激活的 profile 和 sandbox 配置 |
| `show <name>` | 显示模板内容（`name` 为 `current` 时显示当前配置） |
| `apply <name>` | 应用模板（先删旧规则再加新规则），默认写 `.claude/settings.local.json` |
| `apply <name> --shared` | 应用模板到 `.claude/settings.json`（团队共享） |
| `reset` | 移除当前 profile 的 sandbox/permissions 规则 |
| `create <name> [base]` | 基于已有模板创建自定义模板（默认 base=dev） |
| `delete <name>` | 删除自定义模板（预置模板不可删） |

## apply 工作原理

**先删后加**，逐条精确操作：

1. 读取旧 profile 的 JSON（从 `~/.claude/channels/feishu/sandbox-profile/active` 获知当前 profile）
2. **逐条删除**旧 profile 带入的 `permissions.allow` 和 `permissions.deny` 规则（保留用户自己添加的规则）
3. 删除 `sandbox` 对象
4. **逐条添加**新 profile 的 `permissions.allow` 和 `permissions.deny` 规则（去重）
5. 写入新 profile 的 `sandbox` 对象
6. 更新 active 标记

用户自己通过 `/permissions` 或手动添加的规则不会被影响。

## 预置模板

| 模板 | 场景 | sandbox | 网络 | 文件写入 |
|------|------|---------|------|----------|
| `default` | 飞书频道安全模式 | 开启，关闭逃逸口 | 飞书域名放行，其他弹窗 | 仅 cwd + feishu 目录 + /tmp |
| `dev` | 开发调试 | 开启，允许逃逸口 | 全部放开 | cwd + 包管理器缓存 + 开发工具 |
| `dangerously-open` | 无限制 | 关闭 | 无限制 | 无限制 |

## 状态文件

```
~/.claude/channels/feishu/sandbox-profile/
└── active    # 纯文本，当前 profile 名（如 "default"）
```

不存在时表示未应用任何 profile。
