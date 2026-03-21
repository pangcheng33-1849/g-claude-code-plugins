---
name: feishu-channel-configure
description: 设置飞书频道 — 保存应用凭证、查看访问策略和频道状态。当用户提供飞书应用凭证、要求配置飞书、问"怎么设置"或"谁能联系我"、或想查看频道状态时使用。
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Bash(ls *)
  - Bash(mkdir *)
---

# /feishu-channel-configure — 飞书频道配置

将应用凭证写入 `~/.claude/channels/feishu/.env`，并引导用户了解访问策略。服务器在启动时读取这两个文件。

注意：服务器也会从用户的 shell 配置（如 `.zshenv`）读取环境变量 `MY_LARK_APP_ID` 和 `MY_LARK_APP_SECRET`。如果环境变量已设置，.env 文件是可选的。

传入参数：`$ARGUMENTS`

---

## 根据参数分派

### 无参数 — 凭证状态

显示当前凭证配置：

1. **凭证** — 先检查 shell 环境变量 `MY_LARK_APP_ID` / `MY_LARK_APP_SECRET`。如未设置，检查 `~/.claude/channels/feishu/.env` 中的 `MY_LARK_APP_ID`。显示已设置/未设置；如已设置，显示前 8 位掩码（`cli_a8e1...`）。

2. **下一步** — 根据凭证状态给出提示：
   - 无凭证 → *"在 .zshenv 中设置 MY_LARK_APP_ID 和 MY_LARK_APP_SECRET，或运行 `/feishu-channel-configure <appId> <appSecret>`。"*
   - 凭证已设置 → *"凭证已就绪。运行 `/feishu-channel-access` 查看访问控制状态。"*

### `<appId> <appSecret>` — 保存凭证

1. 将 `$ARGUMENTS` 解析为两个空格分隔的值。
2. `mkdir -p ~/.claude/channels/feishu`
3. 读取已有的 `.env`（如存在）；更新/添加 `MY_LARK_APP_ID=` 和 `MY_LARK_APP_SECRET=` 行，保留其他配置。写回，不加引号。
4. 可选设置 `MY_LARK_BRAND=feishu`（国际版用 `lark`）。
5. 确认，然后显示无参数状态，让用户了解当前情况。

### `clear` — 清除凭证

从 .env 中删除 `MY_LARK_APP_ID=` 和 `MY_LARK_APP_SECRET=` 行。

---

## 飞书设置指南

当用户询问如何设置时，提供以下步骤：

1. 前往[飞书开放平台](https://open.feishu.cn)（国际版前往 [Lark Developer](https://open.larksuite.com)）
2. 创建**自建应用**
3. 从凭证页面获取 **App ID** 和 **App Secret**
4. 在**事件与回调**中：
   - 启用**长连接模式**（WebSocket）
   - 订阅事件：`im.message.receive_v1`（接收消息）
5. 在**权限管理**中，启用：
   - `im:message` — 接收消息
   - `im:message:send_as_bot` — 以机器人身份发送消息
   - `im:resource` — 下载消息资源（图片/文件）
   - `im:chat` — 访问会话信息
   - `im:message.reactions:operate` — 添加/移除表情回应（可选）
6. **发布**应用（或添加到测试群进行开发）
7. 在 shell 环境变量中设置凭证，或通过 `/feishu-channel-configure <appId> <appSecret>` 设置

---

## 实现注意事项

- channels 目录可能不存在（服务器尚未运行过）。文件不存在 = 未配置，不是错误。
- 服务器启动时读取一次 `.env`（先检查 shell 环境变量）。凭证变更需要重启会话或 `/reload-plugins`，保存后需告知用户。
- `access.json` 在每条入站消息时重新读取 — 通过 `/feishu-channel-access` 的策略变更立即生效，无需重启。
