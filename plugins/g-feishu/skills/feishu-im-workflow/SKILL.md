---
name: feishu-im-workflow
description: 当用户提出“创建飞书群聊”“读取飞书消息”“发送消息”“回复消息”“编辑消息”“撤回消息”“添加或移除 reaction”“添加群成员”“获取群成员”“读取话题”“发布话题”“回复话题”“编辑话题”“撤回话题”，或需要独立的 Feishu/Lark IM 工作流时，应使用此 skill。
---

# 飞书 IM 工作流

## 快速索引

- `1. 鉴权规则`
- `2. 按任务选命令`
- `3. 当前正式支持`
- `4. 主题与话题模型`
- `5. 消息内容写法`
- `6. 核心工作流`
- `7. 失败处理`
- `8. 附加资源`

## 目的

在不依赖通道 runtime 的前提下，独立完成 Feishu/Lark IM 场景里的真实建群、消息、话题、reaction 和群成员操作。

当前处理范围：

- 创建普通消息群
- 读取 chat 元数据
- 获取群成员
- 添加群成员
- 读取群消息
- 发送消息
- 回复消息
- 编辑消息
- 撤回消息
- 读取话题
- 发布话题
- 回复话题
- 编辑话题
- 撤回话题
- 添加 reaction
- 读取 reaction
- 移除 reaction
- 提供常用 emoji 参考
- 支持文本、富文本长消息和卡片消息发送
- 上传图片（返回 image_key，可用于发送图片消息）
- 上传文件（返回 file_key，可用于发送文件消息）

## 1. 鉴权规则

**所有 IM API 命令（除 `list-reaction-emojis`）都需要 token。在调用任何命令前，必须先获取 token。**

典型流程：

1. 使用 skill `feishu-auth-and-scopes` 的 `resolve-token --identity tenant` 命令获取 tenant token
2. 从输出 JSON 中提取 `access_token`
3. 将 token 作为 `--tenant-access-token` 参数传给本 skill 的命令
4. 同一个 token 可在多个命令间复用（有效期内）

注意：
- 不要在没有 token 的情况下调用命令，会直接报错
- 如果返回 scope 不足（如缺 `im:message`），通过 `feishu-auth-and-scopes` 重新获取 token
- 如果应用身份不在目标群里，先调整应用可见性或把应用拉入群

## 2. 按任务选命令

- 创建群聊
  - `scripts/feishu_im_helper.py create-chat`
- 读取群信息
  - `scripts/feishu_im_helper.py get-chat`
- 获取群成员
  - `scripts/feishu_im_helper.py get-chat-members`
- 添加群成员
  - `scripts/feishu_im_helper.py add-chat-members`
- 读取消息
  - `scripts/feishu_im_helper.py list-messages`
- 发送根消息
  - `scripts/feishu_im_helper.py send-message`
- 发布话题
  - `scripts/feishu_im_helper.py publish-topic`
- 回复消息
  - `scripts/feishu_im_helper.py reply-message`
- 回复话题
  - `scripts/feishu_im_helper.py reply-topic`
- 编辑消息
  - `scripts/feishu_im_helper.py edit-message`
- 编辑话题
  - `scripts/feishu_im_helper.py edit-topic`
- 撤回消息
  - `scripts/feishu_im_helper.py recall-message`
- 撤回话题
  - `scripts/feishu_im_helper.py recall-topic`
- 读取话题
  - `scripts/feishu_im_helper.py get-thread`
  - `scripts/feishu_im_helper.py get-topic`
- 添加 reaction
  - `scripts/feishu_im_helper.py add-reaction`
- 读取 reaction
  - `scripts/feishu_im_helper.py list-reactions`
- 移除 reaction
  - `scripts/feishu_im_helper.py remove-reaction`
- 查看 emoji 参考
  - `scripts/feishu_im_helper.py list-reaction-emojis`
- 上传图片
  - `scripts/feishu_im_helper.py upload-image`
- 上传文件
  - `scripts/feishu_im_helper.py upload-file`

常见调用方式见 `examples/sample-prompts.md`。

## 3. 当前正式支持

- helper 已真实实现以下 IM API 能力：
  - `create-chat`
  - `get-chat`
  - `get-chat-members`
  - `add-chat-members`
  - `list-messages`
  - `send-message`
  - `publish-topic`
  - `reply-message`
  - `reply-topic`
  - `edit-message`
  - `edit-topic`
  - `recall-message`
  - `recall-topic`
  - `get-thread`
  - `get-topic`
  - `add-reaction`
  - `list-reactions`
  - `remove-reaction`
- `list-reaction-emojis` 当前使用内置参考表，不依赖远端 emoji 目录接口。
- 长消息发送已正式支持：
  - `msg_type=post`
  - `msg_type=interactive`
- 媒体上传已正式支持：
  - `upload-image`：上传图片，返回 `image_key`，支持 JPG/JPEG/PNG/WEBP/GIF/BMP/ICO/TIFF/HEIC，最大 10 MB
  - `upload-file`：上传文件，返回 `file_key`，支持 opus/mp4/pdf/doc/xls/ppt/stream，最大 30 MB

当前正式边界：

- 只覆盖普通消息群、消息、话题、reaction、群成员，不覆盖 bot 卡片模板、群公告、话题置顶等扩展能力。
- `create-chat` 当前创建的是普通消息群；如果需要直接创建话题群，请在飞书客户端中创建。
- 话题本质上是”chat 中的一条根消息 + thread 回复”，不是单独对象模型；细节见 `references/thread-model.md`。
- `add-chat-members` 的成功与否强依赖调用身份具备目标群的写权限，以及成员写权限 scope。
- 对候选 chat、消息或线程的比较和消歧，由 Agent 用自然语言完成，不再脚本化生成操作计划。

## 4. 主题与话题模型

在飞书 IM 里，这两个概念的区别是：

- `topic`
  - 指某个 chat 里的“话题根消息”
  - 也就是一条被当作讨论入口的根消息
- `thread`
  - 指围绕这条根消息展开的回复容器
  - 真实读取时依赖 `thread_id`

映射到 helper：

- 发布话题
  - 本质上是向 chat 发送一条根消息
- 回复话题
  - 本质上是对根消息执行 `reply_in_thread = true`
- 读取话题
  - 本质上是列取 `container_id_type = thread`
- 编辑话题 / 撤回话题
  - 本质上是编辑 / 撤回话题根消息

要点：

- `thread_id` 通常要在首次 thread 回复之后才稳定出现
- 如果只有 `topic_message_id`，可以配合 `chat_id` 先解析一次 thread
- 如果 topic 根消息存在但 `thread_id` 还没有生成，helper 会返回结构化失败：
  - `ok = false`
  - `reason = thread_not_created_yet`
  - 同时附带 `topic_message` 和 `thread_note`

完整模型和术语见 `references/thread-model.md`。

## 5. 消息内容写法

- 纯文本优先用：
  - `--text "内容"`
- 发图片（需先 `upload-image` 得到 `image_key`）：
  - `--image-key <image_key>`（自动设置 msg_type=image）
- 发文件（需先 `upload-file` 得到 `file_key`）：
  - `--file-key <file_key> --msg-type file`（pdf/doc/xls/ppt/stream 类型文件）
  - `--file-key <file_key> --msg-type audio`（opus 音频）
  - `--file-key <file_key> --msg-type media`（mp4 视频）
  - `--file-key <file_key> --msg-type sticker`（表情包）
  - 视频可附缩略图：额外加 `--media-image-key <image_key>`
- 非文本消息（富文本/卡片等）用：
  - `--msg-type`
  - `--content-json`
  - 或 `--content-file`
- 非随意对话、正式说明、带结构更新：
  - 优先 `interactive`
- 只需要结构化长正文、但不需要卡片布局：
  - 再考虑 `post`
- 如果要做更美观的卡片布局：
  - 优先查看 `references/message-content.md` 里的卡片基础结构、`div/fields/hr/note/action` 用法、模板和常见错误

注意：上传文件时选择的 `file_type` 必须与发送时 `msg_type` 匹配，否则报错 230055：
- `opus` → `audio`
- `mp4` → `media`
- `pdf/doc/xls/ppt/stream` → `file`

示例：

```bash
# 发文本
python3 scripts/feishu_im_helper.py send-message \
  --receive-id oc_xxx --receive-id-type chat_id \
  --text "你好" \
  --tenant-access-token "<TENANT_TOKEN>"

# 发图片（先上传图片得到 image_key）
python3 scripts/feishu_im_helper.py send-message \
  --receive-id oc_xxx --receive-id-type chat_id \
  --image-key "img_v2_xxx" \
  --tenant-access-token "<TENANT_TOKEN>"

# 发文件（先上传文件得到 file_key）
python3 scripts/feishu_im_helper.py send-message \
  --receive-id oc_xxx --receive-id-type chat_id \
  --file-key "file_xxx" --msg-type file \
  --tenant-access-token "<TENANT_TOKEN>"

# 发视频（带缩略图）
python3 scripts/feishu_im_helper.py send-message \
  --receive-id oc_xxx --receive-id-type chat_id \
  --file-key "file_xxx" --msg-type media \
  --media-image-key "img_v2_xxx" \
  --tenant-access-token "<TENANT_TOKEN>"

# 发卡片
python3 scripts/feishu_im_helper.py send-message \
  --receive-id oc_xxx --receive-id-type chat_id \
  --msg-type interactive --content-file ./card.json \
  --tenant-access-token "<TENANT_TOKEN>"
```

不同 `msg_type` 的内容格式见 `references/message-content.md`。
如果是非随意对话、正式通知、状态同步或结构复杂消息，请不要默认发 `text`，也不要先想 `post`，优先选 `interactive`。

## 6. 核心工作流

### 6.1 建群与加人

1. 先用 `create-chat` 创建普通消息群
2. 如果需要指定 owner，可传 `--owner-id`
3. 如果需要在创建后再加成员，继续调用 `add-chat-members`
4. 如果返回 `232025`
   - 先检查应用是否启用了 bot 能力

### 6.2 读取 chat / member / message

1. 先确定稳定标识符：
   - `chat_id`
   - `message_id`
   - `thread_id`
2. 群维度信息：
   - `get-chat`
   - `get-chat-members`
3. 消息维度信息：
   - `list-messages --chat-id ...`
   - 或 `get-thread --thread-id ...`

### 6.3 消息写操作

消息写操作统一遵循：

1. 先选目标：
   - 发给 chat
   - 还是发给 user
2. 明确消息类型：
   - `text`
   - `post`
   - `interactive`
   - 其他 `msg_type`
3. 对非随意长消息：
   - 优先 `interactive`
   - 只有卡片不合适时，再退回 `post`
4. 失败时优先检查：
   - 当前 token 类型
   - `im:message` 相关 scope
   - 调用身份是否在目标 chat 中

### 6.4 话题工作流

1. `publish-topic`
   - 先发根消息
2. `reply-topic`
   - 对根消息做 thread 回复
3. `get-topic`
   - 用 `thread_id` 或 `topic_message_id + chat_id`
4. `edit-topic / recall-topic`
   - 直接操作话题根消息

### 6.5 媒体上传与发送工作流

发送图片：

1. `upload-image --file-path ./pic.png --image-type message` → 得到 `image_key`
2. `send-message --receive-id <chat_id> --image-key <image_key>`

发送文件（pdf/doc/xls/ppt/stream）：

1. `upload-file --file-path ./doc.pdf --file-type pdf --file-name "文档.pdf"` → 得到 `file_key`
2. `send-message --receive-id <chat_id> --file-key <file_key> --msg-type file`

发送音频（opus）：

1. `upload-file --file-path ./voice.opus --file-type opus --file-name "语音.opus" --duration 3000` → 得到 `file_key`
2. `send-message --receive-id <chat_id> --file-key <file_key> --msg-type audio`

发送视频（mp4）：

1. `upload-file --file-path ./video.mp4 --file-type mp4 --file-name "视频.mp4" --duration 5000` → 得到 `file_key`
2. （可选）`upload-image --file-path ./thumb.jpg --image-type message` → 得到 `image_key`（缩略图）
3. `send-message --receive-id <chat_id> --file-key <file_key> --msg-type media [--media-image-key <image_key>]`

注意：
- 上传和发送需要同一个 tenant token
- 上传所需 scope：`im:resource` 或 `im:resource:upload`
- 发送所需 scope：`im:message`、`im:message:send_as_bot` 或 `im:message:send`
- 上传的 `file_type` 必须与发送时的 `msg_type` 匹配（否则报 230055）
- 音频文件需提前转为 opus 格式：`ffmpeg -i src.mp3 -acodec libopus -ac 1 -ar 16000 out.opus`
- `upload-image` 返回的 `image_key` 只能用于发消息；设头像时上传用 `--image-type avatar`

### 6.6 Reaction 工作流

1. `list-reaction-emojis`
   - 先确定 emoji 类型
   - 默认优先选活泼、正向、低歧义的 emoji，见 `references/reaction-emojis.md`
2. `add-reaction`
3. `list-reactions`
4. `remove-reaction`

推荐默认顺序：

- `THUMBSUP`
- `THANKS`
- `APPLAUSE`
- `SMILE`
- `PARTY`
- `HEART`

完整 emoji_type 参考见 `references/reaction-emojis.md`。

### 6.7 群成员工作流

1. 先确认目标 `chat_id`
2. 先 `get-chat-members`
3. 再 `add-chat-members`
4. 若失败，优先检查：
   - 调用身份是否有群写权限
   - 当前 token 是否具备成员写权限

## 7. 失败处理

- token、scope、授权来源不清楚
  - 切到 Agent Skill `feishu-auth-and-scopes`
- 真实 IM API 已返回错误，但还不能判断是鉴权、chat 可见性、message_id、thread_id 还是 payload 问题
  - 切到 Agent Skill `feishu-api-diagnose`
- 还没拿到稳定 `chat_id / message_id / thread_id`
  - 先切到 Agent Skill `feishu-search-and-locate`

当前 helper 已内建一部分常见 hint：

- 缺 `im:message.send_as_user`
- 缺群成员写权限
- 调用身份不在群里
- `thread_id` 无效或 topic 还没有 thread
- 消息已被撤回或不存在

## 8. 附加资源

- `references/auth-defaults.md`
- `references/thread-model.md`
- `references/message-content.md`
- `references/reaction-emojis.md`
- `examples/sample-prompts.md`
- `scripts/feishu_im_helper.py`
