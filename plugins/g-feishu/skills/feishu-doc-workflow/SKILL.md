---
name: feishu-doc-workflow
description: 当用户提出“读取飞书文档”“创建飞书文档”“更新飞书文档”“导出飞书文档为 Markdown”“处理飞书文档里的图片或附件”，或需要独立的 Feishu/Lark 文档或 wiki 工作流时，应使用此 skill。
---

# 飞书文档工作流

## 目的

处理独立的 Feishu/Lark 文档与 wiki 工作流：

- 读取正文、图片、白板、附件
- 创建、更新、导入文档
- 列举文件夹和 wiki 容器中的文档
- 分享文档、调整协作者权限、转移 owner
- 读取评论、创建全文评论

优先使用现成的 Feishu/Lark MCP 或连接器；没有现成工具时，改用 `scripts/feishu_doc_helper.py`。

## 快速索引

- [1. 鉴权规则](#1-鉴权规则)
- [2. 按任务选命令](#2-按任务选命令)
- [3. 执行总原则](#3-执行总原则)
- [4. 首次写操作先确认权限模式](#4-首次写操作先确认权限模式)
- [5. 读取与媒体](#5-读取与媒体)
- [6. 创建更新与导入](#6-创建更新与导入)
- [6.5 飞书扩展写法](#65-飞书扩展写法)
- [7. 协作权限与评论](#7-协作权限与评论)
- [8. 容器列举与定位](#8-容器列举与定位)
- [9. 输出规则](#9-输出规则)
- [10. 失败处理](#10-失败处理)
- [11. 附加资源](#11-附加资源)

## 1. 鉴权规则

### 1.1 Token 必须在调用前获取

所有需要鉴权的命令，都**必须在调用前拿到 token**。典型流程：

1. 使用 skill `feishu-auth-and-scopes` 的 `resolve-token` 获取 token
2. 从返回的 JSON 中提取 `access_token`
3. 通过 `--user-access-token` 或 `--tenant-access-token` 传给本 skill 的命令

不要依赖环境变量传递 token — 始终使用显式参数。

### 1.2 默认鉴权偏好

默认 **user token 优先**（通过 `--user-access-token` 传入）：

- `create-doc`
- `update-doc`
- `fetch-content`
- `list-docs`
- `resolve-wiki-node`
- `share-doc`
- `update-share`
- `remove-share`
- `transfer-owner`
- `import-doc`

默认 **tenant token 优先**（通过 `--tenant-access-token` 传入）：

- `get-comments`
- `add-comments`

如需覆盖默认偏好，可传另一种 token 或加 `--use-tenant-token` 标志。

### 1.3 其他身份相关变量

- 自动授权默认成员邮箱：`MY_LARK_EMAIL`

## 2. 按任务选命令

| 任务 | 优先命令 | 说明 |
| --- | --- | --- |
| 规范化 URL / token | `extract-ref` | 先把 `docx/wiki/folder` 链接转成稳定引用 |
| 读取正文 | `fetch-content` | 默认只读正文 |
| 读取正文并处理图片 / 白板 / 附件 | `fetch-content --include-media --save-image-manifest` | 会输出 `media_summary / attachment_summary / image_understanding / media_failures` |
| 创建文档并直接写入文本 | `create-doc` | 走 `create -> convert -> create descendant`，失败时再回退 parser |
| 更新文档并直接写入文本 | `update-doc` | 优先局部 patch；复杂长文改走 `overwrite` |
| 导入本地文件 | `import-doc` | 适合 `.md/.html/.docx/.txt` 整体导入 |
| 预判命令会走哪条路线 | `api-plan` | 用于解释 `direct_text_write / file_import / parser_fallback` |
| 规范化 Markdown | `normalize-markdown` | 创建 / 更新前先清洗输入 |
| 列举文件夹 / wiki 容器中的文档 | `list-docs` | 支持 folder、wiki node、wiki space |
| `docx token` 反查 `wiki node` | `resolve-wiki-node` | 处理知识库场景 |
| 给已有文档补授权 | `share-doc` | 新增协作者 |
| 调整协作者权限 | `update-share` | 更新已有协作者权限 |
| 移除协作者 | `remove-share` | 删除已有协作者权限 |
| 转移 owner | `transfer-owner` | 文档 owner 迁移 |
| 读取评论 | `get-comments` | 支持全文评论和划词评论读取 |
| 创建全文评论 | `add-comments` | 当前只支持全文评论创建 |

常见自然语言触发方式见：

- `examples/sample-prompts.md`

## 3. 执行总原则

### 3.1 优先级

1. 优先使用现成 MCP / 连接器 / 官方工具。
2. 没有现成工具时，使用 `scripts/feishu_doc_helper.py`。
3. 缺 token 时，切到 Agent Skill `feishu-auth-and-scopes`。
4. 拿到错误响应但无法判断根因时，切到 Agent Skill `feishu-api-diagnose`。

执行模式和工具优先级细节见：

- `references/execution-modes.md`

### 3.2 目标解析

优先接受这些稳定入口：

- `docx` 链接
- `wiki` 链接
- `folder` 链接
- `folder_token`
- `wiki_space`
- `wiki_node`
- 文档 token

当前 **不支持** “my_library / 我的文档库” 这种抽象入口。  
如果用户说“从我的文档库里找”，要求用户改为提供上述任一明确入口。

### 3.3 复杂长文边界

不再继续优化复杂长文的精细 patch。  
对复杂长文更新，正式兜底方案是：

1. 先读取全文
2. 在本地 Markdown 中修改
3. 再执行 `update-doc --mode overwrite`

如果用户坚持复杂局部编辑，要求用户自己拆成更小的标题范围或 selection。

## 4. 首次写操作先确认权限模式

首次执行这些“写”操作时：

- `create-doc`
- `update-doc`
- `import-doc`
- `share-doc`
- `update-share`
- `remove-share`
- `transfer-owner`
- `add-comments`

如果用户还没有明确说明用 `tenant token` 还是 `user token`，优先尝试用 AskUserQuestion 对应的 `request_user_input` 进行确认。

推荐 schema：

```json
{
  "questions": [
    {
      "header": "权限方式",
      "id": "write_auth_mode",
      "question": "这次首次写入飞书文档时，你希望优先使用哪种权限身份？",
      "options": [
        {
          "label": "User Token (Recommended)",
          "description": "更适合访问用户本人有权限、但应用权限可能不足的文档、文件夹或 wiki 节点。"
        },
        {
          "label": "Tenant Token",
          "description": "更适合应用级自动化，但如果应用对目标对象没有权限，写入可能失败。"
        }
      ]
    }
  ]
}
```

如果当前环境不支持 `request_user_input`：

- 直接问一句：`这次首次写入你希望优先用 tenant token 还是 user token？`
- 如果用户仍未明确，再按本 skill 的默认鉴权规则执行，并在执行前说明当前默认身份

## 5. 读取与媒体

### 5.1 读取正文

优先使用：

```bash
python3 scripts/feishu_doc_helper.py fetch-content --ref "<docx/wiki/folder>"
```

需要图片 / 白板 / 附件时，改用：

```bash
python3 scripts/feishu_doc_helper.py fetch-content \
  --ref "<docx/wiki>" \
  --include-media \
  --save-image-manifest
```

### 5.2 媒体读取策略

当前读取侧策略：

1. 先抓正文
2. 图片优先尝试单图直下
3. 白板优先尝试 `download_as_image`
4. 失败时再回退导出 docx 抽 `word/media/*`
5. 附件块会尝试下载并生成 `attachment_summary`

媒体下载、导出回退、白板处理细节见：

- `references/media-handling.md`

### 5.3 读取输出重点

`fetch-content --include-media` 重点看：

- `media_summary`
- `attachment_summary`
- `image_understanding`
- `media_failures`
- `permission_hints`

`image_understanding` 是给 Agent 消费的结构化骨架，不是脚本自己完成视觉理解。  
拿到图片路径后，继续用图片理解能力补 `summary / extracted_text / entities / questions_to_answer`。

详细字段说明见：

- `references/output-schemas.md`

## 6. 创建更新与导入

### 6.1 直接文本写入

适用：

- 用户直接给文本
- 用户给 Markdown 内容
- Agent 现场生成飞书文档内容

命令：

```bash
python3 scripts/feishu_doc_helper.py create-doc ...
python3 scripts/feishu_doc_helper.py update-doc ...
```

默认路线：

- `create-doc`: `create -> convert -> create descendant`
- `update-doc`: 局部 patch 优先；必要时走 `overwrite`

### 6.2 文件导入

适用：

- 已有 `.md/.markdown/.mark/.html/.docx/.txt`
- 更适合后台异步导入

命令：

```bash
python3 scripts/feishu_doc_helper.py import-doc ...
```

支持：

- `--async`
- `--task-id`
- `--state-dir`
- `--async-threshold-bytes`

当前只有 `import-doc` 保留 task / async 模式。  
`create-doc / update-doc` 不再继续设计 task 模式；内容很大时统一建议改走 `import-doc`。

### 6.3 `update-doc` 当前正式边界

当前优先做局部 patch，无法安全收敛时直接报错，不再静默整文重建。  
复杂长文和原生扩展块修改统一收口为“先读全文，再 `overwrite`”。

详细边界见：

- `references/update-boundaries.md`

### 6.4 自动授权

`create-doc` / `import-doc` 成功后，只有在 **tenant token** 路径下，才默认尝试把：

- `MY_LARK_EMAIL`
- 或 `--grant-email`

对应的用户加成 `full_access`。

如果本次是 **user token** 创建或导入：

- 不再默认给创建者自己补授权
- 如需分享给其他人，显式使用 `share-doc`

如果没读到邮箱：

- 不阻塞创建
- 但要明确提示用户传 `--grant-email` 或设置 `MY_LARK_EMAIL`

### 6.5 飞书扩展写法

这些写法本质上属于**创建文档**或 **`update-doc --mode overwrite`** 的输入语法，不是独立能力。  
只在“Agent 直接生成内容并马上写入飞书”时推荐使用；如果用户要求“本地 Markdown 也能正常预览”，不要用这些扩展标签。

#### 6.5.1 当前支持范围

- `callout`
  - 原生支持
  - 适用于 `create-doc` 和 `update-doc --mode overwrite`
- `grid / column`
  - 原生支持
  - `title` 会折叠进列内第一行文本
- 标准 Markdown table
  - 会写成飞书原生表格块
- `<lark-table>`
  - 原生支持最小子集：`header-row`、`header-column`、普通 `row/cell`
  - 不支持合并单元格、自定义列宽
- `<whiteboard>`
  - 原生支持
  - 标签体是纯文本时，会写入初始 `text_shape`
  - 白板局部 patch 不支持
- ` ```plantuml ` / ` ```mermaid `
  - 原生支持
  - 会通过官方白板语法接口写入白板块
- 图片写法
  - 支持本地路径、`@路径`、`attachment://`、`file://`、`http(s)`、`data:`、HTML `<img>`、自定义 `<image .../>`
- `<file .../>`
  - 只支持读取侧结构化语法
  - 不支持直接写成飞书原生附件块

#### 6.5.2 使用边界

- 如果目标是“本地 Markdown 也能正常预览”，不要用飞书扩展标签。
- 如果目标是“Agent 直接生成更美观的飞书文档”，可以优先用这些扩展写法。
- 原生 `callout`、`grid`、`whiteboard`、图表白板在局部 patch 场景下不保证细粒度更新；需要改动时优先走全文 `overwrite`。
- 需要上传现有文件整体进入文档时，优先用 `import-doc`，不要用 `<file .../>`。

#### 6.5.3 详细语法

详细示例、推荐写法和已知边界见：

- `references/extended-markdown.md`

## 7. 协作权限与评论

### 7.1 协作权限

使用：

- `share-doc`
- `update-share`
- `remove-share`
- `transfer-owner`

输出时明确说明：

- 当前操作类型
- `doc_type`
- 目标成员
- 成员类型
- 权限值

如果 `member_type = openid`：

- 优先显式传 `--member-id --member-type openid`
- 如果用户只给了邮箱或姓名，优先用 `--member-query` 走用户搜索，把结果解析成 `open_id` 后再执行权限操作

### 7.2 评论

读取评论：

```bash
python3 scripts/feishu_doc_helper.py get-comments ...
```

创建评论：

```bash
python3 scripts/feishu_doc_helper.py add-comments --text "..."
```

当前边界：

- `get-comments` 支持全文评论和 inline comment 读取
- `add-comments` 当前只支持**全文评论创建**
- 如果用户传 `selection_with_ellipsis` 或 `selection_by_title` 去创建锚定评论，要明确说明开放平台当前不支持

## 8. 容器列举与定位

### 8.1 列举容器

使用：

```bash
python3 scripts/feishu_doc_helper.py list-docs ...
```

支持：

- 普通文件夹
- 共享文件夹
- wiki node
- wiki space

### 8.2 解析 wiki 节点

使用：

```bash
python3 scripts/feishu_doc_helper.py resolve-wiki-node ...
```

输出要说明：

- 输入是 `wiki token` 还是 `docx token`
- 返回的 `node_token`
- `space_id`
- `obj_token`
- `obj_type`

## 9. 输出规则

### 9.1 读取

- 有图片时，先做图片理解，再总结
- 明确哪些媒体成功下载，哪些失败
- 如果用了 `permission_hints` 或 `media_failures`，把它们翻译成用户可执行的下一步，而不是只复述错误

详细输出字段见：

- `references/output-schemas.md`

### 9.2 创建 / 更新 / 导入

- 说明目标位置
- 说明变更内容
- 说明 `routing_decision`
- 说明下一步可选动作
- 如果未设置 `MY_LARK_WEB_BASE_URL`，明确说明这次只返回稳定 ID，不返回租户内网页链接；脚本会同时返回 `web_link_notice`
- 如果自动授权成功，明确告知加给了谁、是什么权限
- 如果走了 `parser_fallback`，明确告诉用户没有走官方 `convert`
- 如果走 `overwrite`，明确提示是顶层块级 diff 覆盖

详细输出字段见：

- `references/output-schemas.md`

### 9.3 协作 / 评论

- `list-docs` 要明确当前列的是哪类容器
- `get-comments` 要明确 `scope=whole/inline`
- `quote` 要作为 `anchor` 呈现
- `add-comments` 要明确当前只创建全文评论

详细输出字段见：

- `references/output-schemas.md`

## 10. 失败处理

缺 token、scope 不足、应用身份失败、错误归因不清时，按统一错误路由处理。

详细路由见：

- `references/error-routing.md`

## 11. 附加资源

- `references/execution-modes.md`
- `references/error-routing.md`
- `references/media-handling.md`
- `references/output-schemas.md`
- `references/update-boundaries.md`
- `examples/sample-prompts.md`
- `tests/regression-checklist.md`
- `scripts/feishu_doc_helper.py`
