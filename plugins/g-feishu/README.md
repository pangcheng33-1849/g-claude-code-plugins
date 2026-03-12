# G-Feishu Plugin

这个目录包含一组可直接分发的 Feishu/Lark Agent Skills。

## 安装

```bash
# 第一步：添加 marketplace
/plugin marketplace add pangcheng33-1849/g-claude-code-plugins

# 第二步：安装插件
/plugin install g-feishu@g-claude-code-plugins
```

本地开发调试：

```bash
claude --plugin-dir ./plugins/g-feishu
```

## Skills 说明

- `feishu-api-diagnose`
  用于诊断 Feishu/Lark API 报错、权限问题、对象 ID 问题和请求参数问题。
- `feishu-auth-and-scopes`
  用于获取 token、发起授权、刷新 token，并判断 scope 是否满足要求。
- `feishu-bitable-workflow`
  用于创建和管理多维表格 app、数据表、字段、记录和视图。
- `feishu-calendar-workflow`
  用于创建、查询、更新、删除日程，以及查询忙闲时间。
- `feishu-doc-workflow`
  用于读取、创建、更新、导入飞书文档和 wiki，并处理文档里的图片、白板和附件。
- `feishu-im-workflow`
  用于创建群聊、发送消息、回复消息、编辑/撤回消息、管理 reaction、读取话题和线程。
- `feishu-search-and-locate`
  用于搜索用户、文档、wiki 和群聊，并定位后续工作流需要的稳定标识符。
- `feishu-task-workflow`
  用于创建、更新、查询、完成、恢复、删除任务，以及管理任务成员和提醒。

## 统一环境变量

这组 skills 对外依赖的最小环境变量标准只有 3 个：

- `MY_LARK_APP_ID`
- `MY_LARK_APP_SECRET`
- `MY_LARK_EMAIL`

## 最小配置方法

在当前 shell 会话里临时配置：

```bash
export MY_LARK_APP_ID="你的应用 App ID"
export MY_LARK_APP_SECRET="你的应用 App Secret"
export MY_LARK_EMAIL="你的飞书邮箱"
```

如果你希望文档、多维表格等写操作结果直接返回可点击的租户网页链接，可以额外配置：

```bash
export MY_LARK_WEB_BASE_URL="https://你的租户域名.larkoffice.com"
```

如果你希望每次打开终端都自动生效，可以追加到 `~/.zshrc`：

```bash
cat >> ~/.zshrc <<'EOF'
export MY_LARK_APP_ID="你的应用 App ID"
export MY_LARK_APP_SECRET="你的应用 App Secret"
export MY_LARK_EMAIL="你的飞书邮箱"
export MY_LARK_WEB_BASE_URL="https://你的租户域名.larkoffice.com"
EOF
source ~/.zshrc
```

补充说明：
- `MY_LARK_EMAIL` 主要用于默认分享、默认参会人、默认成员授权等场景。
- `MY_LARK_WEB_BASE_URL` 属于可选增强项。未设置时，文档和多维表格类 workflow 仍会返回稳定 ID，但不会伪造租户内网页链接。
- `MY_LARK_USER_ACCESS_TOKEN`、`MY_LARK_TENANT_ACCESS_TOKEN`、`FEISHU_AUTH_CACHE_DIR`、`FEISHU_DOC_TASK_DIR` 都属于内部运行时变量或高级覆盖项，不要求用户手工配置。
- 更完整的变量说明和 CLI 权限矩阵请看：
  - `feishu-auth-and-scopes/references/env-standards.md`
  - `feishu-auth-and-scopes/references/cli-scope-matrix.md`

## 使用原则

- 规划、候选比较、歧义消解，优先交给 Agent 的自然语言能力。
- 真实 API 执行、结构化输入输出、稳定命令入口，交给 `scripts/`。
- 跨 skill 协作统一通过 skill 名，不做跨 skill 的代码级 import。

## 迁移与发布

- 发布时保留这个目录即可。
- 不要把 `__pycache__`、`.pyc`、本地临时文件、环境绑定 ID 一起打包。
