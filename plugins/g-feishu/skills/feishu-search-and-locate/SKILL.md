---
name: feishu-search-and-locate
description: 当用户提出“搜索飞书用户”“搜索飞书文档”“查聊天记录”“查消息里的文件”“定位某个 Feishu 对象”，或在执行下一步动作前需要跨域搜索 Feishu/Lark 对象时，应使用此 skill。
---

# 飞书搜索与定位

## 1. 鉴权规则

- 所有搜索命令都需要 token，必须在调用脚本之前获取。
- 典型流程：先使用 skill `feishu-auth-and-scopes` 的 `resolve-token` 获取 token，从返回的 JSON 中提取 `access_token`，再通过 `--user-access-token` 传给脚本。
- 搜索和定位经常依赖用户可见性；需要真实调用搜索接口时，默认优先 user token。
- 如果环境明确是应用级搜索自动化，并且应用本身已对目标对象范围有权限，才显式切 tenant token（通过 `--tenant-access-token`）。
- token 获取、缓存、refresh 和 scope 诊断统一交给 skill `feishu-auth-and-scopes`；本 skill 只消费通过命令行参数显式传入的 token。

## 2. 目的

在其他工作流真正执行之前，先定位正确的 Feishu/Lark 对象。

这个 skill 不只是“搜索”，而是要产出另一个动作能够消费的稳定对象定位信息。

目标对象包括：

- 用户
- 文档 / wiki 页面
- chat

## 3. 当前正式支持

- 用 `scripts/feishu_locate_helper.py search-doc` 定位文档（底层实现：`search/v2/doc_wiki/search`）
- 用 `scripts/feishu_locate_helper.py search-wiki` 定位 wiki 页面（底层实现：`wiki/v1/nodes/search`）
- 用 `scripts/feishu_locate_helper.py search-chat` 定位 chat（底层实现：`im/v1/chats/search`）
- 用 `scripts/feishu_locate_helper.py search-user` 按姓名或邮箱定位用户（底层实现：`search/v1/user`）
- 把搜索结果收敛成下游动作可消费的稳定标识符，并明确交接给哪个 Agent Skill

当前正式边界：

- helper 现在直接实现了 `user/doc/wiki/chat` 四类真实搜索 API
- 用户定位优先走 `scripts/feishu_locate_helper.py search-user`
- 除 `user/doc/wiki/chat` 之外，其他搜索当前正式不支持

## 4. 执行模式

### 模式 A：已有搜索接口

优先使用现有的搜索或列表接口。

对于用户搜索，优先顺序是：

- `scripts/feishu_locate_helper.py search-user` 处理姓名或邮箱查询
- 已经拿到 `open_id / user_id / union_id` 时，再用通讯录详情接口补全字段

对于文档、wiki、chat，优先顺序是：

- `scripts/feishu_locate_helper.py search-doc`
- `scripts/feishu_locate_helper.py search-wiki`
- `scripts/feishu_locate_helper.py search-chat`
- 如果脚本结果仍然有歧义，再结合自然语言缩小范围并人工比较候选结果

### 模式 B：搜索策略由 Agent 自然语言规划

如果没有可直接调用的搜索接口，或结果仍然有歧义：

- 先判断候选对象类型
- 用自然语言收窄搜索空间，具体策略见 `references/filtering-strategy.md`
- 如果环境已经返回一组噪声较大的候选集，用自然语言比较候选项的标题、owner、更新时间和上下文匹配度
- 最终给出最佳筛选条件，以及继续执行所需的下一个标识符

## 5. 核心工作流

### 1. 判断对象类别

先决定用户要找的是：

- 某个人
- 某篇文档
- 某个 chat

### 2. 收窄搜索空间

尽量组合使用：

- 关键词
- 时间范围
- owner 或发送者
- chat 范围
- wiki 或 drive 范围

只有在没有更好办法时，才做无范围搜索。

筛选策略示例见 `references/filtering-strategy.md`。

### 3. 返回定位信息，而不是只返回匹配结果

一个成功结果通常应包含：

- 最佳候选项
- 稳定标识符
- 置信度或歧义说明
- 现在可以继续执行的下一步动作

### 4. 在合适时做交接

一旦找到目标：

- 文档 -> `feishu-doc-workflow`
- 鉴权阻塞 -> `feishu-auth-and-scopes`
- chat / 消息管理 -> `feishu-im-workflow`
- 任务、日程等业务对象 -> 对应的工作流 skill

交接模式示例见 `references/handoff-patterns.md`。

如果只是想快速判断该怎么搜、该把结果交给谁，先看 `examples/sample-prompts.md`。

## 6. 失败处理

如果候选项太多，返回带简短比较理由的 shortlist。  
如果搜索条件太少，再补问一个消歧信息。

如果搜索接口或列表接口本身已经报错，且还不能判断是鉴权、范围、分页还是对象 ID 问题，切换到 `feishu-api-diagnose` 做排障，再回到定位流程。

## 7. 附加资源

- `references/filtering-strategy.md`
- `references/handoff-patterns.md`
- `examples/sample-prompts.md`
- `scripts/feishu_locate_helper.py`
