# 消息内容写法

构造 `post` 和 `interactive` 消息内容时参考本文档。`text` 消息直接用 `--text` 即可。

官方文档：[发送消息](https://open.larkoffice.com/document/server-docs/im-v1/message/create) · [卡片 Markdown](https://open.larkoffice.com/document/common-capabilities/message-card/message-cards-content/using-markdown-tags#abc9b025) · [卡片富文本组件](https://open.larkoffice.com/document/feishu-cards/card-components/content-components/rich-text)

## 富文本消息（post）

`post.json` 示例：

```json
{
  “zh_cn”: {
    “title”: “版本发布通知”,
    “content”: [
      [
        {“tag”: “text”, “text”: “今晚 20:00 发布新版本。”}
      ],
      [
        {“tag”: “a”, “text”: “查看发布说明”, “href”: “https://open.feishu.cn”}
      ],
      [
        {“tag”: “at”, “user_id”: “ou_xxx”},
        {“tag”: “text”, “text”: “ 请关注”}
      ]
    ]
  }
}
```

post content 是二维数组，每个内层数组是一行。可用元素：`text`、`a`（链接）、`at`（@提及）、`img`（图片）。

## 卡片消息（interactive）

最小结构：

```json
{
  “config”: {“wide_screen_mode”: true},
  “header”: {
    “title”: {“tag”: “plain_text”, “content”: “标题”},
    “template”: “blue”
  },
  “elements”: [
    {
      “tag”: “div”,
      “text”: {“tag”: “lark_md”, “content”: “**Markdown** 正文”}
    }
  ]
}
```

- `header` — 标题和色带（blue/turquoise/green/orange/red/purple/indigo/grey）
- `elements` — 正文布局
- `config.wide_screen_mode` — 长文本建议开启

## 卡片元素速查

| 元素 | 用途 | 关键字段 |
|------|------|----------|
| `div` + `text` | 文本块 | `{“tag”:”lark_md”,”content”:”...”}` |
| `div` + `fields` | 分栏对比 | `[{“is_short”:true,”text”:{...}}]` |
| `hr` | 分割线 | `{“tag”:”hr”}` |
| `note` | 备注 | `{“tag”:”note”,”elements”:[{“tag”:”plain_text”,”content”:”...”}]}` |
| `action` | 按钮组 | `type`: `primary` / `default` / `danger` |
| `markdown` | 富文本（支持 @提及） | `{“tag”:”markdown”,”content”:”...”}` |

## @提及（mention）

**三种消息类型格式不同，不要混用：**

### text

```bash
--text '<at user_id=”ou_xxx”>Name</at> 正文'
```

### post

content 数组中用独立 JSON 元素：

```json
[
  {“tag”: “at”, “user_id”: “ou_xxx”},
  {“tag”: “text”, “text”: “ 请查看”}
]
```

**`<at>` 标签在 post 中无效**，必须用 JSON 元素。

### interactive（卡片）

在 `{“tag”:”markdown”}` 中使用，注意属性名是 **`id`** 不是 `user_id`：

```json
{
  “tag”: “markdown”,
  “content”: “<at id=ou_xxx></at> 请查看”
}
```

**不要**用 `{“tag”:”div”,”text”:{“tag”:”lark_md”}}`，mention 不会被解析。

### @所有人

| msg_type | 写法 |
|----------|------|
| text | `<at user_id=”all”></at>` |
| post | `{“tag”:”at”,”user_id”:”all”}` |
| interactive | `<at id=all></at>`（在 `{“tag”:”markdown”}` 中） |

## 常见错误

- **`div` 里用 `extra` 渲染正文** → 用 `div.text` 或独立 `note`
- **JSON 转义** → `content-file` 比 `content-json` 更稳
- **按钮 type 乱写** → 只用 `primary` / `default` / `danger`
- **卡片 mention 用 `lark_md`** → 必须用 `{“tag”:”markdown”}`，属性名用 `id`

## 卡片模板

更多模板见 `examples/card-templates.md`。
