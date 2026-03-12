# 字段选择策略

真实写入前，优先先看当前字段定义：

- `list-fields --app-token ... --table-id ...`

高风险字段：

- 用户 / 成员
- 日期 / 日期时间
- 单选 / 多选
- 附件
- relation

常用字段别名（脚本层已做一等支持）：

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

常见建模建议：

- `状态`：优先 `single_select`
- `标签`：优先 `multi_select`
- `负责人`：优先 `person`
- `截止时间`：优先 `datetime`
- `是否完成`：优先 `checkbox`
- `参考资料`：优先 `link`

建议：

- 仅当你明确知道字段类型和 property 结构时，才直接 `create-field` 或 `update-field`
- 对常用字段，优先使用脚本层别名和 property 便捷参数，而不是手写整数类型：
  - `--type single_select --option 待确认 --option 进行中 --option 已完成`
  - `--type datetime --date-formatter yyyy/MM/dd --auto-fill false`
- 不要把“看起来像字符串”的字段一律写成文本
- 批量导入前，先确认目标字段名和 CSV / JSON 键名一一对应

最稳的顺序：

1. `list-fields`
2. 确认字段名与字段类型
3. 必要时 `create-field` 或 `update-field`
4. 再做记录写入
