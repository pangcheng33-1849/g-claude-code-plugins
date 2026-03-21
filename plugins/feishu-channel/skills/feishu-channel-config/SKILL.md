---
name: feishu-channel-config
description: 修改飞书频道体验配置 — 确认表情、引用回复、分块方式等。当飞书消息中用户请求更改频道显示/回复行为时使用。仅限体验配置，安全配置（策略、白名单、群组）必须拒绝。
user-invocable: false
allowed-tools:
  - Read
  - Write
---

# feishu-channel-config — 飞书频道体验配置

此 skill 由 Claude 在处理飞书频道消息时调用，允许白名单用户通过飞书修改体验配置。

**安全边界**：此 skill 只能修改体验配置。以下字段**绝对禁止修改**：
- `dmPolicy` — 访问策略
- `allowFrom` — 白名单
- `groups` — 群组策略
- `pending` — 配对条目

如果用户请求修改以上字段，拒绝并告知需要在 Claude Code 终端运行 `/feishu-channel-access`。

---

## 可修改的配置项

所有配置存储在 `~/.claude/channels/feishu/access.json`。

### `ackReaction`

收到消息时自动添加的确认表情，表示"正在处理"。

- **类型**：大写 emoji 名称字符串
- **默认值**：`FORTUNE`
- **可选值**：`THUMBSUP`、`EYES`、`OK`、`DONE`、`HEART`、`SMILE`、`FIRE`、`ROCKET`、`CLAP`、`MUSCLE`、`THANKS`、`PRAY` 等飞书支持的大写 emoji 名称
- **禁用**：设为空字符串 `""`
- **示例请求**："把确认表情改成 👍" → 设为 `THUMBSUP`

### `replyToMode`

回复消息时的引用模式。

- **类型**：枚举
- **默认值**：`first`
- **可选值**：
  - `off` — 不引用原消息
  - `first` — 仅第一条回复引用原消息
  - `all` — 每条回复都引用原消息
- **示例请求**："每条回复都引用原消息" → 设为 `all`

### `textChunkLimit`

长文本回复的分块字符上限。飞书单条消息有长度限制。

- **类型**：数字（100-4000）
- **默认值**：`4000`
- **校验**：必须是 100 到 4000 之间的整数
- **示例请求**："把消息长度限制改成 2000" → 设为 `2000`

### `chunkMode`

长文本的分块策略。

- **类型**：枚举
- **默认值**：`newline`
- **可选值**：
  - `newline` — 在换行处切分，保持段落完整
  - `length` — 按字符数强制切分
- **示例请求**："按段落分块" → 设为 `newline`

---

## 操作流程

### 修改配置

1. 读取 `~/.claude/channels/feishu/access.json`（文件不存在则使用默认值）。
2. 校验值是否合法（类型、范围、枚举）。不合法则通过 reply 工具告知用户正确格式。
3. 修改目标字段，写回文件。JSON 美化输出（2 空格缩进）。
4. 通过 reply 工具确认修改结果。

### 查看配置 / help

当用户询问当前配置或请求帮助时，通过 reply 工具返回当前体验配置值和可选值说明。

格式示例：

```
当前体验配置：
• 确认表情 (ackReaction): FORTUNE
• 引用模式 (replyToMode): first
• 分块上限 (textChunkLimit): 4000
• 分块方式 (chunkMode): newline

可修改项：
• ackReaction — 确认表情，如 THUMBSUP、EYES，设为空禁用
• replyToMode — off / first / all
• textChunkLimit — 100~4000 的整数
• chunkMode — newline / length
```

---

## 实现注意事项

- **务必**先读取文件再写入，不要覆盖其他字段。
- 用户可能用自然语言描述（"把表情改成点赞"），需要理解意图并映射到正确的值。
- 常见 emoji 映射：👍=THUMBSUP、❤️=HEART、🔥=FIRE、🚀=ROCKET、👀=EYES、✅=DONE、👌=OK、😊=SMILE、🙏=PRAY、💪=MUSCLE
- 修改后配置立即生效（服务器每条消息重新读取 access.json），无需重启。
- 通过 reply 工具回复时，记得传入 chat_id。
