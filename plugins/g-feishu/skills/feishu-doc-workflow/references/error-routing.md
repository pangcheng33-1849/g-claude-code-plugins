# 错误路由

本文件定义 `feishu-doc-workflow` 在权限、身份和错误归因不清时的正式路由策略。

## 1. 缺 token / scope

缺 token 或 scope 时：

- 切到 Agent Skill `feishu-auth-and-scopes`

## 2. 应用身份失败

如果当前是应用身份，且报错里出现：

- `403`
- `forbidden`
- `no permission`
- `Unauthorized`
- `1069902`
- `1770032`
- `2890005`

则：

1. 不要继续反复用 tenant token 重试
2. 切到 Agent Skill `feishu-auth-and-scopes`
3. 获取或刷新 user token
4. 再通过 `--user-access-token` 重试当前命令

这是方案 A 的正式边界：

- 文档脚本内部不做自动降级
- 由 agent 在 skill 协同层完成 `auth -> retry`

## 3. 错误归因不清

如果拿到了错误响应，但分不清是：

- 鉴权
- 标识符
- payload
- 分页
- 限流

则切到 Agent Skill `feishu-api-diagnose`。
