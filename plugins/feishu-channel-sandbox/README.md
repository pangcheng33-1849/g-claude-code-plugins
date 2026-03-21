# feishu-channel-sandbox

可选的安全沙盒插件，配合 [feishu-channel](../feishu-channel) 使用。限制通过飞书访问 Claude 时的文件读写和命令执行范围。

## 安装

```bash
/plugin install feishu-channel-sandbox@g-claude-code-plugins
```

## 安全模型

沙盒采用 **fail-closed + 白名单** 策略：

- 配置文件缺失时**阻止所有操作**（而非放行）
- 文件路径经过 `realpath` **规范化**后再比较，防止 `../` 遍历和符号链接逃逸
- Bash 命令使用**白名单**（而非黑名单），支持前缀匹配和 glob 模式匹配
- **子 shell 构造被拒绝**：`$()`、`` ` ``、`<()`、`>()` 直接阻止，防止通过命令替换执行任意命令
- **管道/链式命令逐段校验**：`|`、`&&`、`||`、`;` 拆分后每段都必须在白名单内，防止 `echo ... | sh` 等绕过
- Bash 命令中出现的**文件路径也会被检查**，防止通过 `cat`、`ls` 等白名单命令访问受限路径
- 路径前缀匹配包含**目录边界检查**，`/tmp` 允许 `/tmp/foo` 但不允许 `/tmpevil`

**注意**：此沙盒是应用层防护，非 OS 级隔离。对于高安全场景，建议配合 Docker 或 macOS sandbox-exec 使用。

## 功能

安装后自动生效，通过 PreToolUse hook 拦截：

### sandbox-file.sh — 文件访问控制

拦截 **Read**、**Write**、**Edit** 工具调用：

1. 提取 `file_path`，展开 `~` 并规范化（解析 `../` 和符号链接，macOS 兼容）
2. 自动放行 Claude 工作目录（`cwd`）及其子目录
3. 对比 `sandbox.conf` 白名单（路径同样规范化后前缀匹配）
4. 不在白名单内则阻止（exit 2），并提示读取配置文件查看允许范围
5. 配置文件缺失时阻止所有文件操作
6. 所有 ALLOW/BLOCK 操作写入会话日志

### sandbox-bash.sh — 命令执行控制（三层检查）

拦截 **Bash** 工具调用，执行三层安全检查：

**第 1 层：命令拆分 + 子 shell 检测**

1. 引号感知地解析命令字符串
2. 检测 `$()`、`` ` ``、`<()`、`>()` 子 shell 构造 → 直接阻止
3. 按 `|`、`&&`、`||`、`;`、换行符拆分为多个命令段

**第 2 层：每段命令 glob 白名单**

1. 对每个拆分出的命令段，去除首尾空白
2. 对比 `sandbox-bash.conf` 白名单：无 glob 字符的行做前缀匹配，含 `*`/`?`/`[` 的行做 bash glob 匹配
3. 任一段不在白名单内则阻止（exit 2）

glob 匹配对齐 Claude Code 的 allow 机制风格，`*` 匹配任意字符（含 `/` 和空格）。例如 `python3 /*/.claude/skills/*.py` 允许执行 skill 目录下的 `.py` 脚本，但天然阻止 `python3 -c "..."` 等注入（因为 `-c` 不以 `/` 开头）。

这防止了 `echo "payload" | sh`、`ls -la; rm -rf /` 等通过管道或链式命令绕过白名单的方式。

**第 3 层：命令中的路径检查**

即使所有命令段都在白名单中，还会从命令字符串中提取所有路径形式的子串（绝对路径 `/...`、主目录相对 `~/...`、上级遍历 `../...`），对每个路径做与 sandbox-file.sh 相同的白名单校验。

这防止了通过 `cat ~/secret.txt`、`ls ~/Downloads/`、`echo x > ~/private/file` 等方式绕过文件访问控制。`/dev/*` 路径始终放行（如 `/dev/null`）。

所有 ALLOW/BLOCK 操作写入会话日志。被拦截时会提示 Claude 读取对应配置文件查看允许范围，便于自我纠正。

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

首次启动会话时 setup.sh（SessionStart hook）自动完成初始化：

1. 将插件内的预设 profiles 同步到 `~/.claude/channels/feishu/profiles/`
2. 创建软链接 `sandbox.conf` → `profiles/default-sandbox.conf`、`sandbox-bash.conf` → `profiles/default-bash.conf`

活跃配置是指向 profiles 目录下对应文件的**软链接**，切换配置集只需改变链接指向，即时生效。

### `~/.claude/channels/feishu/sandbox.conf` — 文件路径白名单

默认允许：

```
~/.claude/channels/feishu    # 频道配置
~/.claude/plugins            # 插件缓存
*/.claude/skills             # 项目级 skill（glob 匹配任意祖先）
*/.claude/skills/*
*/.claude/commands           # 项目级命令
*/.claude/commands/*
*/.claude/agents             # 项目级 agent
*/.claude/agents/*
/tmp                         # 临时文件
```

加上 Claude 工作目录（自动检测，无需配置）。每行一个路径，支持 `~` 和 glob 模式（含 `*` 的行用 glob 匹配），`#` 开头为注释。

此白名单同时被 sandbox-file.sh 和 sandbox-bash.sh 的路径检查共用。

### `~/.claude/channels/feishu/sandbox-bash.conf` — 命令白名单

默认（default profile）允许只读类命令：

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
| 目录创建 | `mkdir`（受路径白名单约束） |
| 配置集管理 | `ln -sf ~/.claude/channels/feishu/...`, `readlink`, `cp ~/.claude/channels/feishu/profiles/...`, `rm ~/.claude/channels/feishu/profiles/...` |
| 脚本执行 | `python3 *.py`, `node *.js`, `bash *.sh`, `bun *.[jt]s`（仅限 `~/.claude/plugins/` 和 `*/.claude/skills/` 目录，glob 限定扩展名） |

所有命令都受路径检查约束，只能操作白名单路径内的文件。需要更多命令时可创建自定义配置集。

## 配置集（Profiles）

提供 `default` 和 `dev` 两个预设配置集，同时支持创建自定义配置集。通过 skill 管理：

```bash
/feishu-channel-sandbox-profile help              # 查看所有子命令
/feishu-channel-sandbox-profile                    # 查看当前配置集及可用列表
/feishu-channel-sandbox-profile dev                # 切换到开发模式
/feishu-channel-sandbox-profile default            # 恢复只读模式
/feishu-channel-sandbox-profile show [name]        # 查看配置集详细内容
/feishu-channel-sandbox-profile create <name> [base]  # 基于已有配置集创建自定义版本
/feishu-channel-sandbox-profile edit <name>        # 编辑自定义配置集
/feishu-channel-sandbox-profile delete <name>      # 删除自定义配置集
```

### default — 只读模式（默认）

仅允许只读/信息查询类命令，适合日常飞书对话场景。

### dev — 开发模式

在 default 基础上新增完整开发命令，覆盖前端、后端、iOS、Android 全栈开发：

| 类型 | 新增命令 |
|------|------|
| Git 完整 | `git`（所有子命令） |
| 文件操作 | `mkdir`, `cp`, `mv`, `rm`, `touch`, `chmod`, `ln`, `tar`, `zip`, `unzip` |
| 前端 | `npm`, `npx`, `bun`, `bunx`, `pnpm`, `yarn`, `vite`, `webpack`, `tsc`, `eslint`, `prettier` |
| 后端 | `pip`, `cargo`, `go`, `mvn`, `gradle`, `dotnet`, `composer`, `gem`, `bundle` |
| iOS | `xcodebuild`, `xcrun`, `swift`, `pod`, `simctl`, `codesign` |
| Android | `adb`, `sdkmanager`, `emulator`, `aapt`, `apksigner`, `./gradlew` |
| 构建 | `make`, `cmake`, `ninja`, `bazel` |
| 运行时 | `node`, `python3`, `deno`, `ruby`, `java`, `rustc`, `kotlin` |
| 网络 | `curl`, `wget` |
| 工具 | `docker`, `gh`, `kill`, `lsof` |

dev 模式同时扩展路径白名单：新增 `/usr/local`、`~/.npm`、`~/.bun`、`~/.cargo`、`~/.ssh` 等开发常用路径。

**所有命令仍受路径白名单约束**，只能操作项目目录和已授权路径。

### 自定义配置集

可基于任意已有配置集创建自定义版本：

```bash
# 基于 dev 创建一个前端专用配置集
/feishu-channel-sandbox-profile create frontend dev
# 编辑：按需增删命令和路径
/feishu-channel-sandbox-profile edit frontend
# 切换使用
/feishu-channel-sandbox-profile frontend
```

自定义配置集存放在 `~/.claude/channels/feishu/profiles/`，由 `{name}-bash.conf` 和 `{name}-sandbox.conf` 两个文件组成。预设配置集（default、dev）不可编辑和删除。

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
