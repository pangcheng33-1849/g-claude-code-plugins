# 输出 Schema

本文件定义 `feishu-doc-workflow` 在读取、创建、更新、导入时最重要的结构化输出字段，供 Agent 按需加载。

## 1. 读取输出

`fetch-content --include-media` 重点关注：

- `media_summary`
- `attachment_summary`
- `image_understanding`
- `media_failures`
- `permission_hints`

### 1.1 `image_understanding`

这是给 Agent 消费的结构化骨架，不是脚本自己完成视觉理解。  
拿到图片路径后，继续用图片理解能力补：

- `summary`
- `extracted_text`
- `entities`
- `questions_to_answer`

典型结构：

```json
{
  "schema_version": "1",
  "image_count": 2,
  "image_paths": ["/abs/path/a.png", "/abs/path/b.png"],
  "items": [
    {
      "path": "/abs/path/a.png",
      "summary": "",
      "extracted_text": [],
      "entities": [],
      "questions_to_answer": []
    }
  ],
  "merge_instruction": "将图片理解结果与正文合并后再总结。",
  "next_step": "逐张图片做理解并回填。"
}
```

### 1.2 `attachment_summary.attachments[]`

尽量补全：

- 文本附件：`text_preview / line_count`
- JSON：`top_level_keys / top_level_type`
- CSV/TSV：`header / row_count`
- 二进制附件：`summary_kind = binary`

典型结构：

```json
{
  "attachments": [
    {
      "name": "sample.csv",
      "summary_kind": "csv",
      "header": ["col_a", "col_b"],
      "row_count": 12
    }
  ]
}
```

### 1.3 `media_failures`

媒体失败时返回结构化结果，而不是只返回字符串报错。  
重点字段：

- `token`
- `kind`
- `stage`
- `reason`
- `next_step`

## 2. 创建 / 更新 / 导入输出

输出时优先覆盖：

- 目标位置
- 变更内容
- `routing_decision`
- 下一步可选动作

额外约定：

- 自动授权成功时，明确告知加给了谁、是什么权限
- 走了 `parser_fallback` 时，明确说明没有走官方 `convert`
- 走 `overwrite` 时，明确说明是顶层块级 diff 覆盖
- 图片写入失败时，输出 `image_failures[]`

## 3. 协作 / 评论输出

- `list-docs` 明确当前列的是哪类容器
- `get-comments` 明确 `scope=whole/inline`
- `quote` 作为 `anchor`
- `add-comments` 明确当前只创建全文评论
