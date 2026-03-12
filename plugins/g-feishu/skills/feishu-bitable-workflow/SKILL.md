---
name: feishu-bitable-workflow
description: 当用户提出“创建飞书多维表格”“创建或修改 bitable 字段”“批量导入或更新记录”“读取或管理 bitable 视图”，或需要独立的 Feishu/Lark 多维表格工作流时，应使用此 skill。
---

# 飞书多维表格工作流

## 快速索引

- `1. 权限与默认行为`
- `2. 按任务选命令`
- `3. App 工作流`
- `4. Table 工作流`
- `5. Field 工作流`
- `6. Record 工作流`
- `7. View 工作流`
- `8. 输出规则`
- `9. 失败处理`
- `10. 附加资源`

## 1. 权限与默认行为

- 本 skill 已经是**真实 Bitable workflow**，不再只是 schema 草案或 payload 生成器。
- 默认 **user token 优先**。真实 Bitable 读写默认先使用内部 user token 运行时变量。
- 只有用户明确要求应用身份，或已知 app 对目标 base/table 有权限时，才切到 tenant token：
  - `--tenant-access-token`
  - `--use-tenant-token`
- 所有鉴权、scope、token 获取与刷新，都统一交给 Agent Skill `feishu-auth-and-scopes`。
- 如果 Bitable API 已经报错，但还不清楚是 app token、table id、field payload 还是权限问题，统一切到 Agent Skill `feishu-api-diagnose`。

### 1.1 首次真实写操作

首次真实写操作建议先确认：

- 本次要操作的目标：
  - `app_token`
  - `table_id`
  - `view_id`
- 是否应显式切到 tenant token
- 是否需要先读取当前字段定义再写记录

## 2. 按任务选命令

- 创建或复制一个多维表格应用：
  - `create-app`
  - `get-app`
  - `list-apps`
  - `update-app`
  - `copy-app`
- 创建、列取、修改、删除数据表：
  - `create-table`
  - `list-tables`
  - `update-table`
  - `delete-table`
  - `batch-create-tables`
  - `batch-delete-tables`
- 创建、列取、修改、删除字段：
  - `create-field`
  - `list-fields`
  - `update-field`
  - `delete-field`
- 创建、查询、更新、删除记录：
  - `create-record`
  - `list-records`
  - `update-record`
  - `delete-record`
  - `batch-create-records`
  - `batch-update-records`
  - `batch-delete-records`
- 读取、列取、修改、删除现有视图：
  - `create-view`
  - `get-view`
  - `list-views`
  - `update-view`
  - `delete-view`

示例提示词见 `examples/sample-prompts.md`。

## 3. App 工作流

适合这类请求：

- “创建一个新的 bitable 应用”
- “列出我当前可见的 bitable app”
- “复制这个 base”
- “把 app 改个名字”

命令：

- `create-app`
- `get-app`
- `list-apps`
- `update-app`
- `copy-app`

规则：

- `create-app` 需要明确 app 名称。
- `list-apps` 可以用 `--folder-token` 收窄范围；如果没有目标文件夹，就列当前可见 app。
- 复制 app 前要确认用户真的需要复制整个 base，而不是只增一张表。

## 4. Table 工作流

适合这类请求：

- “创建一张记录表”
- “列出这个 app 里的所有表”
- “把表重命名”
- “删除表”
- “批量创建或删除多张表”

命令：

- `create-table`
- `list-tables`
- `update-table`
- `delete-table`
- `batch-create-tables`
- `batch-delete-tables`

规则：

- `create-table` 支持直接附带字段定义。
- 真实写表前先确认 `app_token` 是否正确。
## 5. Field 工作流

适合这类请求：

- “增加一个负责人字段”
- “把状态字段改成单选”
- “列出当前字段”
- “删除临时字段”

命令：

- `create-field`
- `list-fields`
- `update-field`
- `delete-field`

规则：

- 任何记录写入前，优先 `list-fields` 看当前 schema。
- 常用字段类型已经做成脚本层一等支持，优先用这些别名而不是直接写数字类型：
  - `text`
  - `number`
  - `single_select`
  - `multi_select`
  - `datetime`
  - `checkbox`
  - `person`
  - `phone`
  - `link`
  - `attachment`
- `create-field` / `update-field` 支持常用 property 便捷参数：
  - `--option`
  - `--options-json`
  - `--options-file`
  - `--formatter`
  - `--date-formatter`
  - `--auto-fill`
- `update-field` 缺失值会自动从当前 schema 填充，但高风险字段仍要谨慎：
  - 用户
  - 日期
  - 单选 / 多选
  - 附件
  - relation

字段选择建议见 `references/field-strategy.md`。

## 6. Record 工作流

适合这类请求：

- “插入一条记录”
- “按条件找记录”
- “批量导入记录”
- “批量更新评分”
- “删除一批记录”

命令：

- `create-record`
- `list-records`
- `update-record`
- `delete-record`
- `batch-create-records`
- `batch-update-records`
- `batch-delete-records`

规则：

- 写记录前先明确字段名和字段类型，不要猜字段。
- 常用字段的标准化写入已经做成脚本层能力，不要求用户手写底层 Feishu 结构。
- 业务友好写法示例：

```json
{
  "fields": {
    "文本": "任务A",
    "评分": 2,
    "状态": "进行中",
    "标签": ["审批", "线上"],
    "日期": "2026-03-10T15:00:00+08:00",
    "已完成": false,
    "联系电话": "13800138000",
    "参考链接": {"text": "文档", "link": "https://example.com"},
    "负责人": ["ou_xxx"]
  }
}
```

- 读取结果也会做标准化：
  - 文本字段返回字符串
  - 单选返回单个选项名
  - 多选返回字符串数组
  - 日期返回毫秒时间戳
  - 复选框返回布尔值
  - 链接返回 `{text, link}`
  - 人员返回对象数组
- `list-records` 走 records/search API，可带：
  - `filter`
  - `sort`
  - `view_id`
- 批量写入优先分块执行，不要一次性对同一张表做大批量并行写入。
- `batch-delete-records` 现在已经是真实 API 能力，body 形态为 `records`。

写入与批量策略见 `references/write-strategy.md`。

## 7. View 工作流

适合这类请求：

- “创建一个新的 grid 视图”
- “读取这个视图”
- “列出这张表的视图”
- “修改视图名”
- “删除这个视图”

命令：

- `create-view`
- `get-view`
- `list-views`
- `update-view`
- `delete-view`

规则：

- 如果用户只是想看不同视图下的数据，优先使用已有 `view_id`。
- 修改视图前先 `list-views` 或 `get-view` 确认目标是否存在。

## 8. 输出规则

返回真实执行结果时，优先输出：

- `api_alias`
- `auth_mode`
- `app_token`
- `app_url`
- `table_id`
- `table_url`
- `field`
- `record`
- `record_ids`
- `view`
- `view_url`
- `has_more`
- `page_token`

如果未设置 `MY_LARK_WEB_BASE_URL`，写操作成功输出会返回 `web_link_notice`，提醒当前只返回稳定 ID，不返回租户内网页链接。

不要把响应裁成“只剩一句成功”。要保留后续继续操作所需的稳定标识符。

## 9. 失败处理

- 字段写入报错：
  - 先检查字段名、字段类型、property 结构
- 批量写入报错：
  - 先看是哪一批失败，再缩小输入规模
- 找不到 app/table/view：
  - 先确认 `app_token`、`table_id`、`view_id`
- 权限不明确：
  - 切到 `feishu-auth-and-scopes`
- 错误归因不清：
  - 切到 `feishu-api-diagnose`

## 10. 附加资源

- 字段建议：`references/field-strategy.md`
- 写入策略：`references/write-strategy.md`
- 示例提示词：`examples/sample-prompts.md`
- 回归清单：`tests/regression-checklist.md`
- 真实 helper：`scripts/feishu_bitable_helper.py`
