# CLI 权限矩阵

这份矩阵覆盖本仓库当前 **所有已对外公开的 Feishu CLI 命令**。

它的目的不是替代官方 scope 列表，而是帮助 Agent 快速判断：

- 这个命令默认用哪种 token
- 当前仓库里是否已经有高置信度、已验证的最小 scope
- 哪些命令只能写出权限族，必须回官方文档确认

官方总表：

- [官方 scope 列表](https://open.larkoffice.com/document/server-docs/application-scope/scope-list)

使用规则：

- `已验证`：当前仓库里已有真实回归或高置信度稳定依赖。
- `权限族`：命名在控制台里容易继续细分，不在本地写成伪精确列表。
- 如果控制台里搜不到这里的 scope 名，或实际仍报 `invalid_scope`，直接回官方文档和对应 API 文档核对。

## feishu-auth-and-scopes

| 命令 | 默认身份 | 最小权限 / 前置 | 说明 |
| --- | --- | --- | --- |
| `required-identity` | 无 | 无 | 本地判断，不调飞书 API。 |
| `oauth-url` | 无 | 无 | 只拼授权链接，不调飞书 API。 |
| `tenant-token-curl` | 无 | 无 | 只生成 curl 模板。 |
| `user-token-curl` | 无 | 无 | 只生成 curl 模板。 |
| `classify-error` | 无 | 无 | 本地归因，不调飞书 API。 |
| `tenant-token` | app credentials | 无 scope；需要 `MY_LARK_APP_ID` / `MY_LARK_APP_SECRET` | 获取 tenant token 本身不依赖业务 scope。 |
| `auth-user` | user | `offline_access` + 本次请求的业务 scope | 设备授权获取 user token。 |
| `refresh-user-token` | user | `offline_access` | 使用 refresh token 刷新 user token。 |
| `resolve-token --identity user` | user | 取决于解析来源；如需新授权，同 `auth-user` | 可能命中环境变量、缓存、refresh 或设备授权。 |
| `resolve-token --identity tenant` | app credentials | 无 scope；需要应用凭证 | 本质上会走 tenant token 获取链路。 |
| `show-token-meta` | user | 无 | 只读本地缓存。 |
| `clear-token-cache` | user | 无 | 只改本地缓存。 |

## feishu-doc-workflow

| 命令 | 默认身份 | 最小权限 / 前置 | 说明 |
| --- | --- | --- | --- |
| `extract-ref` | 无 | 无 | 本地解析 URL/token。 |
| `normalize-markdown` | 无 | 无 | 本地清洗 Markdown。 |
| `api-plan` | 无 | 无 | 本地生成 API 计划。 |
| `fetch-content` 正文 | user 优先 | `docs:document.content:read` | 读取 doc/wiki 正文。 |
| `fetch-content --include-media` 图片/媒体 | user 优先 | `docs:document.content:read` + `docs:document.media:download` | 文档图片和媒体下载。 |
| `fetch-content --include-media` 导出兜底 | user 优先 | 再加 `docs:document:export` | 导出链路常用于媒体兜底。 |
| `create-doc` / `update-doc` | user 优先 | `docs` / `docx` 写权限族；按对应 API 文档确认 | 原生写入、convert、评论以外的正文更新都在这一类。 |
| `import-doc` | user 优先 | `drive` 导入 / 上传权限族；按 `import_task` 与上传接口文档确认 | 包含 `upload_all` + `import_tasks`。 |
| `list-docs` | user 优先 | `drive` / `wiki` 读取权限族；按对应 API 文档确认 | 文件夹、wiki space、wiki node 列取。 |
| `resolve-wiki-node` | user 优先 | `wiki` / `docs` 读取权限族；按对应 API 文档确认 | 从 docx token 或 wiki token 解析 wiki node。 |
| `share-doc` | user 优先 | `docs:permission.member:create` | 新增协作者。 |
| `update-share` | user 优先 | `docs:permission.member:update` | 修改协作者权限。 |
| `remove-share` | user 优先 | `docs:permission.member:delete` | 删除协作者。 |
| `transfer-owner` | user 优先 | `docs` 权限成员 / owner 变更权限族；按 API 文档确认 | 控制台命名容易变化。 |
| `get-comments` | tenant 优先 | 文档评论读取权限族；按评论 API 文档确认 | 已支持全文评论和 inline comment 读取。 |
| `add-comments` | tenant 优先 | 文档评论写权限族；按评论 API 文档确认 | 当前只支持创建顶层全文评论。 |
| `<whiteboard>` 读取/下载 | user 优先 | `board:whiteboard:node:read` | 白板图片导出、读取。 |
| `<whiteboard>` / PlantUML / Mermaid 写入 | user / tenant 取决于命令路径 | `board` 白板写权限族；按白板节点 API 文档确认 | 不在本地写死 scope 名。 |

## feishu-task-workflow

| 命令 | 默认身份 | 最小权限 / 前置 | 说明 |
| --- | --- | --- | --- |
| `draft` | 无 | 无 | 本地提取任务草案。 |
| `payload` | 无 | 无 | 本地生成 Task v2 payload。 |
| `create-task` | user 优先 | `task:task:write` | 已真实验证。 |
| `update-task` | user 优先 | `task:task:write` | 已真实验证。 |
| `complete-task` / `reopen-task` | user 优先 | `task:task:write` | 本质是 patch。 |
| `get-task` | user 优先 | `task` 读取权限；若 `task:task:write` 已可用通常也可读 | 如果控制台拆出只读 scope，回官方文档确认。 |
| `delete-task` | user 优先 | `task:task:write` | 已真实验证。 |
| `list-tasks` | user 优先 | `task` 读取权限族；必要时回官方文档确认 | 当前默认只走 user token。 |
| `add-members` / `remove-members` | user 优先 | `task:task:write` | 已真实验证。 |
| `add-reminders` | user 优先 | `task:task:write` | 已真实验证。 |

## feishu-calendar-workflow

| 命令 | 默认身份 | 最小权限 / 前置 | 说明 |
| --- | --- | --- | --- |
| `list-calendars` | user 优先 | calendar 读取权限族；按官方文档确认 | 当前 CLI 支持 user/tenant，但真实工作流通常 user 更稳。 |
| `list-events` / `get-event` | user 优先 | calendar event 读取权限族；按官方文档确认 | |
| `create-event` | tenant 优先 | `calendar:calendar.event:create` + attendee 相关权限族（tenant 路径） | tenant 创建时建议同时加用户参会人。 |
| `update-event` / `delete-event` | user 优先 | calendar event 写权限族；按官方文档确认 | 若用 tenant，需确认目标日历可写。 |
| `freebusy` | user 优先 | freebusy / availability 读取权限族；按官方文档确认 | 忙闲查询通常对用户身份更自然。 |
| `add-event-attendees` | tenant/user | `calendar:calendar` 或 `calendar:calendar.event:update` | 已真实验证。支持 user/chat/third_party 类型参与人。 |

## feishu-search-and-locate

| 命令 | 默认身份 | 最小权限 / 前置 | 说明 |
| --- | --- | --- | --- |
| `search-user` | user 优先 | `search/v1/user` 对应的用户搜索权限族；按官方文档确认 | 已真实验证姓名/邮箱都可搜。 |
| `search-doc` | user 优先 | 文档搜索权限族；按 `search/v2/doc_wiki/search` 文档确认 | 当前只保留 `DOC` 结果。 |
| `search-wiki` | user 优先 | wiki 搜索权限族；按 `wiki/v1/nodes/search` 文档确认 | |
| `search-chat` | user 优先 | chat 搜索 / IM 读取权限族；按 `im/v1/chats/search` 文档确认 | |
| `search-message` | user 优先 | `search:message` | 已真实验证。仅支持 user token。 |

## feishu-im-workflow

| 命令 | 默认身份 | 最小权限 / 前置 | 说明 |
| --- | --- | --- | --- |
| 全部命令 | tenant | tenant token；不支持 user token 降级 | 当前 IM workflow 是 tenant-only。 |
| `create-chat` | tenant | `im:chat:create` 或 `im:chat:create_by_user`，通常还需要 `im:chat` | 已真实验证。 |
| `get-chat` / `get-chat-members` | tenant | `im:chat` | 读取群元信息和成员。 |
| `add-chat-members` | tenant | `im:chat.members:write_only`，通常还需 `im:chat` | 已真实验证。 |
| `list-messages` | tenant | `im:message:readonly`，必要时再配 `im:chat` | 读消息时调用身份必须在群可见范围内。 |
| `send-message` / `publish-topic` / `reply-message` / `reply-topic` | tenant | `im:message` 写权限族；按消息 API 文档确认 | 支持 `text` / `post` / `interactive`。 |
| `edit-message` / `edit-topic` | tenant | `im:message` 写权限族；按更新消息 API 文档确认 | |
| `recall-message` / `recall-topic` | tenant | `im:message` 写权限族；按撤回消息 API 文档确认 | |
| `get-thread` / `get-topic` | tenant | `im:message:readonly` | 本质上是读 thread/topic。 |
| `add-reaction` / `remove-reaction` / `list-reactions` | tenant | reaction 权限族；按 reaction API 文档确认 | `list-reaction-emojis` 为本地命令，不需 scope。 |

## feishu-bitable-workflow

| 命令 | 默认身份 | 最小权限 / 前置 | 说明 |
| --- | --- | --- | --- |
| 全部 bitable 命令 | user 优先 | bitable/base 权限族；按具体资源 API 文档确认 | 这一组最容易猜错，不在本地写伪精确全表。 |
| `create-app` / `get-app` / `list-apps` / `update-app` / `copy-app` | user 优先 | app 读写权限族 | |
| `create-table` / `list-tables` / `update-table` / `delete-table` / `batch-create-tables` / `batch-delete-tables` | user 优先 | table 读写权限族 | |
| `create-field` / `list-fields` / `update-field` / `delete-field` | user 优先 | field 读写权限族 | |
| `create-record` / `list-records` / `update-record` / `delete-record` / `batch-create-records` / `batch-update-records` / `batch-delete-records` | user 优先 | record 读写权限族 | |
| `get-view` / `create-view` / `list-views` / `update-view` / `delete-view` | user 优先 | view 读写权限族 | |

## feishu-sheets-workflow

| 命令 | 默认身份 | 最小权限 / 前置 | 说明 |
| --- | --- | --- | --- |
| `create-sheet` | user 优先 | `sheets:spreadsheet:create` | 已真实验证。Drive 文件夹需 user token；wiki 节点需先添加文档应用。 |
| `get-sheet-info` / `query-sheets` | user 优先 | `sheets:spreadsheet.meta:read` | 已真实验证。 |
| `create-worksheet` / `copy-worksheet` / `delete-worksheet` | user 优先 | `sheets:spreadsheet:write_only` | 已真实验证。 |
| `read-ranges` | user 优先 | `sheets:spreadsheet:read` | 已真实验证。 |
| `write-cells` / `insert-rows` / `append-rows` / `clear-ranges` | user 优先 | `sheets:spreadsheet:write_only` | 已真实验证。 |
| `find-cells` | user 优先 | `sheets:spreadsheet:read` | 已真实验证。 |
| `replace-cells` | user 优先 | `sheets:spreadsheet:write_only` | 已真实验证。 |

## feishu-api-diagnose

| 命令 | 默认身份 | 最小权限 / 前置 | 说明 |
| --- | --- | --- | --- |
| 无独立 CLI | 无 | 无 | 这是自然语言诊断 skill，不靠脚本执行。 |

## 如何使用这份矩阵

1. 先看命令默认 token 类型。
2. 如果这里给了 `已验证` 的明确 scope，优先按它申请。
3. 如果这里只写了 `权限族`，直接回该命令对应 API 文档确认，不要猜。
4. 遇到 `invalid_scope`、控制台搜不到、或 tenant/user 行为不一致时，回：
   - 官方 scope 总表
   - 对应 API 文档
   - `feishu-auth-and-scopes`
   - `feishu-api-diagnose`
