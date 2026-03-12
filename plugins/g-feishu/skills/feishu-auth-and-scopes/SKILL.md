---
name: feishu-auth-and-scopes
description: 当用户提出“获取飞书 token”“排查飞书权限”“做 OAuth 授权”“判断 scope 是否足够”，或需要处理 Feishu/Lark 应用凭证、tenant token、user token 与权限归因时，应使用此 skill。
---

# 飞书鉴权与权限范围

## 目的

在没有预装飞书工具的环境中，也能完成 Feishu/Lark 凭证规划、token 获取、OAuth 排查和 scope 诊断。

用这个 skill 回答以下问题：

- 需要哪一种凭证
- 应该怎么拿到它
- 当前 token 或 scope 是否足够
- 下一步应该由管理员、用户还是应用 owner 来处理

## 何时使用

当用户需要以下任一能力时触发：

- 规划应用凭证
- 获取 tenant access token
- 获取 user access token
- 搭建 OAuth 流程
- 诊断 scope 不匹配
- 区分应用权限问题和用户权限问题

除非阻塞点明显是鉴权相关，否则不要把它作为文档、任务、日程、多维表格或群聊工作流的主 skill。

## 执行模式

### 模式 A：已有 Lark/Auth 工具链

如果环境里已经暴露了：

- Lark/Feishu MCP 工具
- 辅助脚本
- OAuth 回调能力
- token 获取命令

直接用这些能力执行。

真正执行前，仍然先判断 token 类型：

- 只有应用凭证
- tenant access token
- user access token
- refresh token / `offline_access`

### 模式 B：没有现成工具

如果没有直接可用的工具链，给出最小可执行路径：

- 优先使用 `scripts/feishu_auth_helper.py` 生成 OAuth URL、执行设备授权、缓存/刷新 user token、获取 tenant token，以及做第一轮分类；这个脚本是 auth skill 自己的独立运行时
- 明确指出需要的凭证类型
- 说明应该去哪里获取
- 必要时提供 curl 或 Python 示例
- 说明下一步还需要用户提供什么数据

如果当前没有运行路径，不要假装这个动作已经可执行。

### 环境约定

本仓库对外公开的最小环境变量标准只有：

- `MY_LARK_APP_ID`
- `MY_LARK_APP_SECRET`
- `MY_LARK_EMAIL`（当其他飞书 workflow 需要默认分享文档或授权协作者时使用）

如果环境变量已设置，可以省略 `--app-id` 和 `--app-secret`。  
如果需要覆盖默认值，继续传命令行参数即可。

补充说明：

- `MY_LARK_USER_ACCESS_TOKEN`
- `MY_LARK_TENANT_ACCESS_TOKEN`

属于内部运行时 token 交接变量，不要求用户手工设置；正常使用时应先通过本 skill 获取或刷新 token，再由 Agent 在当前运行环境里交接给下游 skill。

本 skill 的 user token 缓存默认落在：

- `~/.feishu-auth-cache`
- 如果设置了 `FEISHU_AUTH_CACHE_DIR`，则优先使用该目录

完整环境变量标准见：

- `references/env-standards.md`

最小必要权限清单见：

- `references/required-scopes.md`

完整 CLI 权限矩阵见：

- `references/cli-scope-matrix.md`

### token 交接标准

本仓库里的 Feishu workflow skill 统一采用下面的 token 交接方式：

1. 先通过 `auth-user`、`refresh-user-token`、`resolve-token` 或 `tenant-token` 获取 token
2. 如果当前运行环境支持写会话级环境变量，优先把 token 写入内部运行时变量，供后续 skill 复用
3. 如果环境不能稳定持久化环境变量，再显式传 `--user-access-token` 或 `--tenant-access-token`

也就是说，本 skill 的正式建议不是“让用户手工 export token”，而是由 Agent 先获取 token，再以内部运行时变量或显式参数的方式交接给后续 skill。

常用命令：

- `auth-user`
  用设备授权获取并缓存 `user_access_token`
- `refresh-user-token`
  用缓存或显式传入的 `refresh_token` 刷新 user token
- `resolve-token`
  统一从显式参数、环境变量、本地缓存、refresh 或设备授权里解析可用 token
- `show-token-meta`
  查看缓存状态、过期时间和来源
- `clear-token-cache`
  清理指定 app/cache key 的本地 user token 缓存

## 核心工作流

### 1. 识别所需身份

判断本次操作需要的是：

- 应用身份
- tenant 身份
- 用户身份

始终优先使用能完成任务的最低权限身份。

### 2. 归类失败或需求

把当前情况归到下列类别之一：

- 缺少应用凭证
- 缺少 tenant token
- 缺少 user token
- 应用 scope 不足
- 用户 scope 不足
- 回调或 OAuth 流程配置错误

### 3. 指定正确的修复责任人

明确标注谁需要动作：

- 应用管理员
- tenant 管理员
- 当前用户
- 应用 owner

不要混淆这些角色。很多 Feishu 失败表象类似，但真正责任人不同。

### 4. 给出下一步动作

优先给出直接可执行的下一步：

- 具体的 token endpoint 流程
- 具体的 OAuth 步骤
- 具体需要检查的 scope
- 仍然缺失的具体值

只要问题进入“到底该申请哪些 scope”这一层，优先参考：

- `references/required-scopes.md`
- `references/cli-scope-matrix.md`

其中：

- `references/required-scopes.md` 只保留最常用、最稳定、已经验证过的最小权限
- `references/cli-scope-matrix.md` 按 skill / CLI 命令分组，覆盖本仓库当前所有公开命令的默认 token 类型与权限范围

更细或更少见的 scope 直接回官方文档查，不在本地维护伪全量表。

不要只说“检查权限”，必须说明是哪个层面的权限。

## 输出规则

始终按以下顺序回答：

1. 所需身份或缺失前置条件
2. 根因分类
3. 下一步动作
4. 由谁执行

如果没有凭证就无法继续，要明确说明，并列出继续所需的最小输入。

## 附加资源

- `references/env-standards.md`
- `references/token-models.md`
- `references/scope-triage.md`
- `references/required-scopes.md`
- `references/cli-scope-matrix.md`
- `examples/sample-prompts.md`
- `scripts/feishu_auth_helper.py`
