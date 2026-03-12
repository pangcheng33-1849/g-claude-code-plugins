# 消息内容写法

官方文档：

- [旧版消息卡片 Markdown 标签](https://open.larkoffice.com/document/common-capabilities/message-card/message-cards-content/using-markdown-tags#abc9b025)
- [飞书卡片富文本（Markdown）组件](https://open.larkoffice.com/document/feishu-cards/card-components/content-components/rich-text)
- [发送消息](https://open.larkoffice.com/document/server-docs/im-v1/message/create)

## 选择原则

- 短消息、测试消息、简单通知：
  - 优先 `text`
- 非随意对话、正式说明、对外同步、长消息、需要强调层次：
  - 优先 `interactive`
- 只有在“不需要卡片布局，只需要结构化长正文”时：
  - 再考虑 `post`

一句话规则：

- **非随意对话不要默认发 `text`，优先 `interactive`；只有卡片不合适时，再退回 `post`。**

## 文本消息

优先用：

```bash
--text "消息正文"
```

等价于：

```json
{
  "msg_type": "text",
  "content": "{\"text\":\"消息正文\"}"
}
```

适合：

- 一句话通知
- 测试消息
- 简单回复

## 富文本消息（post）

需要多段正文、列表、链接或较长说明，但又**不需要卡片布局、按钮、备注、分栏**时，再考虑 `msg_type=post`。

```bash
python3 scripts/feishu_im_helper.py send-message \
  --receive-id oc_xxx \
  --receive-id-type chat_id \
  --msg-type post \
  --content-file ./post.json \
  --tenant-access-token "$MY_LARK_TENANT_ACCESS_TOKEN"
```

`post.json` 示例：

```json
{
  "zh_cn": {
    "title": "版本发布通知",
    "content": [
      [
        {
          "tag": "text",
          "text": "今晚 20:00 发布新版本。"
        }
      ],
      [
        {
          "tag": "text",
          "text": "变更重点："
        }
      ],
      [
        {
          "tag": "a",
          "text": "查看发布说明",
          "href": "https://open.feishu.cn"
        }
      ]
    ]
  }
}
```

## 卡片消息（interactive）

非随意对话里，默认优先用 `msg_type=interactive`。尤其适合：

- 正式通知
- 对外同步
- 状态播报
- 带按钮入口的消息
- 需要明显视觉层级的长消息

```bash
python3 scripts/feishu_im_helper.py send-message \
  --receive-id oc_xxx \
  --receive-id-type chat_id \
  --msg-type interactive \
  --content-file ./card.json \
  --tenant-access-token "$MY_LARK_TENANT_ACCESS_TOKEN"
```

`card.json` 示例：

```json
{
  "config": {
    "wide_screen_mode": true
  },
  "header": {
    "template": "blue",
    "title": {
      "tag": "plain_text",
      "content": "发布通知"
    }
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**上线时间**：今晚 20:00\n- 变更 A\n- 变更 B\n[查看详情](https://open.feishu.cn)"
      }
    }
  ]
}
```

## 卡片消息基础结构

最小卡片一般遵循：

```json
{
  "config": {
    "wide_screen_mode": true
  },
  "header": {
    "title": {
      "tag": "plain_text",
      "content": "标题"
    },
    "template": "blue"
  },
  "elements": []
}
```

推荐理解方式：

- `header`
  - 决定卡片标题和色带
- `elements`
  - 决定正文布局、说明、按钮、备注
- `config.wide_screen_mode`
  - 长文本和分栏场景通常建议开启

## 核心元素类型

### 文本块（div）

最常用，用来承载一段说明、摘要、Markdown 内容。

```json
{
  "tag": "div",
  "text": {
    "tag": "lark_md",
    "content": "**Markdown** 文本内容"
  }
}
```

### 分栏布局（div + fields）

适合做左右对比、指标对照、并列说明。

```json
{
  "tag": "div",
  "fields": [
    {
      "is_short": true,
      "text": {
        "tag": "lark_md",
        "content": "**左栏**\n• 项目1\n• 项目2"
      }
    },
    {
      "is_short": true,
      "text": {
        "tag": "lark_md",
        "content": "**右栏**\n• 项目1\n• 项目2"
      }
    }
  ]
}
```

### 分割线（hr）

适合把卡片拆成多个阅读区域。

```json
{
  "tag": "hr"
}
```

### 备注块（note）

适合补时间、说明、提示，不和正文抢主层级。

```json
{
  "tag": "note",
  "elements": [
    {
      "tag": "plain_text",
      "content": "💡 备注内容"
    }
  ]
}
```

### 按钮组（action）

适合给出一个或多个下一步入口。

```json
{
  "tag": "action",
  "actions": [
    {
      "tag": "button",
      "text": {
        "tag": "plain_text",
        "content": "主要按钮"
      },
      "type": "primary",
      "url": "https://example.com"
    },
    {
      "tag": "button",
      "text": {
        "tag": "plain_text",
        "content": "次要按钮"
      },
      "type": "default",
      "url": "https://example.com"
    }
  ]
}
```

按钮 `type` 只使用：

- `primary`
- `default`
- `danger`

## 卡片富文本能力说明

按官方文档，卡片富文本 / Markdown 常见可用能力包括：

- 加粗、斜体、删除线
- 链接
- `@人` / `@all`
- 列表
- 代码块
- 图片
- 分割线
- 飞书表情

要注意两条路线：

- 旧版消息卡片 / 文本元素里的 `lark_md`
- 新版飞书卡片富文本（Markdown）组件

对 helper 来说，两条路线都一样：

- helper 不负责生成卡片 JSON
- helper 只负责把你提供的合法 `content-json` / `content-file` 原样发送

## 模板示例

### 简洁通知卡片

```json
{
  "config": {
    "wide_screen_mode": true
  },
  "header": {
    "title": {
      "tag": "plain_text",
      "content": "📢 通知标题"
    },
    "template": "blue"
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**消息内容**\n\n这是通知的详细内容。"
      }
    },
    {
      "tag": "hr"
    },
    {
      "tag": "note",
      "elements": [
        {
          "tag": "plain_text",
          "content": "⏰ 2026-03-06 22:30"
        }
      ]
    }
  ]
}
```

### 分栏信息卡片

```json
{
  "config": {
    "wide_screen_mode": true
  },
  "header": {
    "title": {
      "tag": "plain_text",
      "content": "📊 数据报告"
    },
    "template": "turquoise"
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**报告概览**\n\n这是数据的详细分析。"
      }
    },
    {
      "tag": "hr"
    },
    {
      "tag": "div",
      "fields": [
        {
          "is_short": true,
          "text": {
            "tag": "lark_md",
            "content": "**📈 增长指标**\n• 用户数: +15%\n• 活跃度: +8%"
          }
        },
        {
          "is_short": true,
          "text": {
            "tag": "lark_md",
            "content": "**⚠️ 注意事项**\n• 需要关注\n• 优化方向"
          }
        }
      ]
    },
    {
      "tag": "hr"
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "查看详情"
          },
          "type": "primary",
          "url": "https://example.com"
        }
      ]
    }
  ]
}
```

### 完整功能卡片

```json
{
  "config": {
    "wide_screen_mode": true
  },
  "header": {
    "title": {
      "tag": "plain_text",
      "content": "🦞 功能展示"
    },
    "template": "purple"
  },
  "elements": [
    {
      "tag": "div",
      "text": {
        "tag": "lark_md",
        "content": "**欢迎**\n\n这是一个功能完整的卡片示例。"
      }
    },
    {
      "tag": "hr"
    },
    {
      "tag": "div",
      "fields": [
        {
          "is_short": true,
          "text": {
            "tag": "lark_md",
            "content": "**🎨 视觉**\n• 标题栏\n• 分割线\n• 分栏"
          }
        },
        {
          "is_short": true,
          "text": {
            "tag": "lark_md",
            "content": "**🔧 功能**\n• 按钮\n• 链接\n• 交互"
          }
        }
      ]
    },
    {
      "tag": "hr"
    },
    {
      "tag": "note",
      "elements": [
        {
          "tag": "plain_text",
          "content": "💡 提示信息"
        }
      ]
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "主要操作"
          },
          "type": "primary",
          "url": "https://example.com"
        },
        {
          "tag": "button",
          "text": {
            "tag": "plain_text",
            "content": "次要操作"
          },
          "type": "default",
          "url": "https://example.com"
        }
      ]
    }
  ]
}
```

## 常见错误

### 不要在 `div` 里用 `extra` 渲染正文

错误示例：

```json
{
  "tag": "div",
  "fields": [],
  "extra": {
    "tag": "lark_md",
    "content": "文本"
  }
}
```

正确做法：

- 用独立的 `div.text`
- 或用独立的 `note`
- 或拆成多个 `div`

### JSON 转义错误

要注意：

- 引号要转义：`\\\"`
- 换行要转义：`\\n`
- `content-file` 通常比 `content-json` 更稳

### 按钮类型乱写

只用：

- `primary`
- `default`
- `danger`

## 最佳实践

- 卡片优先讲层次，不要把所有字堆成一个大段落
- 先有标题，再有摘要，再拆分明细，再给按钮
- 需要对比时优先用 `fields`
- 需要区分区域时优先加 `hr`
- 需要补提示信息时优先用 `note`
- 需要强引导下一步时优先用 `action/button`
- 非随意对话默认先想卡片，而不是先想 `post`
- 只有当消息只是结构化长正文、且不需要按钮、备注、分栏、视觉层次时，再退回 `post`
- 颜色模板要和语义匹配，不要为了“好看”滥用鲜艳主题

## 使用场景

- 通知公告
- 数据报告
- 任务提醒
- 文档分享
- 活动通知
- 需要按钮入口的状态同步

## 当前建议

- 文本、简单通知、测试消息：
  - 直接用 `--text`
- 非随意对话、正式说明、带结构的更新：
  - 优先 `--msg-type interactive`
- 只需要长正文、列表、链接，但不需要卡片布局：
  - 再考虑 `--msg-type post`
- 非文本内容尽量用：
  - `--content-file`
  - 不要把大段 JSON 直接塞进 `--content-json`

## 边界

- helper 不负责替你生成卡片 JSON
- helper 不负责把自然语言自动转成 `post` / `interactive`
- 如果用户目标是“构造复杂消息内容”，应先让 Agent 用自然语言整理结构，再写成 `content-json` 或 `content-file`
