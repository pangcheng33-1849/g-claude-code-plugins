#!/bin/bash
# =============================================================================
# test-sandbox.sh — sandbox-bash.sh / sandbox-file.sh 安全测试
# =============================================================================
#
# 用法：
#   cd plugins/feishu-channel-sandbox
#   bash tests/test-sandbox.sh
#
# 测试使用临时配置目录，不影响真实配置。
# 分三部分：安全机制测试（default profile）→ default profile 行为 → dev profile 行为
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# 测试框架
# ---------------------------------------------------------------------------

PASS=0
FAIL=0
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BASH_HOOK="$SCRIPT_DIR/hooks/sandbox-bash.sh"
FILE_HOOK="$SCRIPT_DIR/hooks/sandbox-file.sh"

# 临时配置目录（测试完清理）
TEST_HOME=$(mktemp -d)
export HOME="$TEST_HOME"
CONF_DIR="$TEST_HOME/.claude/channels/feishu"
mkdir -p "$CONF_DIR/logs"

# 模拟 cwd
TEST_CWD="/Users/testuser/project"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

run_bash_hook() {
  local cmd="$1"
  local cwd="${2:-$TEST_CWD}"
  local json
  json=$(jq -n --arg cmd "$cmd" --arg cwd "$cwd" '{tool_input:{command:$cmd},cwd:$cwd}')
  echo "$json" | bash "$BASH_HOOK" 2>/dev/null
}

run_file_hook() {
  local path="$1"
  local cwd="${2:-$TEST_CWD}"
  local json
  json=$(jq -n --arg path "$path" --arg cwd "$cwd" '{tool_input:{file_path:$path},cwd:$cwd}')
  echo "$json" | bash "$FILE_HOOK" 2>/dev/null
}

expect_allow() {
  local desc="$1"
  shift
  if "$@" ; then
    PASS=$((PASS + 1))
    echo -e "  ${GREEN}✓ ALLOW${NC}  $desc"
  else
    FAIL=$((FAIL + 1))
    echo -e "  ${RED}✗ FAIL${NC}   $desc  (expected ALLOW, got BLOCK)"
  fi
}

expect_block() {
  local desc="$1"
  shift
  if "$@" ; then
    FAIL=$((FAIL + 1))
    echo -e "  ${RED}✗ FAIL${NC}   $desc  (expected BLOCK, got ALLOW)"
  else
    PASS=$((PASS + 1))
    echo -e "  ${GREEN}✓ BLOCK${NC} $desc"
  fi
}

# 初始化运行时 profiles（模拟 setup.sh 的同步行为）
PROFILES_DST="$CONF_DIR/profiles"
mkdir -p "$PROFILES_DST"
cp "$SCRIPT_DIR/skills/sandbox-profile/profiles/"*.conf "$PROFILES_DST/"

# 切换配置集（模拟 skill 的 ln -sf 行为）
switch_profile() {
  local profile="$1"
  ln -sf "$PROFILES_DST/${profile}-bash.conf" "$CONF_DIR/sandbox-bash.conf"
  ln -sf "$PROFILES_DST/${profile}-sandbox.conf" "$CONF_DIR/sandbox.conf"
}

# ══════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          安全机制测试（三层检查 + 路径边界）         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
# ══════════════════════════════════════════════════════════════════════════

# 使用 default profile
switch_profile default

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── 第 1 层：子 shell 检测 ──${NC}"
# ---------------------------------------------------------------------------

expect_block '$(cmd) 命令替换' \
  run_bash_hook 'echo $(cat /etc/passwd)'

expect_block '反引号命令替换' \
  run_bash_hook 'echo `cat /etc/passwd`'

expect_block '<() 进程替换' \
  run_bash_hook 'diff <(ls) /dev/null'

expect_block '>() 进程替换' \
  run_bash_hook 'cat file >(grep foo)'

expect_block '双引号内的 $()' \
  run_bash_hook 'echo "$(whoami)"'

expect_block 'base64 解码 + 子 shell' \
  run_bash_hook 'echo $(echo Y2F0IC9ldGMvcGFzc3dk | base64 -d)'

expect_allow '单引号内的 $()（字面量，不触发子 shell 检测）' \
  run_bash_hook "echo '\$(date)'"

expect_allow '单引号内的反引号（字面量，不触发子 shell 检测）' \
  run_bash_hook "echo '\`whoami\`'"

expect_block '单引号内 $() 但路径被限制（路径层拦截）' \
  run_bash_hook "echo '\$(cat /etc/passwd)'"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── 第 2 层：管道/链式命令拆分校验 ──${NC}"
# ---------------------------------------------------------------------------

expect_block 'echo | sh（sh 不在白名单）' \
  run_bash_hook 'echo "payload" | sh'

expect_block 'echo | bash（bash 不在白名单）' \
  run_bash_hook 'echo "payload" | bash'

expect_block 'echo | base64 -d | sh' \
  run_bash_hook 'echo "Y2F0Cg==" | base64 -d | sh'

expect_block 'ls ; rm -rf /（rm 不在白名单）' \
  run_bash_hook 'ls ; rm -rf /'

expect_block 'echo && python3 -c "..."（python3 不在白名单）' \
  run_bash_hook 'echo ok && python3 -c "import os; os.system(\"id\")"'

expect_block 'echo || curl（curl 不在白名单）' \
  run_bash_hook 'echo fail || curl http://evil.com'

expect_allow 'echo hello（简单命令）' \
  run_bash_hook 'echo hello'

expect_allow 'grep foo | wc -l（两段都在白名单）' \
  run_bash_hook 'grep foo file.txt | wc -l'

expect_allow 'cat | head -5（两段都在白名单）' \
  run_bash_hook 'cat file.txt | head -5'

expect_allow 'ls -la && echo done（两段都在白名单）' \
  run_bash_hook 'ls -la && echo done'

expect_allow 'git status | grep modified' \
  run_bash_hook 'git status | grep modified'

expect_allow '引号内的管道符不拆分' \
  run_bash_hook 'echo "hello | world"'

expect_allow '引号内的分号不拆分' \
  run_bash_hook 'echo "a; b; c"'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── 第 3 层：路径检查 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'cat cwd 内的文件' \
  run_bash_hook "cat $TEST_CWD/src/main.ts"

expect_allow 'ls /tmp（在白名单）' \
  run_bash_hook 'ls /tmp'

expect_allow 'cat /tmp/foo.txt（在白名单子路径）' \
  run_bash_hook 'cat /tmp/foo.txt'

expect_block 'cat ~/Downloads/file（不在白名单）' \
  run_bash_hook 'cat ~/Downloads/file.txt'

expect_block 'ls ~/Desktop（不在白名单）' \
  run_bash_hook 'ls ~/Desktop'

expect_allow 'echo /dev/null（/dev 始终放行）' \
  run_bash_hook 'echo test > /dev/null'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── 路径边界检查 ──${NC}"
# ---------------------------------------------------------------------------

expect_block '/tmpevil（/tmp 不应匹配 /tmpevil）' \
  run_bash_hook 'cat /tmpevil/secret.txt'

expect_allow '/tmp/safe（/tmp 子路径正常放行）' \
  run_bash_hook 'cat /tmp/safe.txt'

expect_block '${CWD}-secrets（cwd 不应匹配 cwd-secrets）' \
  run_bash_hook "cat ${TEST_CWD}-secrets/key.pem"

expect_allow 'cwd 本身' \
  run_bash_hook "cat $TEST_CWD"

expect_allow 'cwd 子路径' \
  run_bash_hook "cat $TEST_CWD/deep/nested/file.ts"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── sandbox-file.sh：路径白名单 + 边界 + 遍历 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'cwd 内文件' \
  run_file_hook "$TEST_CWD/src/index.ts"

expect_allow '/tmp 内文件' \
  run_file_hook '/tmp/output.json'

expect_allow '~/.claude/channels/feishu 内文件' \
  run_file_hook "$TEST_HOME/.claude/channels/feishu/sandbox.conf"

expect_block '~/Downloads' \
  run_file_hook "$TEST_HOME/Downloads/secret.pdf"

expect_block '/etc/passwd' \
  run_file_hook '/etc/passwd'

expect_block '~/.ssh/id_rsa' \
  run_file_hook "$TEST_HOME/.ssh/id_rsa"

expect_block '/tmpevil（边界）' \
  run_file_hook '/tmpevil/secret.txt'

expect_block '${CWD}-secrets（cwd 边界）' \
  run_file_hook "${TEST_CWD}-secrets/key.pem"

expect_block 'feishu-evil（白名单边界）' \
  run_file_hook "$TEST_HOME/.claude/channels/feishu-evil/config"

expect_allow 'feishu/ 子路径' \
  run_file_hook "$TEST_HOME/.claude/channels/feishu/logs/latest"

expect_block '../ 遍历逃逸 cwd' \
  run_file_hook "$TEST_CWD/../../../etc/passwd"

expect_block '/tmp/../etc/passwd' \
  run_file_hook '/tmp/../etc/passwd'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── glob 路径匹配 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow '~/.claude/plugins 内文件（精确前缀）' \
  run_file_hook "$TEST_HOME/.claude/plugins/cache/abc/script.py"

expect_allow '*/.claude/skills 匹配 cwd 祖先' \
  run_file_hook "/Users/testuser/.claude/skills/my-skill/SKILL.md"

expect_allow '*/.claude/commands 匹配用户级' \
  run_file_hook "$TEST_HOME/.claude/commands/my-cmd.md"

expect_allow '*/.claude/agents 匹配项目祖先' \
  run_file_hook "/Users/testuser/workspace/.claude/agents/helper.md"

expect_allow '*/.claude/skills 深层子路径' \
  run_file_hook "/some/repo/.claude/skills/my-skill/scripts/helper.py"

expect_block '*/.claude 本身不匹配（需要具体子目录）' \
  run_file_hook "/Users/testuser/.claude/settings.json"

expect_block '非 .claude 目录不匹配通配' \
  run_file_hook "/Users/testuser/.config/skills/foo"

expect_allow 'Bash 路径检查也支持通配' \
  run_bash_hook "cat /Users/testuser/.claude/skills/my-skill/SKILL.md"

expect_allow 'Bash 插件缓存路径' \
  run_bash_hook "cat $TEST_HOME/.claude/plugins/cache/foo/script.py"

expect_block 'Bash ~/.claude/settings.json 仍被拦截' \
  run_bash_hook "cat $TEST_HOME/.claude/settings.json"

expect_block '通配不匹配 .claude-evil/skills（目录边界）' \
  run_file_hook "/Users/testuser/.claude-evil/skills/foo.md"

expect_allow '通配匹配多级祖先的 .claude/skills' \
  run_file_hook "/a/.claude/skills/deep/nested/file.py"

expect_block '通配不匹配 .claude/skill（少了 s）' \
  run_file_hook "/Users/testuser/.claude/skill/foo.md"

expect_allow '插件 data 目录（~/.claude/plugins 子路径）' \
  run_file_hook "$TEST_HOME/.claude/plugins/data/my-plugin/state.json"

expect_block '~/.claude/rules 不在白名单' \
  run_file_hook "$TEST_HOME/.claude/rules/my-rule.md"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── ~ 展开与 glob 模式的交叉测试（sandbox-bash 层） ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'cp 白名单（~ 展开）' \
  run_bash_hook "cp $TEST_HOME/.claude/channels/feishu/profiles/dev-bash.conf $TEST_HOME/.claude/channels/feishu/profiles/custom-bash.conf"

expect_allow 'rm 白名单（~ 展开）' \
  run_bash_hook "rm $TEST_HOME/.claude/channels/feishu/profiles/custom-bash.conf"

expect_block 'rm 非白名单路径（~ 展开不影响安全）' \
  run_bash_hook "rm $TEST_HOME/.claude/settings.json"

expect_block 'cp 源在白名单但目标不在' \
  run_bash_hook "cp $TEST_HOME/.claude/channels/feishu/profiles/dev-bash.conf ~/Desktop/stolen.conf"

expect_allow 'readlink 白名单文件' \
  run_bash_hook "readlink $TEST_HOME/.claude/channels/feishu/sandbox-bash.conf"

echo ""

# ══════════════════════════════════════════════════════════════════════════
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              DEFAULT profile 行为测试                ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
# ══════════════════════════════════════════════════════════════════════════

switch_profile default

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── 允许的只读命令 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'ls -la' \
  run_bash_hook 'ls -la'

expect_allow 'cat README.md' \
  run_bash_hook "cat $TEST_CWD/README.md"

expect_allow 'head -20 file' \
  run_bash_hook "head -20 $TEST_CWD/file.ts"

expect_allow 'tail -f log' \
  run_bash_hook "tail -f $TEST_CWD/app.log"

expect_allow 'wc -l' \
  run_bash_hook "wc -l $TEST_CWD/file.ts"

expect_allow 'grep pattern' \
  run_bash_hook "grep -r TODO $TEST_CWD/src"

expect_allow 'find . -name' \
  run_bash_hook "find $TEST_CWD -name '*.ts'"

expect_allow 'diff two files' \
  run_bash_hook "diff $TEST_CWD/a.ts $TEST_CWD/b.ts"

expect_allow 'jq query' \
  run_bash_hook "jq '.name' $TEST_CWD/package.json"

expect_allow 'sort | uniq' \
  run_bash_hook "sort $TEST_CWD/list.txt | uniq"

expect_allow 'sed pattern' \
  run_bash_hook "sed -n '1,10p' $TEST_CWD/file.ts"

expect_allow 'awk print' \
  run_bash_hook "awk '{print \$1}' $TEST_CWD/data.txt"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── 允许的 Git 只读命令 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'git status' \
  run_bash_hook 'git status'

expect_allow 'git log --oneline' \
  run_bash_hook 'git log --oneline -10'

expect_allow 'git diff' \
  run_bash_hook 'git diff HEAD~1'

expect_allow 'git show' \
  run_bash_hook 'git show HEAD:src/main.ts'

expect_allow 'git branch -a' \
  run_bash_hook 'git branch -a'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── 允许的版本/包信息命令 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'node --version' \
  run_bash_hook 'node --version'

expect_allow 'python3 --version' \
  run_bash_hook 'python3 --version'

expect_allow 'npm list' \
  run_bash_hook 'npm list --depth=0'

expect_allow 'pip list' \
  run_bash_hook 'pip list'

expect_allow 'ps' \
  run_bash_hook 'ps aux'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── default 应阻止的命令 ──${NC}"
# ---------------------------------------------------------------------------

expect_block 'git commit（非只读 git）' \
  run_bash_hook 'git commit -m "test"'

expect_block 'git push' \
  run_bash_hook 'git push origin main'

expect_block 'git checkout' \
  run_bash_hook 'git checkout -b new-branch'

expect_block 'npm install' \
  run_bash_hook 'npm install express'

expect_block 'npm run' \
  run_bash_hook 'npm run build'

expect_allow 'mkdir（channel skill 支持）' \
  run_bash_hook "mkdir -p $TEST_CWD/new-dir"

expect_block 'mkdir 受限路径' \
  run_bash_hook "mkdir ~/Downloads/evil"

expect_block 'rm' \
  run_bash_hook "rm $TEST_CWD/file.ts"

expect_block 'cp' \
  run_bash_hook "cp $TEST_CWD/a.ts $TEST_CWD/b.ts"

expect_block 'mv' \
  run_bash_hook "mv $TEST_CWD/old.ts $TEST_CWD/new.ts"

expect_block 'touch' \
  run_bash_hook "touch $TEST_CWD/new-file.ts"

expect_block 'curl' \
  run_bash_hook 'curl https://example.com'

expect_block 'wget' \
  run_bash_hook 'wget https://example.com'

expect_block 'node（运行脚本）' \
  run_bash_hook "node $TEST_CWD/script.js"

expect_block 'python3（运行脚本）' \
  run_bash_hook "python3 $TEST_CWD/script.py"

expect_block 'make' \
  run_bash_hook 'make build'

expect_block 'docker' \
  run_bash_hook 'docker ps'

expect_block 'kill' \
  run_bash_hook 'kill 12345'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── default 限定路径的脚本执行 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'python3 插件脚本（~ 展开匹配）' \
  run_bash_hook "python3 $TEST_HOME/.claude/plugins/cache/g-feishu/scripts/helper.py send-message"

expect_allow 'node 插件脚本' \
  run_bash_hook "node $TEST_HOME/.claude/plugins/cache/some-plugin/scripts/build.js"

expect_allow 'bash 插件脚本' \
  run_bash_hook "bash $TEST_HOME/.claude/plugins/cache/some-plugin/hooks/setup.sh"

expect_allow 'bun 插件脚本' \
  run_bash_hook "bun $TEST_HOME/.claude/plugins/cache/feishu-channel/server.ts"

expect_allow 'python3 项目 skill 脚本（*/ 通配）' \
  run_bash_hook "python3 /Users/testuser/workspace/.claude/skills/my-skill/scripts/run.py"

expect_allow 'node 项目 skill 脚本' \
  run_bash_hook "node /Users/testuser/workspace/.claude/skills/my-skill/scripts/tool.js"

expect_block 'python3 -c（裸执行仍被拦截）' \
  run_bash_hook 'python3 -c "import os; os.system(\"id\")"'

expect_block 'node -e（裸执行仍被拦截）' \
  run_bash_hook 'node -e "require(\"child_process\").execSync(\"id\")"'

# ── 通配路径伪造绕过测试 ──
# 在 -c 参数的字符串中嵌入 .claude/skills/ 路径，尝试欺骗 */ 通配匹配

expect_block 'python3 -c 内嵌 .claude/skills/ 路径（伪造通配）' \
  run_bash_hook 'python3 -c "x='"'"'/.claude/skills/'"'"'; import os; os.system('"'"'id'"'"')"'

expect_block 'node -e 内嵌 .claude/skills/ 路径（伪造通配）' \
  run_bash_hook 'node -e "x='"'"'/.claude/skills/'"'"'; require('"'"'child_process'"'"').execSync('"'"'id'"'"')"'

expect_block 'bash -c 内嵌 .claude/plugins/ 路径（伪造通配）' \
  run_bash_hook "bash -c 'echo /.claude/plugins/pwned'"

expect_block 'python3 --flag 后跟 skill 路径（非第一参数）' \
  run_bash_hook "python3 --verbose /Users/testuser/.claude/skills/my-skill/run.py"

expect_block 'python3 任意路径脚本' \
  run_bash_hook "python3 ~/Downloads/evil.py"

expect_block 'bash 任意路径脚本' \
  run_bash_hook "bash ~/evil.sh"

expect_block 'bun 任意路径脚本' \
  run_bash_hook "bun ~/Desktop/server.ts"

expect_block 'node 任意路径脚本' \
  run_bash_hook "node /etc/evil.js"

expect_allow 'python3 用户级 skill 脚本' \
  run_bash_hook "python3 $TEST_HOME/.claude/skills/my-tool/scripts/run.py --arg1 val"

expect_allow 'bash 祖先项目 skill 脚本' \
  run_bash_hook "bash /Users/testuser/.claude/skills/deploy/scripts/build.sh"

expect_allow 'node 深层嵌套 skill 脚本' \
  run_bash_hook "node /a/b/c/.claude/skills/lint/scripts/check.js --fix"

expect_allow 'bun 插件 skill 脚本' \
  run_bash_hook "bun $TEST_HOME/.claude/plugins/cache/my-plugin/skills/gen/scripts/run.ts"

expect_block 'python3 .claude 但非 skills/plugins 子目录' \
  run_bash_hook "python3 $TEST_HOME/.claude/settings.json"

expect_block 'node .claude/projects（不在白名单）' \
  run_bash_hook "node $TEST_HOME/.claude/projects/abc/memory/run.js"

expect_allow 'python3 插件脚本带管道（两段都需通过）' \
  run_bash_hook "python3 $TEST_HOME/.claude/plugins/cache/foo/script.py | grep result"

expect_block 'python3 插件脚本管道到 sh（sh 段被拦截）' \
  run_bash_hook "python3 $TEST_HOME/.claude/plugins/cache/foo/script.py | sh"

expect_allow 'python3 插件脚本带重定向 /dev/null' \
  run_bash_hook "python3 $TEST_HOME/.claude/plugins/cache/foo/script.py 2>/dev/null"

expect_allow 'ln -sf ~/.claude/channels/feishu（~ 展开兼容）' \
  run_bash_hook "ln -sf $TEST_HOME/.claude/channels/feishu/profiles/dev-bash.conf $TEST_HOME/.claude/channels/feishu/sandbox-bash.conf"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── glob 扩展名精确匹配 ──${NC}"
# ---------------------------------------------------------------------------

expect_block 'python3 .pyc 文件（扩展名不匹配）' \
  run_bash_hook "python3 /a/.claude/skills/s/run.pyc"

expect_block 'python3 .pyw 文件（扩展名不匹配）' \
  run_bash_hook "python3 /a/.claude/skills/s/run.pyw"

expect_block 'node .json 文件（扩展名不匹配）' \
  run_bash_hook "node /a/.claude/skills/s/data.json"

expect_block 'node .jsx 文件（扩展名不匹配）' \
  run_bash_hook "node /a/.claude/skills/s/component.jsx"

expect_block 'bash .bash 文件（扩展名不匹配）' \
  run_bash_hook "bash /a/.claude/skills/s/run.bash"

expect_block 'python3 无扩展名文件' \
  run_bash_hook "python3 /a/.claude/skills/s/run"

expect_allow 'python3 skill .py 带参数' \
  run_bash_hook "python3 /a/.claude/skills/s/run.py --arg1 val --arg2"

expect_allow 'node 插件 .js 带参数' \
  run_bash_hook "node $TEST_HOME/.claude/plugins/cache/foo/check.js --fix"

expect_allow 'bash skill .sh 无参数' \
  run_bash_hook "bash /a/b/.claude/skills/deploy/build.sh"

expect_allow 'bun skill .ts 带参数' \
  run_bash_hook "bun /a/.claude/skills/s/run.ts --watch"

expect_allow 'bun skill .js 无参数' \
  run_bash_hook "bun /a/.claude/skills/s/run.js"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── default 路径白名单 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'Read cwd 文件' \
  run_file_hook "$TEST_CWD/src/main.ts"

expect_allow 'Read /tmp 文件' \
  run_file_hook '/tmp/output.json'

expect_allow 'Read ~/.claude/channels/feishu' \
  run_file_hook "$TEST_HOME/.claude/channels/feishu/access.json"

expect_allow 'Read ~/.claude/plugins（插件缓存）' \
  run_file_hook "$TEST_HOME/.claude/plugins/cache/g-feishu/skills/im/SKILL.md"

expect_allow 'Read */.claude/skills（用户级 skill）' \
  run_file_hook "$TEST_HOME/.claude/skills/my-skill/SKILL.md"

expect_allow 'Read */.claude/commands（用户级命令）' \
  run_file_hook "$TEST_HOME/.claude/commands/deploy.md"

expect_allow 'Read */.claude/agents（任意位置）' \
  run_file_hook "/some/project/.claude/agents/reviewer.md"

expect_block 'Read /usr/local' \
  run_file_hook '/usr/local/bin/node'

expect_block 'Read ~/.npm' \
  run_file_hook "$TEST_HOME/.npm/cache/foo"

expect_block 'Read ~/.cargo' \
  run_file_hook "$TEST_HOME/.cargo/config.toml"

expect_block 'Read ~/.ssh' \
  run_file_hook "$TEST_HOME/.ssh/id_rsa"

expect_block 'Read ~/.gitconfig' \
  run_file_hook "$TEST_HOME/.gitconfig"

echo ""

# ══════════════════════════════════════════════════════════════════════════
echo -e "${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║               DEV profile 行为测试                   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
# ══════════════════════════════════════════════════════════════════════════

switch_profile dev

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 新增：Git 完整操作 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'git commit' \
  run_bash_hook 'git commit -m "feat: add feature"'

expect_allow 'git push' \
  run_bash_hook 'git push origin main'

expect_allow 'git checkout -b' \
  run_bash_hook 'git checkout -b feature/new'

expect_allow 'git merge' \
  run_bash_hook 'git merge develop'

expect_allow 'git rebase' \
  run_bash_hook 'git rebase main'

expect_allow 'git stash' \
  run_bash_hook 'git stash pop'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 新增：文件操作 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'mkdir' \
  run_bash_hook "mkdir -p $TEST_CWD/src/components"

expect_allow 'cp' \
  run_bash_hook "cp $TEST_CWD/a.ts $TEST_CWD/b.ts"

expect_allow 'mv' \
  run_bash_hook "mv $TEST_CWD/old.ts $TEST_CWD/new.ts"

expect_allow 'rm（cwd 内）' \
  run_bash_hook "rm $TEST_CWD/temp.ts"

expect_allow 'touch' \
  run_bash_hook "touch $TEST_CWD/new-file.ts"

expect_allow 'chmod' \
  run_bash_hook "chmod +x $TEST_CWD/script.sh"

expect_allow 'tar（cwd 内）' \
  run_bash_hook "tar czf $TEST_CWD/dist.tar.gz $TEST_CWD/dist"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 新增：前端工具 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'npm install' \
  run_bash_hook 'npm install'

expect_allow 'npm run build' \
  run_bash_hook 'npm run build'

expect_allow 'npx create' \
  run_bash_hook 'npx tsc --init'

expect_allow 'bun install' \
  run_bash_hook 'bun install'

expect_allow 'bunx' \
  run_bash_hook 'bunx --bun vite'

expect_allow 'pnpm add' \
  run_bash_hook 'pnpm add express'

expect_allow 'yarn build' \
  run_bash_hook 'yarn build'

expect_allow 'tsc' \
  run_bash_hook 'tsc --noEmit'

expect_allow 'eslint' \
  run_bash_hook "eslint $TEST_CWD/src"

expect_allow 'prettier' \
  run_bash_hook "prettier --write $TEST_CWD/src"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 新增：后端工具 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'pip install' \
  run_bash_hook 'pip install requests'

expect_allow 'cargo build' \
  run_bash_hook 'cargo build --release'

expect_allow 'go build' \
  run_bash_hook 'go build ./...'

expect_allow 'mvn package' \
  run_bash_hook 'mvn package -DskipTests'

expect_allow 'gradle build' \
  run_bash_hook 'gradle build'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 新增：iOS 工具 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'xcodebuild' \
  run_bash_hook 'xcodebuild -scheme MyApp -configuration Debug build'

expect_allow 'xcrun simctl' \
  run_bash_hook 'xcrun simctl list devices'

expect_allow 'swift build' \
  run_bash_hook 'swift build'

expect_allow 'pod install' \
  run_bash_hook 'pod install'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 新增：Android 工具 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'adb devices' \
  run_bash_hook 'adb devices'

expect_allow './gradlew assembleDebug' \
  run_bash_hook './gradlew assembleDebug'

expect_allow 'sdkmanager --list' \
  run_bash_hook 'sdkmanager --list'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 新增：构建 & 运行时 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'make build' \
  run_bash_hook 'make build'

expect_allow 'cmake' \
  run_bash_hook 'cmake -B build'

expect_allow 'node script.js' \
  run_bash_hook "node $TEST_CWD/server.js"

expect_allow 'python3 script.py' \
  run_bash_hook "python3 $TEST_CWD/app.py"

expect_allow 'deno run' \
  run_bash_hook "deno run $TEST_CWD/main.ts"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 新增：网络 & 工具 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'curl' \
  run_bash_hook 'curl -s https://api.example.com/health'

expect_allow 'wget' \
  run_bash_hook 'wget -q https://example.com/file.tar.gz'

expect_allow 'docker ps' \
  run_bash_hook 'docker ps'

expect_allow 'gh pr list' \
  run_bash_hook 'gh pr list'

expect_allow 'kill' \
  run_bash_hook 'kill 12345'

expect_allow 'lsof -i' \
  run_bash_hook 'lsof -i :3000'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 扩展路径白名单 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'Read ~/.claude/plugins（dev 也放行）' \
  run_file_hook "$TEST_HOME/.claude/plugins/cache/g-feishu/scripts/helper.py"

expect_allow 'Read */.claude/skills（dev 也放行）' \
  run_file_hook "$TEST_HOME/.claude/skills/my-skill/SKILL.md"

expect_allow 'Read /usr/local' \
  run_file_hook '/usr/local/bin/node'

expect_allow 'Read ~/.npm' \
  run_file_hook "$TEST_HOME/.npm/cache/package.json"

expect_allow 'Read ~/.bun' \
  run_file_hook "$TEST_HOME/.bun/install/cache/foo"

expect_allow 'Read ~/.cargo' \
  run_file_hook "$TEST_HOME/.cargo/config.toml"

expect_allow 'Read ~/.ssh' \
  run_file_hook "$TEST_HOME/.ssh/config"

expect_allow 'Read ~/.gitconfig' \
  run_file_hook "$TEST_HOME/.gitconfig"

expect_allow 'Read ~/.pnpm-store' \
  run_file_hook "$TEST_HOME/.pnpm-store/v3/files/foo"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 仍然阻止的路径 ──${NC}"
# ---------------------------------------------------------------------------

expect_block 'Read ~/Downloads（dev 也不允许）' \
  run_file_hook "$TEST_HOME/Downloads/secret.pdf"

expect_block 'Read ~/Documents' \
  run_file_hook "$TEST_HOME/Documents/private.docx"

expect_block 'Read /etc/passwd' \
  run_file_hook '/etc/passwd'

expect_block 'Read ~/Desktop' \
  run_file_hook "$TEST_HOME/Desktop/notes.txt"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 安全机制仍生效 ──${NC}"
# ---------------------------------------------------------------------------

expect_block '$(cmd) 仍被阻止' \
  run_bash_hook 'echo $(cat /etc/passwd)'

expect_block 'echo | sh 仍被阻止' \
  run_bash_hook 'echo "payload" | sh'

expect_block '/tmpevil 边界仍有效' \
  run_bash_hook 'cat /tmpevil/secret.txt'

expect_block 'rm ~/Downloads（路径检查仍生效）' \
  run_bash_hook 'rm ~/Downloads/file.txt'

expect_block 'curl -o 受限路径（命令允许但路径阻止）' \
  run_bash_hook 'curl -o ~/Downloads/data.json https://example.com/api'

expect_allow 'python3 -c（dev 全开 python3）' \
  run_bash_hook 'python3 -c "print(1)"'

expect_allow 'node -e（dev 全开 node）' \
  run_bash_hook 'node -e "console.log(1)"'

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── dev 插件/skill 脚本执行 ──${NC}"
# ---------------------------------------------------------------------------

expect_allow 'dev: python3 插件脚本' \
  run_bash_hook "python3 $TEST_HOME/.claude/plugins/cache/g-feishu/scripts/helper.py"

expect_allow 'dev: python3 cwd 内脚本（dev 全开 python3）' \
  run_bash_hook "python3 $TEST_CWD/scripts/analyze.py"

expect_allow 'dev: node cwd 内脚本' \
  run_bash_hook "node $TEST_CWD/scripts/build.js"

expect_allow 'dev: python3 skill 脚本带参数' \
  run_bash_hook "python3 /workspace/.claude/skills/tool/scripts/run.py --verbose --output /tmp/out.json"

expect_block 'dev: python3 ~/Documents（路径仍受限）' \
  run_bash_hook "python3 ~/Documents/evil.py"

echo ""

# ---------------------------------------------------------------------------
echo -e "${YELLOW}── 配置缺失安全降级 ──${NC}"
# ---------------------------------------------------------------------------

# 临时移除配置测试 fail-closed
mv "$CONF_DIR/sandbox-bash.conf" "$CONF_DIR/sandbox-bash.conf.bak"
expect_block 'bash conf 缺失 → 阻止所有命令' \
  run_bash_hook 'echo hello'
mv "$CONF_DIR/sandbox-bash.conf.bak" "$CONF_DIR/sandbox-bash.conf"

mv "$CONF_DIR/sandbox.conf" "$CONF_DIR/sandbox.conf.bak"
expect_block 'file conf 缺失 → 阻止所有文件操作' \
  run_file_hook "$TEST_CWD/README.md"
mv "$CONF_DIR/sandbox.conf.bak" "$CONF_DIR/sandbox.conf"

echo ""

# ==========================================================================
# 清理
# ==========================================================================
rm -rf "$TEST_HOME"

# 汇总
echo "═══════════════════════════════════"
echo -e "  通过: ${GREEN}$PASS${NC}    失败: ${RED}$FAIL${NC}"
echo "═══════════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
