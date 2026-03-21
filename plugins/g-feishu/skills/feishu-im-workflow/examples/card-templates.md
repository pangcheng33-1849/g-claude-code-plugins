# 卡片模板

## 简洁通知卡片

```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"tag": "plain_text", "content": "通知标题"},
    "template": "blue"
  },
  "elements": [
    {
      "tag": "div",
      "text": {"tag": "lark_md", "content": "**消息内容**\n\n这是通知的详细内容。"}
    },
    {"tag": "hr"},
    {
      "tag": "note",
      "elements": [{"tag": "plain_text", "content": "备注信息"}]
    }
  ]
}
```

## 分栏信息卡片

```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"tag": "plain_text", "content": "数据报告"},
    "template": "turquoise"
  },
  "elements": [
    {
      "tag": "div",
      "text": {"tag": "lark_md", "content": "**报告概览**\n\n这是数据的详细分析。"}
    },
    {"tag": "hr"},
    {
      "tag": "div",
      "fields": [
        {
          "is_short": true,
          "text": {"tag": "lark_md", "content": "**增长指标**\n• 用户数: +15%\n• 活跃度: +8%"}
        },
        {
          "is_short": true,
          "text": {"tag": "lark_md", "content": "**注意事项**\n• 需要关注\n• 优化方向"}
        }
      ]
    },
    {"tag": "hr"},
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {"tag": "plain_text", "content": "查看详情"},
          "type": "primary",
          "url": "https://example.com"
        }
      ]
    }
  ]
}
```

## 完整功能卡片

```json
{
  "config": {"wide_screen_mode": true},
  "header": {
    "title": {"tag": "plain_text", "content": "功能展示"},
    "template": "purple"
  },
  "elements": [
    {
      "tag": "div",
      "text": {"tag": "lark_md", "content": "**欢迎**\n\n这是一个功能完整的卡片示例。"}
    },
    {"tag": "hr"},
    {
      "tag": "div",
      "fields": [
        {
          "is_short": true,
          "text": {"tag": "lark_md", "content": "**视觉**\n• 标题栏\n• 分割线\n• 分栏"}
        },
        {
          "is_short": true,
          "text": {"tag": "lark_md", "content": "**功能**\n• 按钮\n• 链接\n• 交互"}
        }
      ]
    },
    {"tag": "hr"},
    {
      "tag": "note",
      "elements": [{"tag": "plain_text", "content": "提示信息"}]
    },
    {
      "tag": "action",
      "actions": [
        {
          "tag": "button",
          "text": {"tag": "plain_text", "content": "主要操作"},
          "type": "primary",
          "url": "https://example.com"
        },
        {
          "tag": "button",
          "text": {"tag": "plain_text", "content": "次要操作"},
          "type": "default",
          "url": "https://example.com"
        }
      ]
    }
  ]
}
```
