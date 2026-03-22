# feishu-channel

飞书/Lark 频道插件 — 通过飞书 IM 与 Claude Code 对话。

基于 MCP Channel 模式，单个 `server.ts` 作为 Claude Code 子进程运行，通过飞书 WebSocket 长连接接收消息，经 stdio JSON-RPC 传递给 Claude。

## 前置条件

- [Bun](https://bun.sh/) 运行时
- Claude Code CLI
- 飞书自建应用（见下方创建步骤）

## 快速开始

### 1. 创建飞书应用

前往[飞书开放平台](https://open.feishu.cn)（国际版前往 [Lark Developer](https://open.larksuite.com)）：

1. 创建**自建应用**
2. 记录 **App ID** 和 **App Secret**
3. **事件与回调** → 启用**长连接模式**（WebSocket） → 订阅 `im.message.receive_v1`
4. **权限管理**中启用：
   - `im:message` — 接收消息
   - `im:message:send_as_bot` — 以机器人身份发送消息
   - `im:resource` — 下载消息资源（图片/文件）
   - `im:chat` — 访问会话信息
   - `im:message.reactions:operate` — 添加/移除表情回应（可选）
5. **发布**应用

### 2. 配置凭证

**方式一**：设置环境变量（推荐，写入 `~/.zshenv` 或 `~/.bashrc`）：

```bash
export MY_LARK_APP_ID="cli_xxxxxxxx"
export MY_LARK_APP_SECRET="xxxxxxxxxxxxxxxx"
```

**方式二**：通过技能配置（需先安装插件，配置后重启会话）：

```
/feishu-channel-configure <appId> <appSecret>
```

凭证写入 `~/.claude/channels/feishu/.env`。服务器启动时读取，优先级高于环境变量。

国际版（Lark）额外设置：

```bash
export MY_LARK_BRAND="lark"
```

### 3. 安装插件

```bash
# 添加 marketplace（仅首次）
/plugin marketplace add pangcheng1849/g-claude-code-plugins

# 安装插件
/plugin install feishu-channel@g-claude-code-plugins
```

### 4. 启动

```bash
claude --dangerously-load-development-channels plugin:feishu-channel@g-claude-code-plugins
```

建议设置 alias：

```bash
alias claude-feishu='claude --dangerously-skip-permissions --dangerously-load-development-channels plugin:feishu-channel@g-claude-code-plugins'
```

> **权限提示**：如果不使用 `--dangerously-skip-permissions`，Claude 执行飞书技能时会频繁在终端弹出授权确认（每次调用脚本、读写文件都需要手动批准），体验较差。推荐方案：
>
> 1. **快速方案**：加 `--dangerously-skip-permissions` 跳过所有确认（如上 alias）
> 2. **精细方案**：在 `settings.json` 中通过 `allow` 白名单 + `"permission": "dontAsk"` 配置常用操作的自动放行，例如：
>    ```json
>    {
>      "permissions": {
>        "allow": [
>          "Bash(python3 */.claude/skills/*.py *)",
>          "Bash(cd */.claude/skills/* && python3 *)",
>          "Read(*/.claude/skills/*)"
>        ]
>      }
>    }
>    ```

### 5. 配对

首次使用需要配对，将你的飞书账号加入白名单：

1. 在飞书上给机器人发一条私信
2. 机器人回复一个 6 位配对码
3. 在 Claude Code 终端中执行：

```
/feishu-channel-access pair <配对码>
```

4. 飞书收到 "Paired!" 确认，即可开始对话

群组配对流程类似：在群里 @机器人，收到配对码后在终端配对。

## 技能

插件包含 4 个技能：3 个在 Claude Code 终端中执行，1 个通过飞书消息触发。

### `/feishu-channel-configure`

配置飞书应用凭证和查看频道状态。

```
/feishu-channel-configure                    # 查看当前状态
/feishu-channel-configure <appId> <secret>   # 保存凭证
/feishu-channel-configure clear              # 清除凭证
```

### `/feishu-channel-access`

管理访问控制 — 配对、白名单、群组策略。

```
/feishu-channel-access                       # 查看访问状态
/feishu-channel-access pair <code>           # 批准配对
/feishu-channel-access deny <code>           # 拒绝配对
/feishu-channel-access allow <open_id>       # 手动添加白名单
/feishu-channel-access remove <open_id>      # 移除白名单
/feishu-channel-access policy <mode>         # 设置 DM 策略
/feishu-channel-access group add <chat_id>   # 添加群组
/feishu-channel-access group rm <chat_id>    # 移除群组
/feishu-channel-access set <key> <value>     # 修改配置项
```

### `/feishu-channel-doctor`

诊断频道运行状态 — 进程冲突、WebSocket 连接、日志分析。

```
/feishu-channel-doctor                       # 完整诊断
```

### `feishu-channel-config`（飞书端触发）

通过飞书消息修改体验配置。白名单用户在飞书对话中直接说"把确认表情改成 👍"或"帮我看看当前配置"即可。Claude 自动调用此 skill 处理。

支持修改：`ackReaction`、`replyToMode`、`textChunkLimit`、`chunkMode`。

不支持修改安全配置（dmPolicy、allowFrom、groups），需在终端使用 `/feishu-channel-access`。

## 配置项

通过 `/feishu-channel-access set <key> <value>` 修改，存储在 `~/.claude/channels/feishu/access.json`。

### DM 策略 (`dmPolicy`)

| 值 | 说明 |
|---|---|
| `pairing` | 默认。未知发送者收到配对码，配对后加入白名单 |
| `allowlist` | 仅白名单用户可发送，未知发送者静默丢弃 |
| `disabled` | 关闭所有 DM |

### 体验配置

| Key | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `ackReaction` | 字符串 | `FORTUNE` | 收到消息时添加的确认表情（大写 emoji 名称）。设为 `""` 禁用 |
| `replyToMode` | `off` \| `first` \| `all` | `first` | 引用回复模式：`off` 不引用，`first` 首条回复引用原消息，`all` 每条都引用 |
| `textChunkLimit` | 数字 | `4000` | 长文本分块的字符上限（飞书单条消息限制） |
| `chunkMode` | `length` \| `newline` | `newline` | 分块方式：`length` 按字符数切分，`newline` 在换行处切分 |
| `mentionPatterns` | JSON 数组 | 无 | 群聊中额外的 @提及匹配正则（除自动检测外） |

### 群组策略

每个群组独立配置，存储在 `access.json` 的 `groups` 字段：

```
/feishu-channel-access group add <chat_id>                      # 默认：需要 @提及
/feishu-channel-access group add <chat_id> --no-mention         # 无需 @提及
/feishu-channel-access group add <chat_id> --allow id1,id2      # 限制群内发送者
```

| 参数 | 说明 |
|------|------|
| `requireMention` | 是否需要 @机器人才触发（默认 `true`） |
| `allowFrom` | 群内白名单，空数组表示群内所有人可用 |

## MCP 工具

插件向 Claude 提供以下工具，Claude 自动调用来与飞书交互：

| 工具 | 说明 |
|------|------|
| `reply` | 回复飞书消息。支持文本、引用回复（reply_to）、附件（files） |
| `react` | 添加表情回应（大写 emoji 名称，如 THUMBSUP、HEART、DONE），同时清除 ack |
| `edit_message` | 编辑机器人已发送的消息 |
| `fetch_messages` | 拉取聊天历史（最多 50 条） |
| `download_resource` | 下载消息中的图片或文件到本地 |
| `dismiss_ack` | 清除确认表情（当通过飞书技能而非 reply 处理请求时使用） |

## 图片与文件

飞书消息中的图片在收到时**立即下载**到 `~/.claude/channels/feishu/inbox/`，因为飞书的 `image_key` 可能过期失效。下载后的本地路径通过 `image_path` 属性传递给 Claude。

对于消息中的其他附件（文件、音频等），资源信息（`file_key`、`file_name`）包含在通知的 `resources` 字段中，Claude 可通过 `download_resource` 工具按需下载。

## 消息处理

支持解析以下飞书消息类型：

| 类型 | 处理方式 |
|------|----------|
| `text` | 提取文本，去除机器人 @提及占位符 |
| `post` | 多语言富文本展开（zh_cn/en_us），渲染 text/link/at/image/markdown/code_block |
| `image` | 立即下载，传递本地路径 |
| `file` | 提取 file_key 和文件名，可按需下载 |
| `audio` | 提取 file_key 和时长，可按需下载 |
| `video`/`media` | 提取 file_key、文件名和时长，可按需下载 |
| `merge_forward` | 调用 API 获取子消息，递归展开为带时间戳和发送者的文本 |
| `interactive` | 提取卡片中的标题和文本内容（支持 v1 Message Card 和 v2 CardKit） |
| `share_chat` | 提取群组 chat_id |
| `share_user` | 提取用户 user_id |
| `location` | 占位文本 |
| `sticker` | 提取 file_key |
| 其他 | 返回 `[type message]` 占位文本 |

**消息去重**：飞书 WebSocket 重连时会重放消息，插件内置去重机制（5 分钟 TTL，最多 2000 条缓存）。超过 5 分钟的旧消息自动丢弃。

## 与飞书技能联动

feishu-channel 本身提供基础的消息收发能力。如果需要更丰富的飞书功能（发消息到其他会话、创建文档、管理多维表格、查日历、创建任务、搜索用户等），可以同时安装 g-feishu 插件：

```bash
/plugin install g-feishu@g-claude-code-plugins
```

安装后，Claude 会自动识别并优先使用这些技能完成飞书相关任务，channel 的 reply 工具仅用于对话回复。

使用飞书技能处理请求时，Claude 会自动调用 `dismiss_ack` 清除确认表情。在群聊中，通过技能回复时仍会引用原消息。

## 文件结构

```
~/.claude/channels/feishu/
├── .env              # 应用凭证（可选，优先读取环境变量）
├── access.json       # 访问控制配置
├── logs/             # 会话日志（每次启动一个文件，最多保留 10 个）
│   └── latest → ...  # 软链接，指向当前会话日志
├── inbox/            # 下载的图片和文件
└── approved/         # 配对批准标记文件（临时）
```

## 日志

日志按会话隔离，每次服务器启动创建新的日志文件，最多保留 10 个。`logs/latest` 是软链接，指向当前会话日志。

```bash
# 实时查看当前会话日志
tail -f ~/.claude/channels/feishu/logs/latest

# 过滤沙盒拦截记录
grep 'sandbox-' ~/.claude/channels/feishu/logs/latest
```

日志内容包括：服务器启动/关闭、消息收发、gate 判定、表情操作、沙盒 ALLOW/BLOCK 记录。

如果安装了 feishu-channel-sandbox，沙盒的拦截日志会写入同一个会话文件，便于统一排查。

## 常见问题

| 症状 | 原因 | 修复 |
|------|------|------|
| MCP 连接失败（feishu-channel 红色） | 凭证未配置 | 先配置凭证（见上方"配置凭证"），再重启会话。`/feishu-channel-doctor` 可诊断 |
| 消息发出但无回复 | 多个 bun 进程抢 WebSocket | 运行 `/feishu-channel-doctor` 排查，kill 旧进程 |
| gate: dropped | 发送者不在白名单 | `/feishu-channel-access pair <code>` 配对 |
| WebSocket 连接失败 | 凭证错误或网络问题 | `/feishu-channel-configure` 检查凭证 |
| 日志文件不存在 | 服务器尚未运行过 | 正常，首次启动后自动创建 |
| 消息延迟 | WebSocket 长连接偶有延迟 | 正常现象，无需处理 |
| 代码更新后无效 | 插件缓存未刷新 | `/plugin install` 重新安装 + `/mcp` 重连 |

## 安全沙盒（可选）

如果需要限制飞书会话的文件访问范围，可以安装独立的沙盒插件：

```bash
/plugin install feishu-channel-sandbox@g-claude-code-plugins
```

安装后通过 PreToolUse hook 拦截：

- **文件访问**（Read/Write/Edit）：只允许访问工作目录和 `sandbox.conf` 中配置的路径
- **Bash 命令**：两层检查 — 命令前缀白名单 + 命令中的路径白名单，防止通过 `cat`、`ls` 等命令绕过文件限制

不需要时 `/plugin disable feishu-channel-sandbox` 即可关闭，不影响频道功能。

详见 [feishu-channel-sandbox](../feishu-channel-sandbox)。

## 开发

本地开发时，修改代码后需要刷新插件缓存：

```bash
# 安装最新代码到缓存
/plugin install feishu-channel@g-claude-code-plugins

# 重连 MCP（重启 bun 进程）
/mcp
```

## 许可

MIT
