---
name: sandbox-profile
description: 当用户提出"切换沙盒模式""应用安全配置""查看沙盒配置""管理 sandbox profile"时使用此 skill。管理 Claude Code 内置 sandbox 的 settings.json 配置模板。
---

# Sandbox Profile 管理

管理 Claude Code 内置 sandbox 的配置模板。通过读写 `.claude/settings.local.json` 应用预置或自定义的安全配置。

## 命令

根据用户输入的参数执行对应操作：

### `list`（默认，无参数时执行）

1. 读取 skill 目录下 `profiles/*.json` 列出所有可用模板
2. 读取当前项目的 `.claude/settings.local.json`，提取 `sandbox` 和 `permissions` 部分
3. 输出：可用模板列表 + 当前配置摘要

### `show <name>`

1. 如果 `<name>` 是模板名（如 `default`、`dev`、`dangerously-open`）：读取对应 `profiles/<name>.json` 并展示
2. 如果 `<name>` 是 `current`：读取 `.claude/settings.local.json` 展示 sandbox 相关配置

### `apply <name> [--shared]`

1. 读取 `profiles/<name>.json` 模板
2. 读取目标 settings 文件：
   - 默认：`.claude/settings.local.json`（个人配置，gitignored）
   - 加 `--shared`：`.claude/settings.json`（团队共享，提交到 git）
3. 将模板的 `sandbox` 字段**整体替换**到 settings 中
4. 将模板的 `permissions.allow` 和 `permissions.deny` **整体替换**到 settings 中（覆盖旧规则，确保切换 profile 时限制生效）
5. 保留 `permissions` 下其他字段（如 `defaultMode`）和 settings 中其他字段不变
6. 写入文件
7. 提示用户：配置已生效，Claude Code 会自动重载

**注意**：如果目标文件不存在，直接创建。

### `reset [--shared]`

1. 读取目标 settings 文件
2. 删除 `sandbox` 字段
3. 删除 `permissions.allow` 和 `permissions.deny` 字段（保留 `permissions` 下其他字段如 `defaultMode`）
4. 写入文件
5. 提示用户：sandbox 配置已移除

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

## 执行规则

- 所有操作通过 Read/Write 工具直接读写 JSON 文件完成
- 不依赖任何脚本或 hook
- apply 时 sandbox 和 permissions.allow/deny 整体替换（不合并），确保 profile 切换生效
- 写入前确认文件路径正确（`.claude/settings.local.json` 或 `.claude/settings.json`）
