# 话题与 thread 模型

在飞书 IM 里，话题不是独立资源类型，而是：

- 一个 chat 里的根消息
- 再加上这条根消息下面的 thread 回复

## 术语映射

- 话题根消息
  - 一条普通 root message
  - 有自己的 `message_id`
- 话题回复
  - 对根消息执行 `reply_in_thread = true`
- `thread_id`
  - thread 容器 ID
  - 常见形态是 `omt_xxx`

## 关键边界

- 刚发布话题时，通常只有根消息 `message_id`
- `thread_id` 往往要在第一条 thread 回复出现后才稳定产生
- 如果只有 `topic_message_id`，而没有 `thread_id`：
  - 可以配合 `chat_id` 先扫描消息列表
  - 如果仍然没有 `thread_id`，说明话题还没进入 thread 模式
  - helper 会返回结构化失败：
    - `ok = false`
    - `reason = thread_not_created_yet`
    - 以及原始 `topic_message` 和 `thread_note`

## 当前命令映射

- `publish-topic`
  - 对 chat 发送一条 root message
- `reply-topic`
  - 对根消息执行 `reply_in_thread = true`
- `get-topic`
  - 读取 thread
- `edit-topic`
  - 编辑根消息
- `recall-topic`
  - 撤回根消息

## 读取顺序建议

1. 已知 `thread_id`
   - 直接 `get-thread --thread-id ...`
2. 只有 `topic_message_id`
   - `get-topic --topic-message-id ... --chat-id ...`
3. 还没有稳定标识符
   - 先用 Agent Skill `feishu-search-and-locate` 找到 chat / message
