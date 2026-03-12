# IM 鉴权默认规则

## 当前正式支持的 token 模式

- 所有真实 IM API 命令都只支持 `tenant token`
- `create-chat`
- `send-message`
- `publish-topic`
- `reply-message`
- `reply-topic`
- `edit-message`
- `edit-topic`
- `recall-message`
- `recall-topic`
- `add-reaction`
- `remove-reaction`
- `add-chat-members`
- `get-chat`
- `get-chat-members`
- `list-messages`
- `get-thread`
- `get-topic`
- `list-reactions`

说明：

- helper 不再提供 `user token` 路径
- 如果应用身份对目标 chat 不可见，或应用本身不在目标群，读取和写入都会失败
- 这类失败应先处理应用可见性、群成员关系和应用 scope，而不是切到 user token
- `create-chat` 额外依赖建群 scope。当前服务端会校验 `im:chat`、`im:chat:create`、`im:chat:create_by_user` 中至少一个。

## 显式参数优先级

1. `--tenant-access-token`
2. `MY_LARK_TENANT_ACCESS_TOKEN`

## 环境变量

- `MY_LARK_TENANT_ACCESS_TOKEN`

## 典型失败与重试方向

- `99991679` 且提示 `im:chat.members:write_only`
  - 当前 tenant token 缺成员写权限，优先补 scope 并重新获取 tenant token
- `99991672`
  - 当前应用缺 `im:chat` 或 `im:chat.members:write_only`，优先补 scope 并重新获取 tenant token
- `230002`
  - 调用身份不属于目标群，优先把应用拉进群或改用应用可访问的 chat
