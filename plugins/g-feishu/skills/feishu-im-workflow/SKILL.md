---
name: feishu-im-workflow
description: 当用户提出”创建飞书群聊””读取飞书消息””发送消息””回复消息””编辑消息””撤回消息””添加或移除 reaction””添加群成员””获取群成员””读取话题””发布话题””回复话题””编辑话题””撤回话题”，或需要独立的 Feishu/Lark IM 工作流时，应使用此 skill。
---

# 飞书 IM 工作流

独立完成 Feishu/Lark IM 场景的建群、消息、话题、reaction、群成员和媒体上传操作。

## 1. 鉴权规则

**所有命令（除 `list-reaction-emojis`）都需要 token。调用前必须先获取。**

1. `feishu-auth-and-scopes` → `resolve-token --identity tenant`
2. 从 JSON 输出提取 `access_token`
3. 传 `--tenant-access-token` 给本 skill 命令
4. 同一 token 可复用（有效期内）

scope 不足（如缺 `im:message`）→ 通过 `feishu-auth-and-scopes` 重新获取。应用身份不在目标群 → 先调整可见性或拉入群。

## 2. 命令速查

**消息**

| 任务 | 命令 |
|------|------|
| 发送消息 | `send-message` |
| 回复消息 | `reply-message` |
| 编辑消息 | `edit-message` |
| 撤回消息 | `recall-message` |
| 读取消息 | `list-messages` |

**群组**

| 任务 | 命令 |
|------|------|
| 创建群聊 | `create-chat` |
| 群信息 | `get-chat` |
| 群成员 | `get-chat-members` |
| 加成员 | `add-chat-members` |

**话题**

| 任务 | 命令 |
|------|------|
| 发布话题 | `publish-topic` |
| 回复话题 | `reply-topic` |
| 读取话题 | `get-topic` / `get-thread` |
| 编辑话题 | `edit-topic` |
| 撤回话题 | `recall-topic` |

**Reaction**

| 任务 | 命令 |
|------|------|
| 添加 | `add-reaction` |
| 读取 | `list-reactions` |
| 移除 | `remove-reaction` |
| emoji 参考 | `list-reaction-emojis` |

**媒体上传**

| 任务 | 命令 |
|------|------|
| 上传图片 | `upload-image`（JPG/PNG/WEBP/GIF 等，≤10 MB） |
| 上传文件 | `upload-file`（opus/mp4/pdf/doc/xls/ppt/stream，≤30 MB） |

所有命令通过 `scripts/feishu_im_helper.py <command>` 调用。

## 3. 话题模型

- `topic` = chat 中的一条根消息（讨论入口）
- `thread` = 围绕根消息的回复容器，读取依赖 `thread_id`

要点：
- `thread_id` 在首次 thread 回复后才出现
- 只有 `topic_message_id` → 配合 `chat_id` 用 `get-topic` 解析
- topic 存在但无 thread → helper 返回 `reason = thread_not_created_yet`

详见 `references/thread-model.md`。

## 4. 消息内容写法

### 快捷方式

| 场景 | 参数 |
|------|------|
| 纯文本 | `--text “内容”` |
| 图片 | `--image-key <key>`（自动 msg_type=image） |
| 文件 | `--file-key <key> --msg-type file\|audio\|media\|sticker` |
| 富文本/卡片 | `--msg-type post\|interactive --content-json '...'` 或 `--content-file` |

**选择原则**：非随意对话优先 `interactive`；只需结构化长正文再考虑 `post`。

上传的 `file_type` 必须与 `msg_type` 匹配（否则 230055）：`opus→audio`、`mp4→media`、`pdf/doc/xls/ppt/stream→file`。

卡片布局详见 `references/message-content.md`。

### @提及（mention）

**三种消息类型格式不同，不要混用：**

| msg_type | 格式 | 示例 |
|----------|------|------|
| **text** | `<at>` 标签嵌入文本 | `--text '<at user_id=”ou_xxx”>Name</at> 正文'` |
| **post** | JSON 元素在 content 数组中 | `{“tag”:”at”,”user_id”:”ou_xxx”}` |
| **interactive** | `<at>` 标签在 `{“tag”:”markdown”}` 中 | `{“tag”:”markdown”,”content”:”<at id=ou_xxx></at> 正文”}` |

@所有人：`user_id=”all”`（text/post）或 `id=all`（interactive）。

**常见坑：**
- post 中 `<at>` 标签**无效**，必须用 JSON 元素 `{“tag”:”at”,”user_id”:”...”}`
- interactive 中属性名是 **`id`** 不是 `user_id`
- interactive 中必须用 **`{“tag”:”markdown”}`**，不是 `{“tag”:”div”,”text”:{“tag”:”lark_md”}}`

## 5. 核心工作流

### 5.1 媒体上传与发送

发送图片：`upload-image` → `image_key` → `send-message --image-key`

发送文件/音频/视频：`upload-file` → `file_key` → `send-message --file-key --msg-type`

注意：
- 上传和发送需同一个 tenant token
- scope：上传需 `im:resource`，发送需 `im:message`
- 音频需先转 opus：`ffmpeg -i src.mp3 -acodec libopus -ac 1 -ar 16000 out.opus`
- 视频可附缩略图：额外 `upload-image` 得到 `image_key` → `--media-image-key`

### 5.2 话题工作流

1. `publish-topic` → 发根消息
2. `reply-topic` → 对根消息 thread 回复
3. `get-topic` → 用 `thread_id` 或 `topic_message_id + chat_id`
4. `edit-topic` / `recall-topic` → 操作根消息

### 5.3 Reaction

默认 emoji 推荐顺序：`THUMBSUP` → `THANKS` → `APPLAUSE` → `SMILE` → `PARTY` → `HEART`。完整列表见 `references/reaction-emojis.md`。

## 6. 失败处理

| 问题 | 切到 |
|------|------|
| token / scope 不清楚 | `feishu-auth-and-scopes` |
| API 错误但不确定原因 | `feishu-api-diagnose` |
| 缺稳定 ID（chat_id/message_id/thread_id） | `feishu-search-and-locate` |

helper 已内建常见 hint：scope 不足、身份不在群里、thread 不存在、消息已撤回。

## 7. 边界

- 覆盖：消息群、消息、话题、reaction、群成员、媒体上传
- 不覆盖：bot 卡片模板、群公告、话题置顶
- `create-chat` 创建普通消息群；话题群需在飞书客户端创建

## 8. 附加资源

- `references/message-content.md` — 卡片布局与 post/interactive 写法
- `references/thread-model.md` — 话题模型
- `references/reaction-emojis.md` — emoji 参考
- `references/auth-defaults.md` — 鉴权默认值
- `examples/sample-prompts.md` — 常见调用示例
