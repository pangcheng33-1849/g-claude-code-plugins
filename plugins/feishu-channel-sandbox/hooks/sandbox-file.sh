#!/bin/bash
# =============================================================================
# sandbox-file.sh — 文件访问沙盒
# =============================================================================
#
# 作为 PreToolUse hook 拦截 Read/Write/Edit 工具调用，
# 检查目标文件路径是否在允许的白名单范围内。
#
# 安全策略：
#   - fail-closed：配置文件缺失时阻止所有操作（exit 2），而非放行
#   - 路径规范化：通过 realpath 解析 ../ 遍历和符号链接，防止绕过
#   - 前缀匹配：规范化后的路径必须以白名单中某个路径为前缀
#
# 白名单来源（按优先级）：
#   1. Claude 的工作目录（cwd）— 从 hook 输入自动获取，无需配置
#   2. sandbox.conf 中列出的路径 — 用户可编辑
#
# 输入：PreToolUse hook 的 JSON（通过 stdin），包含 tool_input.file_path 和 cwd
# 输出：exit 0 = 放行，exit 2 = 阻止（stderr 输出原因）
# =============================================================================

set -e

# 日志：写入当前 session 的日志文件（.session 是 server.ts 创建的软链接，指向 logs/ 下的会话日志）
log_sandbox() {
  local LOGS_DIR="$HOME/.claude/channels/feishu/logs"
  local LOG="$LOGS_DIR/latest"
  if [ ! -e "$LOG" ]; then
    mkdir -p "$LOGS_DIR"
    LOG="$LOGS_DIR/sandbox.log"
  fi
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%S.000Z')] sandbox-file: $1" >> "$LOG" 2>/dev/null
}

# 白名单配置文件路径，由 setup.sh 在 SessionStart 时创建
CONF="$HOME/.claude/channels/feishu/sandbox.conf"

# 安全降级策略：配置缺失 → 阻止所有操作
# 这防止了通过删除配置文件来禁用沙盒的攻击
if [ ! -f "$CONF" ]; then
  echo "feishu-sandbox: blocked (sandbox.conf missing — reinstall feishu-channel-sandbox or create $CONF)" >&2
  exit 2
fi

# 从 stdin 读取 hook 输入 JSON，提取文件路径和工作目录
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

# 某些工具调用可能没有 file_path（如特殊模式），放行
[ -z "$FILE_PATH" ] && exit 0

# 展开 ~ 为 $HOME（配置文件和用户输入都可能使用 ~ 表示主目录）
expand_home() {
  echo "${1/#\~/$HOME}"
}

# 路径规范化函数：解析 ../ 序列和符号链接，返回绝对路径
# 使用 realpath -m（允许路径不存在，Write 工具写新文件时需要）
# 兼容性：优先 realpath（Linux），回退 python3（macOS），最后原样返回
canonicalize() {
  local p="$1"
  local result
  # 优先尝试 GNU realpath -m（支持不存在的路径）
  result=$(realpath -m "$p" 2>/dev/null) && { echo "$result"; return; }
  # macOS 的 realpath 不支持 -m，回退到 python3
  python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$p" 2>/dev/null || echo "$p"
}

# 对输入路径进行展开和规范化
# 例如 /tmp/../etc/passwd → /etc/passwd，~/.ssh → /Users/xxx/.ssh
FILE_PATH_EXPANDED=$(expand_home "$FILE_PATH")
FILE_PATH_CANONICAL=$(canonicalize "$FILE_PATH_EXPANDED")

# 检查 1：Claude 工作目录自动放行
# cwd 也需要规范化，防止 cwd 本身包含符号链接
if [[ -n "$CWD" ]]; then
  CWD_CANONICAL=$(canonicalize "$CWD")
  if [[ "$FILE_PATH_CANONICAL" == "$CWD_CANONICAL" || "$FILE_PATH_CANONICAL" == "$CWD_CANONICAL/"* ]]; then
    log_sandbox "ALLOW path=$FILE_PATH_CANONICAL (cwd)"
    exit 0
  fi
fi

# 检查 2：逐行读取 sandbox.conf，支持 glob 模式匹配和前缀匹配
while IFS= read -r line; do
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${line// /}" ]] && continue

  TRIMMED_LINE=$(echo "$line" | xargs)

  # 含 glob 元字符 → glob 匹配（同时检查规范化路径和原始路径，兼容 symlink）
  if [[ "$TRIMMED_LINE" == *'*'* || "$TRIMMED_LINE" == *'?'* || "$TRIMMED_LINE" == *'['* ]]; then
    if [[ "$FILE_PATH_CANONICAL" == $TRIMMED_LINE ]]; then
      log_sandbox "ALLOW path=$FILE_PATH_CANONICAL (glob: $TRIMMED_LINE)"
      exit 0
    fi
    if [[ "$FILE_PATH_EXPANDED" != "$FILE_PATH_CANONICAL" && "$FILE_PATH_EXPANDED" == $TRIMMED_LINE ]]; then
      log_sandbox "ALLOW path=$FILE_PATH_EXPANDED (glob via original: $TRIMMED_LINE)"
      exit 0
    fi
    continue
  fi

  # 无 glob 元字符 → 展开 ~，规范化，目录边界前缀匹配
  ALLOWED_CANONICAL=$(canonicalize "$(expand_home "$TRIMMED_LINE")")
  if [[ "$FILE_PATH_CANONICAL" == "$ALLOWED_CANONICAL" || "$FILE_PATH_CANONICAL" == "$ALLOWED_CANONICAL/"* ]]; then
    log_sandbox "ALLOW path=$FILE_PATH_CANONICAL"
    exit 0
  fi
done < "$CONF"

# 所有检查都未通过，阻止操作并输出详细信息便于排查
log_sandbox "BLOCK path=$FILE_PATH_CANONICAL (original: $FILE_PATH)"
echo "feishu-sandbox: blocked $FILE_PATH (resolved: $FILE_PATH_CANONICAL, not in allowed paths). Read $CONF to see allowed paths." >&2
exit 2
