#!/bin/bash
# =============================================================================
# sandbox-bash.sh — 命令执行沙盒
# =============================================================================
#
# 作为 PreToolUse hook 拦截 Bash 工具调用，执行三层检查：
#   1. 命令拆分 + 子 shell 检测 — 拒绝 $()、``、<()、>() 构造
#   2. glob 模式白名单 — 管道/链式命令的每一段都必须匹配白名单
#   3. 路径白名单 — 命令中出现的文件路径必须在允许范围内
#
# 第一层防止通过子 shell 执行任意命令。
# 第二层防止通过管道/链式命令绕过白名单（如 echo ... | sh）。
# 第三层防止白名单命令（如 cat、ls）访问不在允许范围内的路径。
#
# 安全策略：
#   - 白名单模式（而非黑名单）：只允许明确列出的命令
#   - fail-closed：配置文件缺失时阻止所有命令
#   - 子 shell 阻止：$()、``、<()、>() 构造被直接拒绝
#   - 管道/链式拆分：按引号感知方式拆分命令，每段独立校验
#   - 路径前缀匹配包含目录边界检查，防止 /tmp 匹配 /tmpevil
#   - 路径检查复用 sandbox.conf 的白名单 + cwd 自动放行
#
# 白名单配置：~/.claude/channels/feishu/sandbox-bash.conf
#   支持两种匹配模式：
#   - 无 glob 字符（如 "git status"）→ 前缀匹配，允许 "git status --short" 等
#   - 含 glob 字符（如 "python3 /*/.claude/skills/*.py"）→ bash glob 匹配
#   glob 中 * 匹配任意字符（含 / 和空格），对齐 Claude Code allow 机制风格。
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
  local result
  # 优先尝试 GNU realpath -m（支持不存在的路径）
  result=$(realpath -m "$p" 2>/dev/null) && { echo "$result"; return; }
  # macOS 的 realpath 不支持 -m，回退到 python3
  python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$p" 2>/dev/null || echo "$p"
}

# 检查单个路径是否在允许范围内（cwd + sandbox.conf）
# 使用目录边界匹配：/tmp 允许 /tmp/foo 但不允许 /tmpevil
is_path_allowed() {
  local CANONICAL=$(canonicalize "$(expand_home "$1")")

  # cwd 自动放行
  if [[ -n "$CWD" ]]; then
    local CWD_C=$(canonicalize "$CWD")
    [[ "$CANONICAL" == "$CWD_C" || "$CANONICAL" == "$CWD_C/"* ]] && return 0
  fi

  # 检查 sandbox.conf（支持 glob 模式匹配）
  if [ -f "$PATH_CONF" ]; then
    while IFS= read -r line; do
      [[ "$line" =~ ^[[:space:]]*# ]] && continue
      [[ -z "${line// /}" ]] && continue
      local PATTERN=$(echo "$line" | xargs)

      # 含 glob 元字符 → glob 匹配
      if [[ "$PATTERN" == *'*'* || "$PATTERN" == *'?'* || "$PATTERN" == *'['* ]]; then
        [[ "$CANONICAL" == $PATTERN ]] && return 0
      else
        # 无 glob 元字符 → 展开 ~，规范化，目录边界前缀匹配
        local ALLOWED=$(canonicalize "$(expand_home "$PATTERN")")
        [[ "$CANONICAL" == "$ALLOWED" || "$CANONICAL" == "$ALLOWED/"* ]] && return 0
      fi
    done < "$PATH_CONF"
  fi

  return 1
}

# ---------------------------------------------------------------------------
# 命令拆分：按 shell 操作符拆分，检测子 shell 构造
# ---------------------------------------------------------------------------
# 按未转义、不在引号内的管道/链式操作符（|、&&、||、;、换行）拆分命令。
# 如果发现子 shell 构造（$(...)、`...`、<(...)、>(...)），直接阻止。
# 结果存入全局数组 CMD_SEGMENTS。
# 返回 0 = 正常拆分，1 = 发现子 shell 构造

split_command_segments() {
  local cmd="$1"
  local len=${#cmd}
  local i=0
  local seg=""
  local sq=false  # in single quote
  local dq=false  # in double quote
  CMD_SEGMENTS=()

  while (( i < len )); do
    local c="${cmd:i:1}"
    local nc="${cmd:i+1:1}"

    # 单引号内：只检测结束引号，其他一切按字面处理
    if [[ "$sq" == true ]]; then
      [[ "$c" == "'" ]] && sq=false
      seg+="$c"; (( i++ )); continue
    fi

    # 反斜杠转义（单引号外有效）
    if [[ "$c" == '\' ]]; then
      seg+="${cmd:i:2}"; (( i += 2 )); continue
    fi

    # 单引号开始
    if [[ "$c" == "'" ]]; then
      sq=true; seg+="$c"; (( i++ )); continue
    fi

    # 双引号切换
    if [[ "$c" == '"' ]]; then
      if [[ "$dq" == true ]]; then dq=false; else dq=true; fi
      seg+="$c"; (( i++ )); continue
    fi

    # 子 shell 检测（双引号内和引号外都生效，单引号内已在上面跳过）
    if [[ "$c" == '$' ]] && [[ "$nc" == '(' ]]; then return 1; fi
    if [[ "$c" == '`' ]]; then return 1; fi

    # 以下仅在引号外生效
    if [[ "$dq" == false ]]; then
      # 进程替换 <( >(
      if [[ "$c" == '<' ]] && [[ "$nc" == '(' ]]; then return 1; fi
      if [[ "$c" == '>' ]] && [[ "$nc" == '(' ]]; then return 1; fi

      # 管道 | 或逻辑或 ||
      if [[ "$c" == '|' ]]; then
        CMD_SEGMENTS+=("$seg"); seg=""
        [[ "$nc" == '|' ]] && (( i++ ))
        (( i++ )); continue
      fi

      # 逻辑与 &&
      if [[ "$c" == '&' ]] && [[ "$nc" == '&' ]]; then
        CMD_SEGMENTS+=("$seg"); seg=""
        (( i += 2 )); continue
      fi

      # 顺序执行 ; 和换行
      if [[ "$c" == ';' ]] || [[ "$c" == $'\n' ]]; then
        CMD_SEGMENTS+=("$seg"); seg=""
        (( i++ )); continue
      fi
    fi

    seg+="$c"; (( i++ ))
  done

  CMD_SEGMENTS+=("$seg")
  return 0
}

# 检查单个命令段是否匹配白名单
# 使用 bash 原生 glob 匹配（对齐 Claude Code allow 机制）：
#   - 含 glob 元字符（* ? [）的行 → [[ "$cmd" == $PATTERN ]] glob 匹配
#   - 无 glob 元字符的行 → 前缀匹配（自动追加 *）
# ~ 在匹配前展开为 $HOME
is_prefix_allowed() {
  local segment="$1"
  segment=$(echo "$segment" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
  [ -z "$segment" ] && return 0  # 空段放行

  while IFS= read -r line; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// /}" ]] && continue
    local PATTERN=$(echo "$line" | xargs)
    PATTERN="${PATTERN//\~/$HOME}"

    # 含 glob 元字符 → glob 匹配；无 → 前缀匹配
    if [[ "$PATTERN" == *'*'* || "$PATTERN" == *'?'* || "$PATTERN" == *'['* ]]; then
      [[ "$segment" == $PATTERN ]] && return 0
    else
      [[ "$segment" == "$PATTERN"* ]] && return 0
    fi
  done < "$CONF"

  return 1
}

# ---------------------------------------------------------------------------
# 第 1 层：命令拆分 + 子 shell 检测
# ---------------------------------------------------------------------------

if ! split_command_segments "$COMMAND"; then
  log_sandbox "BLOCK command=${COMMAND:0:120} (subshell construct detected)"
  echo "feishu-sandbox: blocked command (subshell constructs like \$(), \`\`, <(), >() are not allowed)" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# 第 2 层：每段命令前缀白名单
# ---------------------------------------------------------------------------

for seg in "${CMD_SEGMENTS[@]}"; do
  if ! is_prefix_allowed "$seg"; then
    TRIMMED=$(echo "$seg" | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
    log_sandbox "BLOCK command=${COMMAND:0:120} (segment '${TRIMMED:0:60}' not in allowlist)"
    echo "feishu-sandbox: blocked command (segment '${TRIMMED:0:60}' not in allowlist). Read $CONF to see allowed command prefixes, read $PATH_CONF to see allowed paths." >&2
    exit 2
  fi
done

# ---------------------------------------------------------------------------
# 第 3 层：检查命令中的文件路径
# ---------------------------------------------------------------------------
# 用正则从命令字符串中提取所有路径形式的子串：
#   - 绝对路径：/path/to/file
#   - 主目录相对：~/path 或 ~
#   - 上级遍历：../path
# /dev/* 始终放行（如 /dev/null）
#
# 路径必须出现在词边界（前面是空白、> < = 或字符串开头），
# 避免从 git 引用（HEAD~1、feature/new）、URL（https://...）等中误提取。

PATH_RE='[[:space:]><=](/[^[:space:];|&>]+|~(/[^[:space:];|&>]*)?|\.\./[^[:space:];|&>]*)'
PATHS=$(echo " $COMMAND" | grep -oE "$PATH_RE" | sed 's/^[[:space:]><=]//' || true)

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
  echo "feishu-sandbox: blocked (path $BLOCKED_PATH not in allowed paths). Read $PATH_CONF to see allowed paths." >&2
  exit 2
fi

log_sandbox "ALLOW command=${COMMAND:0:120}"
exit 0
