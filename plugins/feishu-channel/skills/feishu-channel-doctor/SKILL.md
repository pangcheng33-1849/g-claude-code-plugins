---
name: feishu-channel-doctor
description: 诊断飞书频道健康状态 — 排查多进程冲突、WebSocket 连接问题、日志分析。当用户报告"没有回复""消息丢失""连接异常"或想查看飞书频道运行状态时使用。
user-invocable: true
allowed-tools:
  - Read
  - Bash(ps aux)
  - Bash(ps -p *)
  - Bash(kill *)
  - Bash(ls *)
  - Bash(wc *)
---

# /feishu-channel-doctor — 飞书频道诊断

诊断飞书 MCP channel 的运行状态。只读取本地文件和进程信息，不调用飞书 API。

传入参数：`$ARGUMENTS`

---

## 根据参数分派

无参数或 `status` — 运行完整诊断（见下方）。

---

## 完整诊断流程

### 1. 进程检查

```bash
ps aux | grep 'bun.*server.ts' | grep -v grep
```

列出所有 feishu server 进程。正常情况下只有 **1 个**。

如果有多个：
- 运行 `ps -p <pid> -o pid,ppid,command` 查看每个进程的父进程
- 父进程是 `claude` 说明是某个 Claude Code 会话启动的
- 告知用户哪些是**当前会话**的（父 PID 与当前 shell 的 PPID 匹配），哪些是**旧会话残留**的
- 多进程会导致 Feishu WebSocket 消息被随机分发，造成部分消息无法回复

**修复建议**：关闭旧的 Claude Code 窗口，或手动 kill 旧进程。

### 2. 日志分析

读取 `~/.claude/channels/feishu/logs/latest`（软链接，指向当前会话日志）。如果 `latest` 不存在，回退查找 `logs/` 目录下最新的 `.log` 文件。日志按会话隔离，每次服务器启动创建新文件，最多保留 10 个。

分析当前会话日志最近 100 行：
- **连接状态**：查找 `WebSocket connecting` / `WebSocket start failed` 等关键词，判断 WS 是否成功建立
- **消息收发**：统计最近的 `message from` 条目，显示最后收到消息的时间
- **gate 结果**：查找 `gate: dropped` / `gate: pairing` / `gate: delivering`，判断是否有消息被拦截
- **沙盒拦截**：查找 `sandbox-bash: BLOCK` / `sandbox-file: BLOCK`，显示被沙盒拦截的操作
- **错误**：查找 `ERROR` / `failed` / `error` 关键词，摘要显示最近的错误

输出示例：
```
连接：✅ WebSocket 已连接（进程 PID 9496）
最近消息：3 分钟前收到（ou_xxx in oc_xxx）
Gate 统计：今日 12 条投递，0 条拦截
错误：无
```

### 3. 配置检查

读取 `~/.claude/channels/feishu/access.json`：
- 显示 dmPolicy、allowFrom 数量、groups 数量、pending 数量
- 如果有 pending 条目：提示用户用 `/feishu-channel-access pair <code>` 批准

### 4. 诊断结论

根据以上信息给出结论：
- ✅ 一切正常
- ⚠️ 有问题 + 具体原因 + 修复步骤

---

## 常见问题速查

| 症状 | 原因 | 修复 |
|------|------|------|
| 消息发出但无回复 | 多个 bun 进程抢 WS | kill 旧进程，关闭多余 Claude 窗口 |
| gate: dropped | 发送者不在白名单 | `/feishu-channel-access pair <code>` 或 `/feishu-channel-access allow <id>` |
| WebSocket start failed | 凭证错误或网络问题 | `/feishu-channel-configure` 检查凭证 |
| 日志文件不存在 | 服务器版本不支持文件日志 | 重启 Claude Code 后再试 |
| 消息延迟高 | 正常，WS 长连接偶有延迟 | 无需处理 |
