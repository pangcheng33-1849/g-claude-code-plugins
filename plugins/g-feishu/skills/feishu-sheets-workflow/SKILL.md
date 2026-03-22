---
name: feishu-sheets-workflow
description: 当用户提出"创建飞书电子表格""读写单元格""查找替换内容""管理工作表"，或需要独立的 Feishu/Lark Sheets 工作流时，应使用此 skill。
---

# 飞书电子表格工作流

## 快速索引

- `1. 权限与默认行为`
- `2. 按任务选命令`
- `3. 电子表格工作流`
- `4. 工作表工作流`
- `5. 读写工作流`
- `6. 查找替换工作流`
- `7. 输出规则`
- `8. 失败处理`

## 1. 权限与默认行为

- 本 skill 是**真实 Sheets workflow**，直接调用飞书电子表格 API。
- **所有命令在调用前必须先获取 token**。典型流程：
  1. 使用 skill `feishu-auth-and-scopes` 的 `resolve-token` 命令获取 token
  2. 从返回的 JSON 中提取 `access_token`
  3. 通过 `--user-access-token` 或 `--tenant-access-token` 参数传入
- 默认 **user token 优先**。
- 如果 Sheets API 报错但原因不明，切到 skill `feishu-api-diagnose`。

**所需 scope（按操作）：**

| 操作 | 所需 scope（任一） |
|------|-------------------|
| 创建电子表格 | `sheets:spreadsheet:create` |
| 查看/读取 | `sheets:spreadsheet:read` |
| 写入/插入/追加/清除/替换 | `sheets:spreadsheet:write_only` |
| 查询元信息 | `sheets:spreadsheet.meta:read` |

如果使用 user token 时报 99991679（scope 不足），需要通过 `feishu-auth-and-scopes` 的 `auth-user --scopes sheets:spreadsheet:create sheets:spreadsheet:read sheets:spreadsheet:write_only sheets:spreadsheet.meta:read offline_access` 重新授权。

## 2. 按任务选命令

| 任务 | 命令 |
|---|---|
| 创建电子表格 | `create-sheet` |
| 获取表格信息 | `get-sheet-info` |
| 列出工作表 | `query-sheets` |
| 创建工作表 | `create-worksheet` |
| 复制工作表 | `copy-worksheet` |
| 删除工作表 | `delete-worksheet` |
| 读取单元格 | `read-ranges` |
| 写入单元格 | `write-cells` |
| 插入行 | `insert-rows` |
| 追加行 | `append-rows` |
| 清除范围 | `clear-ranges` |
| 查找单元格 | `find-cells` |
| 查找替换 | `replace-cells` |

## 3. 电子表格工作流

适合这类请求："创建一个新的电子表格"、"查看表格元信息"、"列出有哪些工作表"。

- `create-sheet --title <name> [--folder-token <token>]` — 创建到 Drive 文件夹（folder-token 需要 user token）
- `create-sheet --title <name> --wiki-parent-node <node_token>` — 创建到 wiki 节点下（tenant token 需先在 wiki 中添加文档应用）
- `get-sheet-info --spreadsheet-token <token>`
- `query-sheets --spreadsheet-token <token>` — 返回 `sheet_ids` 列表，后续操作需要

## 4. 工作表工作流

适合这类请求："增加一个工作表 tab"、"复制这个 sheet"、"删掉这张子表"。

- `create-worksheet --spreadsheet-token <token> --title <name> [--index <n>]`
- `copy-worksheet --spreadsheet-token <token> --source-sheet-id <id> [--title <name>]`
- `delete-worksheet --spreadsheet-token <token> --sheet-id <id>`

## 5. 读写工作流

适合这类请求："读取 A1:D10"、"写入成绩"、"插入新行"、"追加数据"、"清空区域"。

读取：
- `read-ranges --spreadsheet-token <t> --sheet-id <s> --range A1:C5 [--range D1:F5]`

写入（三种数据输入方式）：
- `--values-json` — 内联 3D rich text JSON
- `--values-file` — 文件路径
- `--simple-values` — 简化 2D 数组，自动转换为 rich text

```bash
# 简化写入示例
write-cells --spreadsheet-token <t> --sheet-id <s> --range A1:B2 \
  --simple-values '[["姓名","分数"],["Alice",95]]'
```

- `write-cells` — 覆盖写入指定范围
- `insert-rows` — 在范围处插入行，已有行下移
- `append-rows` — 追加到范围最后一个非空行之后
- `clear-ranges` — 清除一个或多个范围的内容（最多 10 个）

限制：每次 ≤10 ranges、≤5000 cells、每 cell ≤40000 chars。

## 6. 查找替换工作流

适合这类请求："找出所有包含 xxx 的单元格"、"把旧名字全部替换成新名字"。

- `find-cells --spreadsheet-token <t> --sheet-id <s> --find <text> [--match-case] [--search-by-regex]`
- `replace-cells --spreadsheet-token <t> --sheet-id <s> --find <text> --replacement <new> [--match-case]`

替换限制：≤5000 cells。

## 7. 输出规则

返回结果优先包含：
- `api_alias`、`auth_mode`
- `spreadsheet_token`、`spreadsheet_url`（需配置 `MY_LARK_WEB_BASE_URL`）
- `sheet_id`、`sheet_ids`

不要把响应裁成"只剩一句成功"。保留后续操作所需的标识符。

## 8. 失败处理

- 范围格式错误 — 检查 range 是否为 `A1:B2` 格式
- sheet_id 不存在 — 先 `query-sheets` 获取有效列表
- 权限不足 — 切到 `feishu-auth-and-scopes`
- 错误归因不清 — 切到 `feishu-api-diagnose`

## 附加资源

- 单元格数据结构与范围格式：`references/sheets-api.md`
- 真实 helper：`scripts/feishu_sheets_helper.py`
