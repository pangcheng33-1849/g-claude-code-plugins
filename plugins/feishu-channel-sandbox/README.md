# feishu-channel-sandbox

可选的安全沙盒插件，配合 [feishu-channel](https://github.com/pangcheng1849/g-claude-code-plugins/tree/main/plugins/feishu-channel) 使用。限制通过飞书访问 Claude 时的文件读写和命令执行范围。

## 安装

```bash
/plugin install feishu-channel-sandbox@g-claude-code-plugins
```

## 安全模型

沙盒采用 **fail-closed + 白名单** 策略：

- 配置文件缺失时**阻止所有操作**（而非放行）
- 文件路径经过 `realpath` **规范化**后再比较，防止 `../` 遍历和符号链接逃逸
- Bash 命令使用**白名单**（而非黑名单），只允许明确列出的命令前缀
- Bash 命令中出现的**文件路径也会被检查**，防止通过 `cat`、`ls` 等白名单命令访问受限路径

**注意**：此沙盒是应用层防护，非 OS 级隔离。对于高安全场景，建议配合 Docker 或 macOS sandbox-exec 使用。

## 功能

安装后自动生效，通过 PreToolUse hook 拦截：

### sandbox-file.sh — 文件访问控制

拦截 **Read**、**Write**、**Edit** 工具调用：

1. 提取 `file_path`，展开 `~` 并通过 `realpath -m` 规范化（解析 `../` 和符号链接）
2. 自动放行 Claude 工作目录（`cwd`）及其子目录
3. 对比 `sandbox.conf` 白名单（路径同样规范化后前缀匹配）
4. 不在白名单内则阻止（exit 2）
5. 配置文件缺失时阻止所有文件操作
6. 所有 ALLOW/BLOCK 操作写入会话日志

### sandbox-bash.sh — 命令执行控制（两层检查）

拦截 **Bash** 工具调用，执行两层安全检查：

**第 1 层：命令前缀白名单**

1. 提取 `command` 内容
2. 对比 `sandbox-bash.conf` 白名单（命令前缀匹配）
3. 不在白名单内则阻止（exit 2）

**第 2 层：命令中的路径检查**

即使命令前缀在白名单中，还会从命令字符串中提取所有路径形式的子串（绝对路径 `/...`、主目录相对 `~/...`、上级遍历 `../...`），对每个路径做与 sandbox-file.sh 相同的白名单校验。

这防止了通过 `cat ~/secret.txt`、`ls ~/Downloads/`、`echo x > ~/private/file` 等方式绕过文件访问控制。`/dev/*` 路径始终放行（如 `/dev/null`）。

所有 ALLOW/BLOCK 操作写入会话日志。

## 日志

沙盒的 ALLOW/BLOCK 操作与 feishu-channel 的服务日志写入同一个会话文件，便于按会话排查问题。

```bash
# 查看当前会话日志（包含 server + sandbox 日志）
tail -f ~/.claude/channels/feishu/logs/latest

# 过滤沙盒拦截记录
grep 'sandbox-' ~/.claude/channels/feishu/logs/latest
```

日志格式：

```
[2026-03-21T09:53:45.000Z] sandbox-bash: BLOCK command=ls ~/Downloads/ (path /Users/.../Downloads/ not allowed)
[2026-03-21T09:54:32.000Z] sandbox-file: BLOCK path=/Users/.../Downloads/file.md (original: ~/Downloads/file.md)
[2026-03-21T09:55:14.000Z] sandbox-bash: ALLOW command=ls -la
```

日志按会话隔离，每次 feishu-channel 启动创建新文件，最多保留 10 个。`logs/latest` 是软链接，指向当前会话日志。

## 配置

首次启动会话时自动创建配置文件（SessionStart hook）。

### `~/.claude/channels/feishu/sandbox.conf` — 文件路径白名单

默认允许：

```
~/.claude/channels/feishu    # 频道配置
/tmp                          # 临时文件
```

加上 Claude 工作目录（自动检测，无需配置）。每行一个路径，支持 `~`，`#` 开头为注释。

此白名单同时被 sandbox-file.sh 和 sandbox-bash.sh 的路径检查共用。

### `~/.claude/channels/feishu/sandbox-bash.conf` — 命令白名单

默认允许只读类命令：

| 类型 | 默认允许的命令前缀 |
|------|------|
| 文件查看 | `ls`, `cat`, `head`, `tail`, `wc`, `file`, `stat` |
| 文本处理 | `grep`, `rg`, `ag`, `sed`, `awk`, `cut`, `tr`, `sort`, `uniq`, `diff`, `jq`, `yq` |
| 文件系统信息 | `du`, `df`, `find` |
| 系统信息 | `date`, `pwd`, `whoami`, `which`, `ps`, `top -l 1` |
| 输出 | `echo`, `printf` |
| Git 只读 | `git status`, `git log`, `git diff`, `git show`, `git branch` |
| 版本查询 | `node --version`, `python3 --version`, `bun --version` |
| 包信息 | `npm list`, `npm info`, `pip list`, `pip show` |

所有命令都受第 2 层路径检查约束，只能操作白名单路径内的文件。需要更多命令时编辑 `sandbox-bash.conf` 添加对应前缀。

## 禁用

不需要沙盒时，禁用或卸载插件即可：

```bash
/plugin disable feishu-channel-sandbox
# 或
/plugin uninstall feishu-channel-sandbox@g-claude-code-plugins
```

feishu-channel 频道功能不受影响。

## 许可

MIT
