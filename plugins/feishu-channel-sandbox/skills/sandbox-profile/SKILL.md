---
name: sandbox-profile
description: 当用户提出"切换沙盒模式""应用安全配置""查看沙盒配置""管理 sandbox profile"时使用此 skill。管理 Claude Code 内置 sandbox 的 settings.json 配置模板。
---

# Sandbox Profile 管理

管理 Claude Code 内置 sandbox 的配置模板。通过读写 `.claude/settings.local.json` 应用预置或自定义的安全配置。

当前激活的 profile 名记录在 `~/.claude/channels/feishu/sandbox-profile/active`（纯文本，内容为 profile 名）。

## 命令

根据用户输入的参数执行对应操作：

### `list`（默认，无参数时执行）

1. 读取 skill 目录下 `profiles/*.json` 列出所有可用模板
2. 读取 `~/.claude/channels/feishu/sandbox-profile/active` 获取当前 profile 名
3. 输出：可用模板列表（标注当前激活的）+ 当前配置摘要

### `show <name>`

1. 如果 `<name>` 是模板名（如 `default`、`dev`、`dangerously-open`）：读取对应 `profiles/<name>.json` 并展示
2. 如果 `<name>` 是 `current`：读取 `.claude/settings.local.json` 展示 sandbox 相关配置

### `apply <name> [--shared]`

**先删后加**，确保 profile 切换干净：

1. 读取 `profiles/<name>.json` 模板
2. 读取目标 settings 文件：
   - 默认：`.claude/settings.local.json`（个人配置，gitignored）
   - 加 `--shared`：`.claude/settings.json`（团队共享，提交到 git）
3. **删除阶段**：从 settings 中移除以下字段
   - `sandbox`（整个对象）
   - `permissions.allow`（整个数组）
   - `permissions.deny`（整个数组）
4. **添加阶段**：将模板的字段写入 settings
   - `sandbox` → 写入模板的 sandbox 对象
   - `permissions.allow` → 写入模板的 allow 数组
   - `permissions.deny` → 写入模板的 deny 数组（如模板中有）
5. 保留 `permissions` 下其他字段（如 `defaultMode`）和 settings 中其他字段不变
6. 写入 settings 文件
7. 将 profile 名写入 `~/.claude/channels/feishu/sandbox-profile/active`（创建目录如不存在）
8. 提示用户：配置已生效，Claude Code 会自动重载

**注意**：如果目标 settings 文件不存在，直接创建。

### `reset [--shared]`

**清除所有 sandbox 相关配置**：

1. 读取目标 settings 文件
2. 删除以下字段：
   - `sandbox`
   - `permissions.allow`
   - `permissions.deny`
3. 如果 `permissions` 对象为空，也删除 `permissions`
4. 写入 settings 文件
5. 删除 `~/.claude/channels/feishu/sandbox-profile/active`
6. 提示用户：sandbox 配置已移除

### `create <name> [base]`

1. `base` 默认为 `dev`
2. 复制 `profiles/<base>.json` 为 `profiles/<name>.json`
3. 提示用户可以编辑新模板

预置模板（`default`、`dev`、`dangerously-open`）不可被覆盖。

### `delete <name>`

1. 检查 `<name>` 不是预置模板
2. 删除 `profiles/<name>.json`

## 预置模板说明

| 模板 | 场景 | sandbox | 网络 | 文件写入 |
|------|------|---------|------|----------|
| `default` | 飞书频道安全模式 | 开启，关闭逃逸口 | 飞书域名放行，其他弹窗 | 仅 cwd + feishu 目录 + /tmp |
| `dev` | 开发调试 | 开启，允许逃逸口 | 全部放开 | cwd + 包管理器缓存 + 开发工具 |
| `dangerously-open` | 无限制 | 关闭 | 无限制 | 无限制 |

## 状态文件

```
~/.claude/channels/feishu/sandbox-profile/
└── active    # 纯文本，内容为当前 profile 名（如 "default"）
```

不存在时表示未应用任何 profile。

## 执行规则

- 所有操作通过 Read/Write/Bash 工具完成，不依赖脚本或 hook
- **apply 使用先删后加模式**：先移除旧 sandbox/permissions 配置，再写入新 profile
- settings.json 中不添加任何自定义字段，profile 状态存储在独立文件
- 写入前确认文件路径正确（`.claude/settings.local.json` 或 `.claude/settings.json`）
