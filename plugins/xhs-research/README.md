# XHS Research Plugin

针对小红书话题做口碑调研的 Claude Code 插件。它会搜索相关笔记，筛选掉明显的新闻稿和营销内容，采集正文与评论区，再输出带溯源链接的 Markdown 总结。

## 安装

```bash
# 第一步：添加 marketplace
/plugin marketplace add pangcheng1849/g-claude-code-plugins

# 第二步：安装插件
/plugin install xhs-research@g-claude-code-plugins
```

本地开发调试：

```bash
claude --plugin-dir ./plugins/xhs-research
```

## Skill

- `xhs-research`
  在小红书上对指定话题进行口碑调研，采集笔记正文和评论区内容，输出结构化 Markdown 报告。

## 前置依赖

- 必需：`playwright-cli`
- 必需：Playwright MCP Bridge 浏览器扩展，并通过 `--extension` 连接用户真实浏览器
- 必需：将扩展状态页里显示的 token 配置到环境变量 `PLAYWRIGHT_MCP_EXTENSION_TOKEN`
- 推荐：用户浏览器中已登录小红书账号

推荐先在当前 shell 中导出：

```bash
export PLAYWRIGHT_MCP_EXTENSION_TOKEN="your-token-here"
```

这个 token 可以在 Playwright MCP Bridge 扩展图标或状态页中复制到；配置后可避免每次连接浏览器时手动确认。

## 可选协作 Skills

如果当前环境里已经有以下飞书 skills，`xhs-research` 会在可用时调用它们：

- `feishu-auth-and-scopes`
- `feishu-doc-workflow`
- `feishu-im-workflow`

这些飞书能力仅用于登录提醒、结果汇总成飞书文档和消息推送；即使这些 skills 不可用，插件仍应完整生成本地 Markdown 结果。

## 输出

默认会在当前工作目录下生成一个以调研主题命名的目录，例如：

```text
<话题>_notes_YYYY-MM-DD/
├── 01_<标题>_<作者>.md
├── 02_<标题>_<作者>.md
├── ...
└── 总结_<话题>口碑分析.md
```
