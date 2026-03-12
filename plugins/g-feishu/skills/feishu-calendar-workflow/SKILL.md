---
name: feishu-calendar-workflow
description: 当用户提出“创建飞书日程”“安排会议”“查询忙闲”“修改会议时间”“管理日程内容”，或需要独立的 Feishu/Lark 日程工作流时，应使用此 skill。
---

# 飞书日程工作流

## 快速索引

- `1. 何时使用`
- `2. 默认鉴权规则`
- `3. 按任务选命令`
- `4. 执行总原则`
- `5. 正式支持范围`
- `6. 当前边界`
- `7. 失败处理`
- `8. 附加资源`

## 1. 何时使用

以下场景使用本 skill：

- 创建飞书日程
- 查询多个用户的忙闲时间
- 读取、修改、删除某条日程
- 先把自然语言时间规范化，再生成或执行真实日程操作

如果用户本质上是在管理任务，切到 Agent Skill `feishu-task-workflow`。  
如果已经报错但还不能判断是时间格式、权限、calendar_id 还是 endpoint 问题，切到 Agent Skill `feishu-api-diagnose`。  
如果缺 token 或 user/tenant 身份不明确，切到 Agent Skill `feishu-auth-and-scopes`。

## 2. 默认鉴权规则

- `create-event`
  - 默认 `tenant token` 优先
  - 如果环境支持 AskUserQuestion / `request_user_input`，首次写操作优先问用户这次创建日程使用 `tenant token` 还是 `user token`
  - 如果最终使用 `tenant token` 创建事件，至少应把目标用户加为参会人，优先级如下：
    1. `--attendee-open-id`
    2. `--attendee-query`
    3. `--attendee-email` 或 `MY_LARK_EMAIL`，前提是环境里还有可用的用户搜索 token 可把邮箱或姓名解析成 `open_id`
- `list-calendars / list-events / get-event / update-event / delete-event / freebusy`
  - 默认 `user token` 优先
- 显式传 `--tenant-access-token` 或 `--use-tenant-token`
  - 才切到 `tenant token`
- 显式传 `--user-access-token`
  - 始终优先于环境变量
- 没有显式 token 时，脚本按内部运行时 token 变量顺序自动选择：
  1. `create-event`: tenant 优先，再回退 user
  2. 其他命令: user 优先，再回退 tenant
- 如果本轮先通过 Agent Skill `feishu-auth-and-scopes` 拿到了新 token，优先把它交接给运行时环境再继续调本 skill；只有环境不适合持久化环境变量时，才改用显式参数。

原因：

- 创建日程更偏组织内自动化动作，优先 tenant 更稳
- 忙闲和读取主日历操作通常强依赖用户身份

首次创建日程时，如果环境支持 AskUserQuestion / `request_user_input`，优先先问一次本次写操作用哪种权限，推荐把 `tenant token` 放第一个选项。最小 schema 可以是：

```json
{
  "questions": [
    {
      "header": "日程权限",
      "id": "calendar_write_auth_mode",
      "question": "这次创建飞书日程优先使用哪种权限？",
      "options": [
        {
          "label": "Tenant Token (Recommended)",
          "description": "适合组织内正式日程创建和通知。"
        },
        {
          "label": "User Token",
          "description": "适合明确要以个人身份写入个人日历。"
        }
      ]
    }
  ]
}
```

如果环境不支持 AskUserQuestion，直接按本 skill 的默认规则执行：`create-event` 默认 `tenant token` 优先。

## 3. 按任务选命令

- 列出现有日历  
  用 `scripts/feishu_calendar_helper.py list-calendars`
- 列某个日历里的事件  
  用 `scripts/feishu_calendar_helper.py list-events`
- 创建日程  
  用 `scripts/feishu_calendar_helper.py create-event`
- 获取单条日程详情  
  用 `scripts/feishu_calendar_helper.py get-event`
- 修改日程标题、描述、时间、提醒  
  用 `scripts/feishu_calendar_helper.py update-event`
- 删除日程  
  用 `scripts/feishu_calendar_helper.py delete-event`
- 查询忙闲  
  用 `scripts/feishu_calendar_helper.py freebusy`
更多触发语句见 `examples/sample-prompts.md`。

## 4. 执行总原则

### 4.1 先把时间规范化

始终把自然语言时间转成明确的：

- 日期
- 开始时间
- 结束时间
- 时区

参考：`references/time-normalization.md`

### 4.2 选择时间时总是先考虑用户时区

- 默认按用户当前时区理解“上午 / 下午 / 晚上”
- 给候选时间时，优先落在以下窗口：
  - `10:30 - 12:00`
  - `14:00 - 18:00`
  - `17:00 - 21:00`
- 如果是会议日程：
  - 时长至少 `30` 分钟
  - 一般不要超过 `60` 分钟
- 如果用户没有指定时区，但上下文明确是中国团队，默认 `Asia/Shanghai`
- 如果用户跨时区协作，先把候选时间转换到用户时区再确认

### 4.3 缺 `calendar_id` 时先列日历

- 默认主日历不接受字面量 `primary`
- 让脚本先通过 `list-calendars` 解析真实 `primary_calendar_id`
- 不要自己猜 `calendar_id`

### 4.4 忙闲查询优先 user token

- `freebusy` 对用户身份最稳定
- 需要多个用户时，逐个 `--user-id` 传入
- 当前 helper 会按用户逐个请求并汇总结果

### 4.5 参会人和资源先明确，再决定是否创建

当前脚本已经支持在 `tenant token` 创建事件后追加用户参会人，但尚未把更完整的参会人管理、会议室写操作做成稳定 CLI。  
如果用户要求“先查大家都有空”，忙闲查询是主动作，不是附带检查。  
创建事件时，脚本默认会带：

- `need_notification = true`
- `attendee_ability = can_modify_event`

如果 `create-event` 最终走 `tenant token`，而又没有办法解析出至少一个用户 `open_id` 作为参会人，脚本会直接报错，而不是创建一条用户无法验收的应用日程。

`create-event` 成功后，总是优先返回 `preferred_app_link` 作为用户验收链接：

- 如果能用内部 user token 运行时变量读取到参会人视角事件，则 `preferred_app_link` 会指向参会人可直接打开的链接
- 否则回退到服务端原始返回的 organizer `app_link`

参考：`references/attendee-model.md`

## 5. 正式支持范围

### 5.1 真实 Calendar v4 API

当前 helper 已正式支持：

- `list-calendars`
- `list-events`
- `create-event`
- `get-event`
- `update-event`
- `delete-event`
- `freebusy`

### 5.2 当前正式输入边界

- 直接用真实 Calendar v4 API 命令
- 时间规范化仍由脚本内部完成，但不再单独暴露 payload-only 命令
- 搜索候选时间、判断会议时长、决定是否先查忙闲，这些属于 Agent 的自然语言规划能力

## 6. 当前边界

- 当前**没有**把“增删参会人”“会议室预定”“会议室审批状态”做成稳定 CLI
- 当前**没有**单独做 recurring rule / 重复日程编辑器
- 复杂多人忙闲编排仍依赖 Agent 结合 `freebusy` 结果自然语言决策
- 默认日历解析依赖 `list-calendars`，不接受硬编码 `primary`
- `create-event` 默认 tenant 优先，但如果你明确要以个人身份写入自己的日历，应显式传 `--user-access-token`

如果用户要求高度复杂的排期优化，先输出时间窗口和冲突，再由 Agent 做自然语言协调，不要把策略硬编码进脚本。

## 7. 失败处理

- 如果缺 token 或 token 过期  
  切到 Agent Skill `feishu-auth-and-scopes`
- 如果 API 已报错，但还分不清是时间格式、用户 ID、calendar_id 还是权限  
  切到 Agent Skill `feishu-api-diagnose`
- 如果用户给的是任务场景而不是日程场景  
  切到 Agent Skill `feishu-task-workflow`

## 8. 附加资源

- `references/time-normalization.md`
- `references/attendee-model.md`
- `examples/sample-prompts.md`
- `scripts/feishu_calendar_helper.py`
