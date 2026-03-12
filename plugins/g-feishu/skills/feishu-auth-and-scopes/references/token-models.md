# Token 模型

在这份说明之外，整套 skills 的统一环境变量标准见：

- `references/env-standards.md`

## 常见凭证类型

### 应用凭证

- `app_id`
- `app_secret`

本 skill 自带的 helper script 默认会从环境变量 `MY_LARK_APP_ID` 和 `MY_LARK_APP_SECRET` 读取这两个值，也可以继续通过命令行参数覆盖。

用于启动 tenant 级或 OAuth 流程。

### 默认联系邮箱

- `MY_LARK_EMAIL`

当其他飞书 workflow 需要在创建文档、导入文档或授予协作者权限后，自动把结果分享给当前用户时，优先从这个环境变量读取邮箱地址。  
如果没有设置，就应该显式要求用户提供邮箱，或者传入对应的 `--grant-email` 参数。

### Tenant Access Token

当动作是应用级权限、且不需要模拟真实用户时使用。

典型例子：

- 应用元数据
- 部分管理 / 配置查询

### User Access Token

当动作必须体现真实用户身份时使用。

典型例子：

- 用户私有数据
- 用户可见的文档 / 消息 / 任务 / 日程操作

默认环境变量：

- `MY_LARK_USER_ACCESS_TOKEN`

### Token 缓存

`feishu_auth_helper.py` 现在会把通过设备授权得到的 `user_access_token / refresh_token` 缓存到本地：

- `~/.feishu-auth-cache`
- 如果设置了 `FEISHU_AUTH_CACHE_DIR`，则优先使用该目录

缓存键默认按 `app_id` 区分；如果同一个应用需要多套用户身份，可以额外传 `--cache-key`。

缓存模型支持：

- 读取缓存并判断 access token 是否仍有效
- access token 失效后优先用 refresh token 刷新
- refresh token 也失效时，再重新走设备授权

### Tenant Token 环境变量

如果已经有现成 tenant token，也可以通过环境变量直接提供：

- `MY_LARK_TENANT_ACCESS_TOKEN`

## 决策规则

如果用户要操作自己的资源，且 Feishu 权限模型是用户侧授权，就按 user token 方案走。  
如果动作更偏应用配置，优先按应用或 tenant 身份规划。

## 命名收口

新文档和新 skill 统一使用：

- `MY_LARK_APP_ID`
- `MY_LARK_APP_SECRET`
- `MY_LARK_USER_ACCESS_TOKEN`
- `MY_LARK_TENANT_ACCESS_TOKEN`
- `MY_LARK_EMAIL`

像 `FEISHU_EMAIL`、`LARK_EMAIL` 这类名称，如果仍在脚本里出现，只应视为历史兼容，不应继续扩散到新的主文档说明。需要 `open_id` 时，应优先通过 Agent Skill `feishu-search-and-locate` 或 workflow 内部搜索能力按邮箱/姓名解析得到，而不是依赖环境变量。
