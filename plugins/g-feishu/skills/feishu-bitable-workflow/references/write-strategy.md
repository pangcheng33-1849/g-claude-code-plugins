# 写入策略

## 记录写入前

- 先确认：
  - `app_token`
  - `table_id`
  - 字段定义
- 如果用户只给了自然语言描述，不要直接猜字段结构，先 `list-fields`

## 单条写入

- `create-record`
- `update-record`
- `delete-record`

适合：

- 单条修复
- 小范围改值
- 精准删除

推荐把业务友好值直接交给脚本归一化，例如：

```json
{
  "fields": {
    "文本": "任务A",
    "评分": "4.5",
    "状态": "已完成",
    "标签": ["审批", "线上"],
    "日期": "2026-03-10T15:00:00+08:00",
    "已完成": true,
    "联系电话": "13800138000",
    "参考链接": {"text": "文档", "link": "https://example.com"},
    "负责人": ["ou_xxx"]
  }
}
```

脚本会自动归一化：

- 数字字符串 -> 数字
- 日期字符串 -> 毫秒时间戳
- 单选 / 多选 -> 选项值
- 链接 -> `{text, link}`
- 人员 -> `[{id: ...}]`

## 批量写入

- `batch-create-records`
- `batch-update-records`
- `batch-delete-records`

适合：

- 批量导入
- 批量修正
- 批量清理

建议：

- 优先分批执行
- 保留输入与输出的稳定映射
- 删除前先保留 record id 清单
- `list-records` 的返回值会同时给：
  - 归一化后的 `records`
  - 原始 API 返回的 `records_raw`

## 视图操作

- 视图只支持：
  - `create-view`
  - `get-view`
  - `list-views`
  - `update-view`
  - `delete-view`
