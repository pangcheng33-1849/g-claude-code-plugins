---
name: xhs-research
description: 在小红书上对指定话题进行口碑调研，采集笔记正文和评论区内容，生成结构化分析报告。支持指定采集篇数（至少10篇），自动过滤广告和营销内容。当用户需要了解某个产品、品牌或话题在小红书上的真实用户评价时使用。触发场景包括但不限于："小红书调研"、"小红书口碑"、"小红书搜索分析"、"xhs research"、"帮我看看小红书上怎么评价X"、"X在小红书上口碑怎么样"、"小红书舆情"、"小红书用户怎么看"、"去小红书上搜一下"、"小红书上关于X的评价"、"research X on xiaohongshu"。即使用户没有明确说"小红书"，但提到了"口碑调研"、"用户评价采集"、"社交平台舆情"并涉及中文消费品或科技产品话题，也应考虑触发此 skill。
---

# 小红书口碑调研 (XHS Research)

对指定话题在小红书上进行系统性口碑调研：搜索、筛选、采集笔记正文与评论区、生成结构化分析报告。

## 前置依赖

本 skill 依赖以下工具，执行前必须确认可用：

### 1. playwright-cli（必需）
- 用于浏览器自动化操作小红书页面
- 安装方式：`npm install -g playwright-cli` 或 `npx playwright-cli`

### 2. Playwright MCP Bridge 浏览器扩展（必需）
- 小红书有严格的反爬机制，必须连接用户真实浏览器（`--extension` 模式）
- 无头模式和新实例会被安全限制拦截（HTTP 461 / IP风险提示）
- 安装指南：https://github.com/microsoft/playwright-mcp/blob/main/packages/extension/README.md
- 用户需在 Chrome 中安装此扩展后，skill 才能正常工作

### 3. 用户已登录小红书（推荐）
- 未登录状态下部分笔记内容和评论可能不完整
- 连接用户浏览器后会自动继承登录态

### 4. g-feishu 插件（可选）
- 如果当前环境还安装了 `g-feishu@g-claude-code-plugins`，则可以复用其中的 `feishu-auth-and-scopes`、`feishu-doc-workflow`、`feishu-im-workflow`
- 飞书能力只用于登录提醒、文档归档和消息推送，不应成为本地调研流程的阻塞条件

## 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 话题/关键词 | 要调研的主题 | 必填 |
| 笔记数量 | 需要采集的笔记篇数 | 10（最少10篇） |
| 输出目录 | 保存结果的本地目录 | 当前工作目录下以话题命名的子目录 |
| 筛选标签 | 搜索结果页的筛选项（如"测评"） | 可选 |

## 执行流程

### Phase 1: 连接浏览器

```bash
# 连接用户已有浏览器（必须用 --extension 模式）
playwright-cli open --extension
```

**关键**：不要用 `--persistent` 或 `--headed` 模式直接打开小红书，会被反爬拦截。必须用 `--extension` 连接用户真实浏览器。

如果 `--extension` 失败，提示用户安装 Playwright MCP Bridge 扩展。

### Phase 1.1: 登录检测

导航到小红书后，检查页面是否要求登录（出现登录弹窗或二维码页面）。如果需要登录：

1. **截图登录二维码**：
```bash
playwright-cli screenshot --filename=/tmp/xhs-login-qr.png
```

2. **通过飞书发送给用户并加急**（仅当已安装 `g-feishu` 且 `feishu-im-workflow` 可用时）：
```bash
# 上传截图
playwright-cli run-code "..." # 或用 feishu_im_helper.py upload-image
# 发送图片消息
feishu_im_helper.py send-message --receive-id <用户邮箱> --receive-id-type email --image-key <image_key> --tenant-access-token <token>
# 对消息加急（urgent）
feishu_im_helper.py urgent-message --message-id <msg_id> --urgent-type buzzer --user-ids <user_open_id> --tenant-access-token <token>
```

如果未安装 `g-feishu` 或相关 skill 不可用，直接告知用户需要登录并提供截图本地路径。

发送后等待用户扫码完成登录，通过轮询 snapshot 检测登录状态（登录弹窗消失即表示成功），超时 2 分钟后提示用户手动处理。

### Phase 2: 搜索与筛选

```bash
# 导航到小红书并搜索
playwright-cli goto https://www.xiaohongshu.com
playwright-cli snapshot

# 搜索框是一个 textbox，placeholder 为"搜索小红书"
# 在 snapshot 中找到对应 ref（通常是 textbox "搜索小红书" 的 ref）
playwright-cli click <搜索框ref>
playwright-cli fill <搜索框ref> "<关键词>"
playwright-cli press Enter
```

搜索结果页有两层筛选控件，善用它们可以大幅提升笔记质量：

**第一层：内容类型**（搜索框正下方）
- 全部 | 图文 | 视频 | 用户
- 口碑调研通常选"图文"，因为图文笔记正文信息密度更高

**第二层：话题关键词标签**（内容类型下方的横向滚动标签栏）
- 这些标签由小红书根据搜索词动态生成，例如搜索"perplexity"时出现：综合 | 学生认证 | 优惠码 | 使用教程 | 测评 | 免费领取 | 性价比 | 订阅 | 模型 | ...
- **强烈推荐**：优先点击"测评"、"使用教程"、"性价比"等标签来筛选口碑类笔记，可以有效过滤掉新闻和营销内容
- 如果用户指定了筛选标签，点击对应按钮；如果未指定，根据调研目的自动选择最合适的标签（口碑调研优先"测评"）

筛选完成后，通过 snapshot 读取搜索结果列表，记录每篇笔记的标题、作者、点赞数、URL ref

### Phase 3: 笔记筛选（跳过广告/营销）

在搜索结果中识别并跳过以下类型：
- **新闻报道类**：来自媒体账号（如"量子位"、"投资界"、"TechFlow"等）的产品发布/行业新闻
- **营销推广类**：标题含"免费领取"、"优惠码"、"激活码"等推广关键词
- **纯转载类**：无个人观点的官方公告转载

优先选择：
- 个人使用体验和主观评价
- 产品对比和测评
- 吐槽和问题反馈
- 有较多评论互动的笔记（评论区是口碑的核心来源）

如果当前页面的合格笔记不够，需要滚动加载更多结果或尝试不同的搜索关键词组合（如添加"使用体验"、"测评"、"好用吗"等后缀）。

### Phase 4: 逐篇采集（核心步骤）

对每篇笔记，使用以下高效采集流程：

#### 4.1 导航到笔记

从搜索结果页点击笔记链接，或使用搜索结果中的完整 URL（含 `xsec_token`）直接导航：

```bash
playwright-cli goto "https://www.xiaohongshu.com/search_result/<note_id>?xsec_token=<token>&xsec_source="
```

**注意**：直接构造 `/explore/<note_id>` 的 URL 会被 403 拒绝，必须使用搜索结果页中带 `xsec_token` 的完整链接。

#### 4.2 滚动加载评论

使用 `run-code` 滚动页面以加载更多评论（至少滚动 3 轮）：

```bash
playwright-cli run-code "async page => {
  for (let i = 0; i < 10; i++) {
    await page.evaluate(() => {
      document.querySelectorAll('[class*=interaction],[class*=scroll],[class*=detail]')
        .forEach(c => c.scrollBy(0, 2000));
      window.scrollBy(0, 2000);
    });
    await page.waitForTimeout(600);
  }
}"
```

#### 4.3 提取笔记数据（关键脚本）

使用 `run-code` + `page.evaluate()` 一次性从 DOM 提取所有数据，这是最高效的方式：

```bash
playwright-cli run-code "async page => {
  // 先滚动加载评论
  for (let i = 0; i < 10; i++) {
    await page.evaluate(() => {
      document.querySelectorAll('[class*=interaction],[class*=scroll],[class*=detail]')
        .forEach(c => c.scrollBy(0, 2000));
      window.scrollBy(0, 2000);
    });
    await page.waitForTimeout(600);
  }
  // 提取所有数据
  return await page.evaluate(() => {
    const title = document.querySelector('#detail-title')?.textContent?.trim() || '';
    const desc = document.querySelector('#detail-desc')?.textContent?.trim() || '';
    const author = document.querySelector('.username')?.textContent?.trim() || '';
    const date = document.querySelector('.date')?.textContent?.trim() || '';
    const url = location.href;
    const tags = Array.from(document.querySelectorAll('#detail-desc a[href*=keyword]'))
      .map(t => t.textContent.trim());
    const counts = Array.from(document.querySelectorAll('.engage-bar .count'))
      .map(c => c.textContent.trim());
    const comments = [];
    document.querySelectorAll('.parent-comment').forEach(c => {
      const replies = [];
      c.querySelectorAll('.sub-comment-container .comment-inner-container').forEach(r => {
        replies.push({
          name: r.querySelector('.name')?.textContent?.trim() || '',
          content: r.querySelector('.content')?.textContent?.trim() || '',
          time: r.querySelector('.date')?.textContent?.trim() || ''
        });
      });
      comments.push({
        name: c.querySelector('.name')?.textContent?.trim() || '',
        content: c.querySelector('.content')?.textContent?.trim() || '',
        time: c.querySelector('.date')?.textContent?.trim() || '',
        likes: c.querySelector('.like .count')?.textContent?.trim() || '0',
        replies
      });
    });
    return JSON.stringify({
      title, desc: desc.substring(0, 5000), author, date, url, tags, counts, comments
    });
  });
}"
```

**性能对比**：
- ❌ snapshot → Read YAML → 逐字段解析：每篇约 5 分钟
- ✅ run-code + page.evaluate()：每篇约 15 秒（含滚动加载）

**错误处理**：如果提取结果中 `title` 和 `desc` 均为空，说明页面未正确加载或被反爬拦截，跳过该笔记并记录失败原因，继续处理下一篇。最终如果成功采集的笔记数不足用户要求，在总结中说明实际采集数量。

#### 4.4 保存为 Markdown

将每篇笔记保存为独立 MD 文件，格式：

```markdown
# <标题>

- **作者**: <作者名>
- **日期**: <发布日期>
- **互动**: <赞数>赞 | <收藏数>收藏 | <评论数>评论
- **链接**: <笔记URL>
- **标签**: <标签列表>

## 笔记正文

<正文内容>

## 评论区（共N条）

### 1. <评论者> (<时间>) 👍<赞数>
> <评论内容>
```

文件命名：`{序号}_{简短标题}_{作者}.md`

### Phase 5: 生成总结报告

所有笔记采集完成后，分析全部正文和评论区内容，生成一篇总结 MD。

总结的结构和侧重点应根据话题特性自适应，不要套用固定模板。例如：
- 产品口碑调研：侧重优缺点、性价比、替代品
- 品牌舆情分析：侧重情感倾向、争议事件、传播趋势
- 行业趋势研究：侧重关键玩家、用户需求变化、未来预判
- 消费决策类：侧重购买建议、避坑指南、真实使用场景

**唯一硬性要求**：总结中的每个观点必须以 inline 形式引用原始笔记链接，格式为 `[笔记N](URL)`，让读者可以溯源验证。

## 进度汇报

每完成一篇笔记的采集，向用户汇报进度，格式如：
```
已完成 3/15 篇：《标题》by 作者 (N条评论)
```

## 反爬注意事项

1. **不要频繁快速操作**：每次页面导航后等待页面完全加载
2. **不要用无头浏览器**：小红书检测自动化浏览器并返回 461 错误
3. **必须用 --extension 模式**：继承用户真实浏览器的 cookies 和指纹
4. **xsec_token 有时效性**：从搜索结果页获取的 token 可能过期，遇到 403 时回到搜索页重新获取
5. **评论加载需要滚动**：评论不会一次性加载，需要多次滚动触发懒加载

## 输出清单

执行完成后，输出目录中应包含：

```text
<话题>_notes_YYYY-MM-DD/
├── 01_<标题>_<作者>.md
├── 02_<标题>_<作者>.md
├── ...
├── 10_<标题>_<作者>.md  (至少10篇)
└── 总结_<话题>口碑分析.md
```

## Phase 6（可选）: 飞书文档与消息推送

如果当前环境还安装了 `g-feishu` 插件，并且其中的 `feishu-doc-workflow`、`feishu-im-workflow`、`feishu-auth-and-scopes` 可用，在本地文件全部生成后，自动执行以下步骤：

### 6.1 合并为飞书文档

将总结报告和全部原始笔记合并为一个 Markdown 文件（总结在前，原始笔记以附录形式追加），然后调用 `feishu-doc-workflow` 的 `create-doc` 创建飞书文档。

合并顺序：
1. 总结报告全文
2. 分隔线 + "附录：N篇原始笔记"
3. 各篇笔记全文（按序号排列，笔记间用分隔线分隔）

### 6.2 飞书消息通知用户

文档创建成功后，调用 `feishu-im-workflow` 的 `send-message` 向用户发送一条卡片消息（`msg_type=interactive`），包含：
- 标题：调研话题名称
- 摘要：采集了多少篇笔记、多少条评论
- 按钮：跳转到飞书文档的链接

鉴权说明：
- 创建文档优先使用 **user token**（文档归属用户本人）
- 发送消息使用 **tenant token**（应用身份发送卡片）
- 两种 token 通过 `feishu-auth-and-scopes` 获取

如果未安装 `g-feishu` 或相关 skill 不可用，跳过此阶段，仅输出本地文件。

## 示例调用

```
/xhs-research perplexity 口碑评价，采集15篇
/xhs-research Cursor编辑器 使用体验
/xhs-research Claude Code 测评，20篇，筛选"测评"
/xhs-research Dyson吹风机 口碑，发到我飞书
```
