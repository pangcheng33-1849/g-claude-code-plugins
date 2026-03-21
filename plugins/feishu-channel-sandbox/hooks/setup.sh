#!/bin/bash
# =============================================================================
# setup.sh — 沙盒初始化
# =============================================================================
#
# 作为 SessionStart hook 运行，在会话启动时创建默认配置文件。
# 仅在配置文件不存在时创建，已有的配置不会被覆盖。
#
# 创建两个配置文件：
#   1. sandbox.conf      — 文件路径白名单（供 sandbox-file.sh 使用）
#   2. sandbox-bash.conf — 命令前缀白名单（供 sandbox-bash.sh 使用）
#
# 配置文件位置：~/.claude/channels/feishu/
# 用户可随时编辑这些文件来自定义沙盒规则。
# =============================================================================

# 确保配置目录存在
CONF_DIR="$HOME/.claude/channels/feishu"
mkdir -p "$CONF_DIR"

# -------------------------------------------------------------------------
# 文件路径白名单
# -------------------------------------------------------------------------
# sandbox-file.sh 会读取此文件，决定哪些路径允许 Read/Write/Edit。
# 注意：Claude 的工作目录（cwd）会被 sandbox-file.sh 自动放行，无需在此列出。
# 这里只需配置额外需要访问的路径。
FILE_CONF="$CONF_DIR/sandbox.conf"
if [ ! -f "$FILE_CONF" ]; then
  cat > "$FILE_CONF" << 'DEFAULTS'
# feishu-channel-sandbox: allowed file paths (one per line)
# Lines starting with # are comments. Paths are prefix-matched after canonicalization.
# Claude's working directory (cwd) is always allowed automatically.
# Edit this file to customize. Remove feishu-channel-sandbox plugin to disable.

# Feishu channel state
~/.claude/channels/feishu

# Temp files
/tmp
DEFAULTS
fi

# -------------------------------------------------------------------------
# 命令前缀白名单
# -------------------------------------------------------------------------
# sandbox-bash.sh 会读取此文件，决定哪些 Bash 命令允许执行。
# 匹配规则：命令必须以配置中某行的内容为前缀。
# 例如 "git status" 允许 "git status --short"，但不允许 "git push"。
# 如果只写 "git"，则允许所有 git 子命令，请谨慎配置。
#
# 默认只允许只读/信息类命令，不包含写入或网络操作。
BASH_CONF="$CONF_DIR/sandbox-bash.conf"
if [ ! -f "$BASH_CONF" ]; then
  cat > "$BASH_CONF" << 'DEFAULTS'
# feishu-channel-sandbox: allowed bash command prefixes (one per line)
# Lines starting with # are comments. Commands must start with an allowed prefix.
# Edit this file to customize. Remove feishu-channel-sandbox plugin to disable.

# Common safe commands
ls
cat
head
tail
wc
echo
printf
date
pwd
whoami
which
file
stat
du
df
find
sort
uniq
grep
rg
ag
sed
awk
cut
tr
diff
jq
yq

# Version/info commands
git status
git log
git diff
git show
git branch
node --version
python3 --version
bun --version

# Package info (read-only)
npm list
npm info
pip list
pip show

# Process info
ps
top -l 1
DEFAULTS
fi
