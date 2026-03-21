#!/bin/bash
# =============================================================================
# sandbox-bash.sh — 命令执行沙盒
# =============================================================================
#
# 作为 PreToolUse hook 拦截 Bash 工具调用，执行两层检查：
#   1. 命令前缀白名单 — 命令必须以白名单中的某个前缀开头
#   2. 路径白名单 — 命令中出现的文件路径必须在允许范围内
#
# 第二层检查防止白名单命令（如 cat、ls）访问不在允许范围内的路径，
# 避免通过 Bash 工具绕过 sandbox-file.sh 的文件访问限制。
#
# 安全策略：
#   - 白名单模式（而非黑名单）：只允许明确列出的命令前缀
#   - fail-closed：配置文件缺失时阻止所有命令
#   - 路径检查复用 sandbox.conf 的白名单 + cwd 自动放行
#
# 白名单配置：~/.claude/channels/feishu/sandbox-bash.conf
#   每行一个命令前缀，命令必须以某个前缀开头才放行。
#   例如 "git status" 允许 "git status"、"git status --short" 等。
#   但 "git" 作为前缀会允许所有 git 子命令。
#
# 输入：PreToolUse hook 的 JSON（通过 stdin），包含 tool_input.command 和 cwd
# 输出：exit 0 = 放行，exit 2 = 阻止（stderr 输出原因）
# =============================================================================

set -e

# 日志：写入当前 session 的日志文件（latest 是 server.ts 创建的软链接）
log_sandbox() {
  local LOGS_DIR="$HOME/.claude/channels/feishu/logs"
  local LOG="$LOGS_DIR/latest"
  if [ ! -e "$LOG" ]; then
    mkdir -p "$LOGS_DIR"
    LOG="$LOGS_DIR/sandbox.log"
  fi
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%S.000Z')] sandbox-bash: $1" >> "$LOG" 2>/dev/null
}

# ---------------------------------------------------------------------------
# 配置文件
# ---------------------------------------------------------------------------

CONF="$HOME/.claude/channels/feishu/sandbox-bash.conf"
PATH_CONF="$HOME/.claude/channels/feishu/sandbox.conf"

# 安全降级策略：配置缺失 → 阻止所有命令
if [ ! -f "$CONF" ]; then
  echo "feishu-sandbox: blocked (sandbox-bash.conf missing — reinstall feishu-channel-sandbox or create $CONF)" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# 从 stdin 读取 hook 输入 JSON
# ---------------------------------------------------------------------------

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

# 空命令放行
[ -z "$COMMAND" ] && exit 0

# ---------------------------------------------------------------------------
# 路径检查工具函数（与 sandbox-file.sh 相同逻辑）
# ---------------------------------------------------------------------------

expand_home() {
  echo "${1/#\~/$HOME}"
}

canonicalize() {
  local p="$1"
  if command -v realpath &>/dev/null; then
    realpath -m "$p" 2>/dev/null || echo "$p"
  else
    python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$p" 2>/dev/null || echo "$p"
  fi
}

# 检查单个路径是否在允许范围内（cwd + sandbox.conf）
is_path_allowed() {
  local CANONICAL=$(canonicalize "$(expand_home "$1")")

  # cwd 自动放行
  if [[ -n "$CWD" ]]; then
    local CWD_C=$(canonicalize "$CWD")
    [[ "$CANONICAL" == "$CWD_C"* ]] && return 0
  fi

  # 检查 sandbox.conf
  if [ -f "$PATH_CONF" ]; then
    while IFS= read -r line; do
      [[ "$line" =~ ^[[:space:]]*# ]] && continue
      [[ -z "${line// /}" ]] && continue
      local ALLOWED=$(canonicalize "$(expand_home "$(echo "$line" | xargs)")")
      [[ "$CANONICAL" == "$ALLOWED"* ]] && return 0
    done < "$PATH_CONF"
  fi

  return 1
}

# ---------------------------------------------------------------------------
# 第 1 层：命令前缀白名单
# ---------------------------------------------------------------------------

ALLOWED_PREFIX=false
while IFS= read -r line; do
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${line// /}" ]] && continue

  PREFIX=$(echo "$line" | xargs)
  if [[ "$COMMAND" == "$PREFIX"* ]]; then
    ALLOWED_PREFIX=true
    break
  fi
done < "$CONF"

if [ "$ALLOWED_PREFIX" != "true" ]; then
  log_sandbox "BLOCK command=${COMMAND:0:120} (not in allowlist)"
  echo "feishu-sandbox: blocked command (not in allowlist, edit $CONF to customize)" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# 第 2 层：检查命令中的文件路径
# ---------------------------------------------------------------------------
# 用正则从命令字符串中提取所有路径形式的子串：
#   - 绝对路径：/path/to/file
#   - 主目录相对：~/path 或 ~
#   - 上级遍历：../path
# /dev/* 始终放行（如 /dev/null）

PATH_RE='(/[^[:space:];|&>]+|~(/[^[:space:];|&>]*)?|\.\./[^[:space:];|&>]*)'
PATHS=$(echo "$COMMAND" | grep -oE "$PATH_RE" || true)

BLOCKED_PATH=""
while IFS= read -r p; do
  [ -z "$p" ] && continue
  # /dev/* 始终放行（/dev/null、/dev/zero 等）
  [[ "$p" == /dev/* ]] && continue
  if ! is_path_allowed "$p"; then
    BLOCKED_PATH="$p"
    break
  fi
done <<< "$PATHS"

if [ -n "$BLOCKED_PATH" ]; then
  RESOLVED=$(canonicalize "$(expand_home "$BLOCKED_PATH")")
  log_sandbox "BLOCK command=${COMMAND:0:120} (path $RESOLVED not allowed)"
  echo "feishu-sandbox: blocked (path $BLOCKED_PATH not in allowed paths, edit $PATH_CONF)" >&2
  exit 2
fi

log_sandbox "ALLOW command=${COMMAND:0:120}"
exit 0
