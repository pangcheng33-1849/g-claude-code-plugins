---
name: feishu-channel-sandbox-profile
description: 切换飞书沙盒配置集（default/dev）。当用户要求"切换沙盒配置""sandbox profile""沙盒改成开发模式""恢复只读模式"时使用。
user-invocable: true
allowed-tools:
  - Read
  - Write
---

# /feishu-channel-sandbox-profile — 沙盒配置集切换

切换 feishu-channel-sandbox 的命令和路径白名单配置。

传入参数：`$ARGUMENTS`

---

## 根据参数分派

### 无参数 — 查看当前配置集

1. 读取 `~/.claude/channels/feishu/sandbox-bash.conf`
2. 检查文件第一行注释：
   - 包含 `DEV profile` → 当前为 **dev**
   - 包含 `DEFAULT profile` 或其他 → 当前为 **default**
   - 文件不存在 → 未初始化
3. 输出当前配置集和可用选项：

```
当前沙盒配置集：default（只读模式）

可用配置集：
  default — 只读命令（ls, cat, grep, git status 等），安全最严格
  dev     — 完整开发命令（git, npm, make, xcodebuild, adb 等），仍受路径白名单约束

切换：/feishu-channel-sandbox-profile dev
```

### `dev` — 切换到开发配置

用 Write 工具将以下内容写入两个文件。**先写 sandbox.conf（路径白名单），再写 sandbox-bash.conf（命令白名单）**，因为命令白名单依赖路径白名单。

**写入 `~/.claude/channels/feishu/sandbox.conf`：**

```
# feishu-channel-sandbox: DEV profile — allowed file paths
# Lines starting with # are comments. Paths are prefix-matched after canonicalization.
# Claude's working directory (cwd) is always allowed automatically.
# Switch profiles: /feishu-channel-sandbox-profile default

# Feishu channel state
~/.claude/channels/feishu

# Temp files
/tmp

# ── Dev paths ──

# Homebrew / system tools
/usr/local

# Package manager caches
~/.npm
~/.bun
~/.cargo
~/.pnpm-store

# Git config
~/.gitconfig
~/.gitignore_global
~/.ssh
```

**写入 `~/.claude/channels/feishu/sandbox-bash.conf`：**

```
# feishu-channel-sandbox: DEV profile — allowed bash command prefixes
# Full development commands. All commands are still constrained by sandbox.conf path whitelist.
# Switch profiles: /feishu-channel-sandbox-profile default

# ── Common safe commands ──
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
ps
top -l 1

# ── Git (full access) ──
git

# ── File operations ──
mkdir
cp
mv
rm
touch
chmod
chown
ln
tar
zip
unzip
gzip
gunzip
xz

# ── Frontend ──
npm
npx
bun
bunx
pnpm
yarn
vite
webpack
tsc
eslint
prettier
sass
postcss
tailwind

# ── Backend ──
pip
pip3
cargo
go
mvn
gradle
dotnet
composer
gem
bundle

# ── iOS ──
xcodebuild
xcrun
xcode-select
swift
swiftc
pod
xctool
simctl
codesign
plutil
xcpretty

# ── Android ──
adb
fastboot
sdkmanager
avdmanager
emulator
aapt
apksigner
zipalign
./gradlew

# ── Build tools ──
make
cmake
ninja
bazel

# ── Language runtimes ──
node
python3
python
deno
ruby
java
javac
rustc
kotlin

# ── Network ──
curl
wget

# ── Process management ──
kill
killall
lsof

# ── Dev tools ──
open
code
tee
xargs
env
docker
docker-compose
gh
```

写入后输出：

```
已切换到 dev 配置集（完整开发命令）。

新增命令：git（完整）、npm/bun/yarn/pnpm、make/cmake、xcodebuild/pod、adb/gradle、curl、docker 等
新增路径：/usr/local、~/.npm、~/.bun、~/.cargo、~/.ssh 等

所有命令仍受路径白名单约束，只能操作项目目录和已授权路径。
恢复只读模式：/feishu-channel-sandbox-profile default
```

### `default` — 恢复只读配置

用 Write 工具将以下内容写入两个文件。

**写入 `~/.claude/channels/feishu/sandbox.conf`：**

```
# feishu-channel-sandbox: DEFAULT profile — allowed file paths
# Lines starting with # are comments. Paths are prefix-matched after canonicalization.
# Claude's working directory (cwd) is always allowed automatically.
# Switch profiles: /feishu-channel-sandbox-profile dev

# Feishu channel state
~/.claude/channels/feishu

# Temp files
/tmp
```

**写入 `~/.claude/channels/feishu/sandbox-bash.conf`：**

```
# feishu-channel-sandbox: DEFAULT profile — allowed bash command prefixes
# Read-only commands only. All commands are constrained by sandbox.conf path whitelist.
# Switch profiles: /feishu-channel-sandbox-profile dev

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
```

写入后输出：

```
已恢复 default 配置集（只读模式）。

命令限制为：ls, cat, grep, git status/log/diff 等只读操作
路径限制为：项目目录、~/.claude/channels/feishu、/tmp

切换到开发模式：/feishu-channel-sandbox-profile dev
```

### 其他参数 — 无效

输出错误信息：

```
未知配置集：$ARGUMENTS

可用配置集：default, dev
用法：/feishu-channel-sandbox-profile <配置集名称>
```
