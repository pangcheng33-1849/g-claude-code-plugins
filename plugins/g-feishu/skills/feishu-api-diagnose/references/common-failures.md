# 常见失败类型

下面这些规则是经验性的第一轮归类，不是硬编码判决。  
真正诊断时，仍应结合：

- 原始错误文本
- HTTP 状态码
- `code` / `msg`
- 请求身份
- endpoint 路径
- 对象标识符类型

## 鉴权 / Scope

- token 类型错误
- 缺少用户授权
- 缺少应用权限
- 常见表象：
  - `403`
  - `forbidden`
  - `permission`
  - `scope`
- 典型下一步：
  - 先判断当前是 `tenant_access_token` 还是 `user_access_token`
  - 再检查应用 scope 与用户授权是否匹配
  - 必要时切到 `feishu-auth-and-scopes`

## 标识符问题

- 在需要 `open_id` 的地方误用了 `chat_id`
- 把 `thread_id` 当成 `message_id`
- 混淆了 wiki token 和 doc token
- 常见表象：
  - `404`
  - `not found`
  - `invalid ... id`
  - `file token invalid`
- 典型下一步：
  - 重新确认对象类型
  - 重新确认 parent chat / table / folder / wiki scope
  - 必要时切到 `feishu-search-and-locate`

## Payload 问题

- 时间戳格式错误
- 类型化对象的字段结构错误
- 把二进制资源获取和元数据获取混在一起
- 常见表象：
  - `param`
  - `invalid request`
  - `bad request`
  - `time format`
  - `RFC 3339`
  - `ISO 8601`
- 典型下一步：
  - 把请求缩到最小 payload
  - 明确时间字段的时区和格式
  - 检查字段名、字段层级和对象形态

## 运行层问题

- 被限流
- 分页后续请求缺失
- 搜索或列表请求范围过大
- 常见表象：
  - `429`
  - `rate limit`
  - `too many requests`
  - `cursor`
  - `page_token`
  - `pagination`
- 典型下一步：
  - 降低并发或减小批量大小
  - 对分页请求保持排序和过滤条件稳定
  - 复用服务端返回的 `page_token`

## 已知高价值错误码

### 230011

- 含义倾向：消息已不可用，无法继续对该消息做删除、回复或后续操作
- 常见场景：
  - 用旧 `message_id` 回复消息
  - 对已删除/已撤回消息继续操作
- 建议：
  - 刷新 thread 或消息上下文
  - 确认是否应该改用原始被引用消息
  - 继续排查 IM 路径时切到 `feishu-im-workflow`

### 231003

- 含义倾向：消息已不可拉取或不可变更
- 常见场景：
  - 读取已失效消息
  - 修改或删除不再可见的消息
- 建议：
  - 先确认消息是否已撤回、过期或跨容器
  - 再确认当前调用身份是否仍在目标 chat / thread 中

## 常见误区

- `404` 不一定都是“资源不存在”，也可能是路径错、容器错、token 类型错。
- `403` 不一定只是“缺权限”，也可能是用错了 token 身份，或者资源只对用户身份开放。
- 时间格式错误不一定只出现在 calendar，带截止时间、提醒、筛选窗口的 API 都可能触发。
- 分页问题经常被误判成“接口不稳定”，但更常见的根因是：`page_token`、排序、筛选条件前后不一致。
