# 参会人模型

要区分下面几类角色：

- organizer
- attendee
- watcher 或可选参会人
- 资源 / 会议室

当用户说“找个大家都有空的时间”时，忙闲查询是主动作，不是附带检查。

## tenant 创建事件时的最小验收规则

- 如果用 `tenant token` 创建事件，至少应添加一个真实用户参会人，否则用户往往无法直接验收这条事件。
- 推荐优先提供：
  - `--attendee-open-id`
  - 或 `--attendee-query`
- 如果只有邮箱或姓名：
  - 可传 `--attendee-email`
  - 或 `--attendee-query`
  - 或设置 `MY_LARK_EMAIL`
  - 但这条链路还需要环境里有可用的用户搜索 token，才能把邮箱或姓名解析成 `open_id`

## 当前脚本行为

- `create-event` 使用 `tenant token` 时：
  - 会先尝试解析默认参会人
  - 解析不到时直接报错
  - 解析到后，创建事件成功即调用 attendee API 追加参会人
  - 然后如果同时传了 `--user-access-token`，会尝试用它读取参会人视角事件，并返回 `preferred_app_link`
  - 如果参会人视角读取失败，则回退到 organizer `app_link`
- attendee API 默认也会带：
  - `need_notification = true`
