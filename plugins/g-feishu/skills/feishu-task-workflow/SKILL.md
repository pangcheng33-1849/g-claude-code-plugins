---
name: feishu-task-workflow
description: 当用户提出“创建飞书任务”“同步待办到飞书任务”“创建任务清单”“更新任务状态”，或需要独立的 Feishu/Lark 任务工作流时，应使用此 skill。
---

# 飞书任务工作流

## 快速索引

- `1. 按任务选命令`
- `2. 鉴权默认规则`
- `3. 真实 Task v2 API 能力`
- `4. 任务处理总原则`
- `5. 失败处理`
- `6. 附加资源`

## 目的

把自由形式的工作事项整理成 Feishu/Lark 任务动作，并在需要时直接调用真实 Task v2 API。

处理范围：

- 创建任务
- 更新任务
- 修改完成状态
- 查询任务详情
- 删除任务
- 列取任务
- 添加或移除成员
- 添加提醒

## 1. 按任务选命令

- 创建任务
  - `scripts/feishu_task_helper.py create-task`
- 更新任务字段
  - `scripts/feishu_task_helper.py update-task`
- 完成任务
  - `scripts/feishu_task_helper.py complete-task`
- 恢复未完成
  - `scripts/feishu_task_helper.py reopen-task`
- 查询任务详情
  - `scripts/feishu_task_helper.py get-task`
- 删除任务
  - `scripts/feishu_task_helper.py delete-task`
- 列出任务
  - `scripts/feishu_task_helper.py list-tasks`
- 添加成员
  - `scripts/feishu_task_helper.py add-members`
- 移除成员
  - `scripts/feishu_task_helper.py remove-members`
- 添加提醒
  - `scripts/feishu_task_helper.py add-reminders`

更多示例见 `examples/sample-prompts.md`。

## 2. 鉴权默认规则

- `create-task / update-task / complete-task / reopen-task / get-task / delete-task / add-members / remove-members / add-reminders`
  - 默认 `user token` 优先
- `list-tasks`
  - 只支持 `user token`

显式参数优先级：

1. `--user-access-token`
2. `--tenant-access-token`
3. `--use-tenant-token`
4. 内部运行时 token 变量

默认协作方式：

- 真实任务操作优先通过 Agent Skill `feishu-auth-and-scopes` 获取或刷新 `user token`
- 只有在明确知道应用对目标任务有足够权限时，才显式切换到 `tenant token`
- 如果本轮先通过 `feishu-auth-and-scopes` 拿到了新 token，优先把它交接给运行时环境再继续执行；只有环境不适合持久化环境变量时，才改用显式参数。

## 3. 真实 Task v2 API 能力

当前正式支持：

- `create-task`
  - 真实创建任务
  - 支持 `summary / description / due / start / members / tasklists / reminders / docx_source`
- `update-task`
  - 真实更新任务字段
  - 支持 `summary / description / extra / due / start / mode / is_milestone / completed_at`
- `complete-task`
  - 把任务标记为已完成
- `reopen-task`
  - 把已完成任务恢复为未完成
- `get-task`
  - 查询任务详情
- `delete-task`
  - 删除任务
  - 注意：删除后短时间内再查询可能存在最终一致性延迟，应以稍后返回 `1470404` 为准
- `list-tasks`
  - 列出当前用户任务
  - 当前按官方接口边界只走 `my_tasks`
- `add-members`
  - 添加 assignee 或 follower
- `remove-members`
  - 移除 assignee 或 follower
- `add-reminders`
  - 添加任务提醒

当前明确不支持：

- 任务评论
- 子任务
- tasklist 自身的创建、重命名、删除
- 自定义字段的完整管理
- 把任务“假装创建成功”而实际没调 API

## 4. 任务处理总原则

### 5.1 先区分任务形态

把请求归类为：

- 单个任务
- 批量任务
- 任务清单
- 更新现有任务

### 5.2 规范化核心字段

尽量提取：

- `summary`
- `description`
- `due`
- `assignee`
- `followers`
- `tasklist`

如果字段缺失，优先生成安全的最小任务，而不是编造数据。

任务字段归一化原则见 `references/task-normalization.md`。

### 4.3 选择创建或更新策略

- 孤立任务
  - 直接 `create-task`
- 状态切换
  - 优先 `complete-task / reopen-task`
- 细字段修改
  - 用 `update-task`

### 4.4 成员和提醒单独处理

不要把成员或提醒修改混进普通 patch 里：

- 成员
  - `add-members / remove-members`
- 提醒
  - `add-reminders`

## 5. 失败处理

- token、scope、授权来源不清楚
  - 切到 Agent Skill `feishu-auth-and-scopes`
- 已发生真实 API 报错，但分不清是鉴权、对象 ID、参数还是调用顺序问题
  - 切到 Agent Skill `feishu-api-diagnose`
- 用户给的其实不是任务，而是会议安排、忙闲查询或日程变更
  - 切到 Agent Skill `feishu-calendar-workflow`

## 6. 附加资源

- `references/task-normalization.md`
- `examples/sample-prompts.md`
- `scripts/feishu_task_helper.py`
