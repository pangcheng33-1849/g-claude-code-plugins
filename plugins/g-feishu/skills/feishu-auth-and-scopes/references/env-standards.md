# 环境变量标准

这套 Feishu skills 对外公开的最小环境变量标准只有：

- `MY_LARK_APP_ID`
- `MY_LARK_APP_SECRET`
- `MY_LARK_EMAIL`

## 公开最小变量

### 应用凭证

- `MY_LARK_APP_ID`
- `MY_LARK_APP_SECRET`

用于：

- 获取 `tenant_access_token`
- 发起设备授权或 OAuth
- 刷新 `user_access_token`

### 默认身份

- `MY_LARK_EMAIL`

用于：

- 默认分享文档
- 默认成员授权
- 作为邮箱身份的默认交接值

## 可选增强变量

- `MY_LARK_WEB_BASE_URL`

用于：

- 为 doc/wiki/base 等写操作结果构造可直接打开的租户内链接
  未设置时，相关 workflow 只返回稳定 ID，不伪造网页链接

## 内部运行时变量

下面这些变量属于 Agent 内部交接、缓存或高级覆盖项，不要求用户手工配置：

- `MY_LARK_USER_ACCESS_TOKEN`
- `MY_LARK_TENANT_ACCESS_TOKEN`
- `FEISHU_AUTH_CACHE_DIR`
- `FEISHU_DOC_TASK_DIR`

其中：

- token 变量用于在 skill 之间交接已获取的 token
- `FEISHU_AUTH_CACHE_DIR` 用于覆盖 user token 缓存目录
- `FEISHU_DOC_TASK_DIR` 仅用于覆盖文档导入异步状态目录，不属于公开最小依赖

## 正式交接规则

如果一个 skill 先通过 `feishu-auth-and-scopes` 获取了新 token，正式建议是：

1. 优先写入内部运行时 token 变量
2. 只有当前环境不适合持久化环境变量时，才回退到显式参数：
   - `--user-access-token`
   - `--tenant-access-token`

## 兼容别名

下面这些名称目前只应视为历史兼容，不应再作为新标准写进主文档：

- `FEISHU_EMAIL`
- `LARK_EMAIL`

如果后续新增或重写 skill，请只使用 `MY_LARK_*` 命名。
