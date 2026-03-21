---
name: feishu-channel-sandbox-profile
description: Switch feishu sandbox profile (default/dev).
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Write
---

# /feishu-channel-sandbox-profile — 沙盒配置集管理

活跃配置是指向 `~/.claude/channels/feishu/profiles/` 下对应文件的软链接。
每个 profile 由两个文件组成：`{name}-bash.conf`（命令白名单）和 `{name}-sandbox.conf`（路径白名单）。

常量定义（后续指令中直接使用）：
- `PROFILES=~/.claude/channels/feishu/profiles`
- `CONF=~/.claude/channels/feishu`
- 预设 profile（不可编辑/删除）：`default`、`dev`

传入参数：`$ARGUMENTS`

---

## 根据第一个参数分派

### 无参数 — 等同于 `list`

执行下方 `list` 子命令。

### `help` — 显示帮助

输出：

```
沙盒配置集管理

用法：/feishu-channel-sandbox-profile <子命令> [参数]

子命令：
  (无参数)             查看当前配置集及所有可用配置集
  list                 同上
  show [name]          显示指定配置集的详细内容（默认为当前活跃）
  <name>               切换到指定配置集（如 default、dev、或自定义名称）
  create <name> [base] 基于 base（默认 dev）创建自定义配置集
  edit <name>          编辑自定义配置集（不可编辑 default/dev）
  delete <name>        删除自定义配置集（不可删除 default/dev）
  help                 显示此帮助

示例：
  /feishu-channel-sandbox-profile dev              切换到开发模式
  /feishu-channel-sandbox-profile create fe dev    基于 dev 创建名为 fe 的配置集
  /feishu-channel-sandbox-profile edit fe          编辑 fe 配置集
  /feishu-channel-sandbox-profile fe               切换到 fe
  /feishu-channel-sandbox-profile delete fe        删除 fe
```

### `list` — 列出所有配置集

运行：
```bash
readlink ~/.claude/channels/feishu/sandbox-bash.conf 2>/dev/null; ls ~/.claude/channels/feishu/profiles/*-bash.conf 2>/dev/null
```

根据输出：
1. 从 `readlink` 结果提取当前活跃 profile 名（文件名去掉 `-bash.conf`）
2. 从 `ls` 结果提取所有 profile 名
3. 标注预设（default、dev）和自定义
4. 标注当前活跃

输出示例：

```
当前沙盒配置集：dev

可用配置集：
  default    只读模式（预设）
  dev        完整开发命令（预设）← 当前
  frontend   自定义

切换：/feishu-channel-sandbox-profile <名称>
管理：/feishu-channel-sandbox-profile help
```

### `show` 或 `show <name>` — 显示配置集内容

如果没有指定 name，先通过 `readlink` 获取当前活跃 profile 名。

用 Read 工具读取 `PROFILES/{name}-bash.conf` 和 `PROFILES/{name}-sandbox.conf`，将内容展示给用户。

输出格式：

```
配置集：dev

── 命令白名单（sandbox-bash.conf）──
[文件内容]

── 路径白名单（sandbox.conf）──
[文件内容]
```

### `create <name>` 或 `create <name> <base>` — 创建自定义配置集

参数解析：第一个参数为 name，第二个参数为 base（默认 `dev`）。

前置检查：
- name 不能是 `default` 或 `dev`（提示：预设配置集不可覆盖）
- name 只允许字母、数字、连字符（提示命名规则）
- `PROFILES/{name}-bash.conf` 不能已存在（提示：已存在，用 edit 修改或 delete 后重建）
- `PROFILES/{base}-bash.conf` 必须存在（提示：基础配置集不存在）

步骤：
1. 运行 `cp PROFILES/{base}-bash.conf PROFILES/{name}-bash.conf && cp PROFILES/{base}-sandbox.conf PROFILES/{name}-sandbox.conf`
2. 用 Read 工具读取两个新文件
3. 如果用户在 `$ARGUMENTS` 中提供了额外描述（create name base 之后的文本），根据描述自动编辑配置（用 Write 工具写入修改后内容）。如果没有额外描述，提示用户可以用 `/feishu-channel-sandbox-profile edit {name}` 定制。
4. 输出确认：

```
已创建配置集：{name}（基于 {base}）

切换到此配置集：/feishu-channel-sandbox-profile {name}
编辑此配置集：/feishu-channel-sandbox-profile edit {name}
```

### `edit <name>` — 编辑自定义配置集

前置检查：
- name 不能是 `default` 或 `dev`（提示：预设配置集不可编辑，用 create 基于它创建自定义版本）
- `PROFILES/{name}-bash.conf` 必须存在（提示：配置集不存在，用 create 创建）

步骤：
1. 用 Read 工具读取 `PROFILES/{name}-bash.conf` 和 `PROFILES/{name}-sandbox.conf`
2. 展示当前内容
3. 如果用户在 `$ARGUMENTS` 中 edit name 之后提供了修改描述，根据描述自动修改并用 Write 写入。否则询问用户想修改什么。
4. 写入修改后内容
5. 如果当前软链接指向该 profile，提示已即时生效

### `delete <name>` — 删除自定义配置集

前置检查：
- name 不能是 `default` 或 `dev`（提示：预设配置集不可删除）
- `PROFILES/{name}-bash.conf` 必须存在（提示：配置集不存在）

步骤：
1. 检查当前是否正在使用该 profile（`readlink` 检查）。如果是，先切换到 default。
2. 运行 `rm PROFILES/{name}-bash.conf PROFILES/{name}-sandbox.conf`
3. 输出确认

### `default` — 切换到默认只读配置

运行：
```bash
ln -sf ~/.claude/channels/feishu/profiles/default-sandbox.conf ~/.claude/channels/feishu/sandbox.conf && ln -sf ~/.claude/channels/feishu/profiles/default-bash.conf ~/.claude/channels/feishu/sandbox-bash.conf
```

输出：

```
已恢复 default 配置集（只读模式）。

命令限制为：ls, cat, grep, git status/log/diff 等只读操作
路径限制为：项目目录、~/.claude/channels/feishu、/tmp

切换到开发模式：/feishu-channel-sandbox-profile dev
```

### `dev` — 切换到开发配置

运行：
```bash
ln -sf ~/.claude/channels/feishu/profiles/dev-sandbox.conf ~/.claude/channels/feishu/sandbox.conf && ln -sf ~/.claude/channels/feishu/profiles/dev-bash.conf ~/.claude/channels/feishu/sandbox-bash.conf
```

输出：

```
已切换到 dev 配置集（完整开发命令）。

新增命令：git（完整）、npm/bun/yarn/pnpm、make/cmake、xcodebuild/pod、adb/gradle、curl、docker 等
新增路径：/usr/local、~/.npm、~/.bun、~/.cargo、~/.ssh 等

所有命令仍受路径白名单约束，只能操作项目目录和已授权路径。
恢复只读模式：/feishu-channel-sandbox-profile default
```

### 其他 — 切换到指定配置集

检查 `PROFILES/{参数}-bash.conf` 是否存在：
- 存在 → 运行 `ln -sf` 切换（同 default/dev 的模式），输出确认
- 不存在 → 输出：

```
未知配置集：{参数}

查看可用配置集：/feishu-channel-sandbox-profile list
创建新配置集：/feishu-channel-sandbox-profile create {参数} dev
查看帮助：/feishu-channel-sandbox-profile help
```
