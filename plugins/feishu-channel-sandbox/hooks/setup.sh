#!/bin/bash
# =============================================================================
# setup.sh — 沙盒初始化
# =============================================================================
#
# 作为 SessionStart hook 运行：
#   1. 同步 profiles 到运行时目录（每次会话）
#   2. 创建默认配置软链接（仅首次）
#
# 活跃配置（sandbox.conf、sandbox-bash.conf）是指向 profiles/ 下对应文件的软链接。
# 切换配置集只需改变软链接指向，查询当前配置集只需检查链接目标。
# =============================================================================

# 确保配置目录存在
CONF_DIR="$HOME/.claude/channels/feishu"
mkdir -p "$CONF_DIR"

# 定位 profiles 目录（skill 目录下）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
PROFILES_SRC="$PLUGIN_DIR/skills/sandbox-profile/profiles"

# -------------------------------------------------------------------------
# 同步预设 profiles 到运行时目录
# -------------------------------------------------------------------------
# sandbox hook 会拦截从插件缓存目录读取文件，因此 skill 无法直接读取插件内的 profiles。
# 将 profiles 复制到 ~/.claude/channels/feishu/profiles/（在沙盒白名单内），
# 每次会话启动都同步，确保插件更新后配置跟进。
# 如果用户手动修改过预设 profile，先备份再覆盖。
PROFILES_DST="$CONF_DIR/profiles"
if [ -d "$PROFILES_SRC" ]; then
  mkdir -p "$PROFILES_DST"
  for src_file in "$PROFILES_SRC"/*.conf; do
    [ ! -f "$src_file" ] && continue
    filename=$(basename "$src_file")
    dst_file="$PROFILES_DST/$filename"
    if [ -f "$dst_file" ]; then
      if ! diff -q "$src_file" "$dst_file" >/dev/null 2>&1; then
        backup="${dst_file%.conf}.$(date +%Y%m%d%H%M%S).bak"
        cp "$dst_file" "$backup"
        echo "feishu-sandbox: preset profile $filename was modified locally, backed up to $(basename "$backup")" >&2
      fi
    fi
    cp "$src_file" "$dst_file"
  done
fi

# -------------------------------------------------------------------------
# 初始化活跃配置（仅首次，已有配置不覆盖）
# -------------------------------------------------------------------------
# 用软链接指向 profiles/ 下的 default 配置。
# -e 检查链接目标是否存在（断链返回 false），-L 检查是否是软链接。
FILE_CONF="$CONF_DIR/sandbox.conf"
if [ ! -e "$FILE_CONF" ] && [ ! -L "$FILE_CONF" ]; then
  ln -sf "$PROFILES_DST/default-sandbox.conf" "$FILE_CONF"
fi

BASH_CONF="$CONF_DIR/sandbox-bash.conf"
if [ ! -e "$BASH_CONF" ] && [ ! -L "$BASH_CONF" ]; then
  ln -sf "$PROFILES_DST/default-bash.conf" "$BASH_CONF"
fi
