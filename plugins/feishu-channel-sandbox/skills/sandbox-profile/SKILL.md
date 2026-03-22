---
name: sandbox-profile
description: 当用户提出"切换沙盒模式""应用安全配置""查看沙盒配置""管理 sandbox profile"时使用此 skill。管理 Claude Code 内置 sandbox 的 settings.json 配置模板。
---

# Sandbox Profile 管理

管理 Claude Code 内置 sandbox 的配置模板。通过读写 `.claude/settings.local.json` 应用预置或自定义的安全配置。

使用 `_sandboxProfile` 字段追踪当前应用的 profile 名称。

## 命令

根据用户输入的参数执行对应操作：

### `list`（默认，无参数时执行）

1. 读取 skill 目录下 `profiles/*.json` 列出所有可用模板
2. 读取当前项目的 `.claude/settings.local.json`，提取 `_sandboxProfile` 标记当前 profile
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
   - `_sandboxProfile`
4. **添加阶段**：将模板的字段写入 settings
   - `sandbox` → 写入模板的 sandbox 对象
   - `permissions.allow` → 写入模板的 allow 数组
   - `permissions.deny` → 写入模板的 deny 数组
   - `_sandboxProfile` → 写入 `"<name>"`
5. 保留 `permissions` 下其他字段（如 `defaultMode`）和 settings 中其他字段不变
6. 写入文件
7. 提示用户：配置已生效，Claude Code 会自动重载

**注意**：如果目标文件不存在，直接创建。

### `reset [--shared]`

**清除所有 sandbox 相关配置**：

1. 读取目标 settings 文件
2. 删除以下字段：
   - `sandbox`
   - `permissions.allow`
   - `permissions.deny`
   - `_sandboxProfile`
3. 如果 `permissions` 对象为空，也删除 `permissions`
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
- **apply 使用先删后加模式**：先移除旧的 sandbox/permissions 配置，再写入新 profile 的配置
- `_sandboxProfile` 字段记录当前激活的 profile 名，用于 list/show 标记
- 写入前确认文件路径正确（`.claude/settings.local.json` 或 `.claude/settings.json`）
