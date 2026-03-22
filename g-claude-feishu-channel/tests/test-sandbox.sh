#!/usr/bin/env bash
# Automated tests for g-claude-feishu-channel sandbox CLI (Node.js)
# Run from any directory: bash <repo>/g-claude-feishu-channel/tests/test-sandbox.sh
# Uses temp directories — does NOT modify user settings or HOME.

set -euo pipefail

CLI="$(cd "$(dirname "$0")/.." && pwd)/bin/cli.js"
FIXTURES="$(cd "$(dirname "$0")" && pwd)/fixtures"

# Isolated test environment
TEST_DIR=$(mktemp -d)
TEST_HOME=$(mktemp -d)
mkdir -p "$TEST_DIR/.claude"
export HOME="$TEST_HOME"
cd "$TEST_DIR"

SETTINGS=".claude/settings.local.json"
PASS=0
FAIL=0

# Snapshots
SNAPSHOTS="$(cd "$(dirname "$0")" && pwd)/snapshots"
rm -rf "$SNAPSHOTS"
mkdir -p "$SNAPSHOTS"

snapshot() {
  local dir="$SNAPSHOTS/$1"
  mkdir -p "$dir"
  cp "$SETTINGS" "$dir/settings.local.json" 2>/dev/null || echo '(not exists)' > "$dir/settings.local.json"
  # Copy active file if exists
  local active_dir="$TEST_HOME/.claude/channels/feishu/sandbox-profile/active"
  if [ -d "$active_dir" ]; then
    cp -r "$active_dir" "$dir/active_records" 2>/dev/null || true
  else
    echo '(no active records)' > "$dir/active_records"
  fi
}

cleanup() { rm -rf "$TEST_DIR" "$TEST_HOME"; }
trap cleanup EXIT

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "  PASS: $desc"; ((PASS++)) || true
  else
    echo "  FAIL: $desc"; echo "    expected: $expected"; echo "    actual:   $actual"; ((FAIL++)) || true
  fi
}

assert_exit() {
  local desc="$1" expected_code="$2"; shift 2
  set +e; "$@" > /dev/null 2>&1; local code=$?; set -e
  assert_eq "$desc" "$expected_code" "$code"
}

jv() { node -e "const d=JSON.parse(require('fs').readFileSync('/dev/stdin','utf-8')); console.log($1)"; }

read_setting() {
  node -e "
const s = require('fs').existsSync('$SETTINGS') ? JSON.parse(require('fs').readFileSync('$SETTINGS','utf-8')) : {};
$1
"
}

# ═══════════════════════════════════════════════════════
# Setup: realistic initial user config
# ═══════════════════════════════════════════════════════

echo "=== 0. Setup ==="
cp "$FIXTURES/initial-user-settings.json" "$SETTINGS"
snapshot "00-initial"

# ═══════════════════════════════════════════════════════
# 1-4. List / Show
# ═══════════════════════════════════════════════════════

echo "=== 1. list (no active) ==="
OUT=$(node "$CLI" sandbox list)
assert_eq "active null" "null" "$(echo "$OUT" | jv 'd.active_profile')"
assert_eq "has presets" "true" "$(echo "$OUT" | jv '["default","dev","dangerously-open"].every(n=>d.profiles.some(p=>p.name===n))')"
assert_eq "user allow visible" "true" "$(echo "$OUT" | jv '(d.current_permissions_allow||[]).includes("Bash(gh repo:*)")')"

echo "=== 2. show (current) ==="
OUT=$(node "$CLI" sandbox show)
assert_eq "defaultMode" "default" "$(echo "$OUT" | jv 'd.permissions.defaultMode')"

echo "=== 3. show presets ==="
assert_eq "default on" "true" "$(node "$CLI" sandbox show default | jv 'd.config.sandbox.enabled')"
assert_eq "dev on" "true" "$(node "$CLI" sandbox show dev | jv 'd.config.sandbox.enabled')"
assert_eq "open off" "false" "$(node "$CLI" sandbox show dangerously-open | jv 'd.config.sandbox.enabled')"

echo "=== 4. show nonexistent ==="
assert_exit "exits 1" 1 node "$CLI" sandbox show nonexistent

# ═══════════════════════════════════════════════════════
# 5-6. Apply default + verify user config preserved
# ═══════════════════════════════════════════════════════

echo "=== 5. apply default ==="
node "$CLI" sandbox apply default > /dev/null
snapshot "05-apply-default"
read_setting "
const a = (s.permissions||{}).allow||[];
const d = (s.permissions||{}).deny||[];
console.assert(a.includes('Bash(cat *)'), 'default cat missing');
console.assert(!a.includes('Bash(curl *)'), 'curl should not be in allow');
console.assert(d.includes('Bash(git push *)'), 'deny missing');
console.assert(a.includes('Bash(gh repo:*)'), 'user gh rule lost');
console.assert(a.includes('WebFetch(domain:www.npmjs.com)'), 'user webfetch lost');
console.assert(s.enabledPlugins['skill-creator@claude-plugins-official']===true, 'plugins lost');
console.assert(s.effortLevel==='high', 'effortLevel lost');
console.assert(s.permissions.defaultMode==='dontAsk', 'mode should be dontAsk');
console.assert(s.sandbox.enabled===true, 'sandbox not on');
console.assert(s.sandbox.allowUnsandboxedCommands===false, 'escape not off');
console.log('ok');
"
LAST=$?; [[ "$(read_setting 'console.log("ok")')" == "ok" ]] && { echo "  PASS: default + user config preserved"; ((PASS++)) || true; } || { echo "  FAIL: apply default"; ((FAIL++)) || true; }

echo "=== 6. list active ==="
assert_eq "active" "default" "$(node "$CLI" sandbox list | jv 'd.active_profile')"

# ═══════════════════════════════════════════════════════
# 7. User manually adds config
# ═══════════════════════════════════════════════════════

echo "=== 7. user adds manual config ==="
node -e "
const fs=require('fs');
const s=JSON.parse(fs.readFileSync('$SETTINGS','utf-8'));
s.permissions.allow.push('Bash(my-deploy-script *)');
s.permissions.deny.push('Bash(rm -rf /home/*)');
s.myCustomKey='should-survive';
fs.writeFileSync('$SETTINGS',JSON.stringify(s,null,2));
"
snapshot "07-user-manual"

# ═══════════════════════════════════════════════════════
# 8. Switch default → dev
# ═══════════════════════════════════════════════════════

echo "=== 8. switch to dev ==="
OUT=$(node "$CLI" sandbox apply dev)
snapshot "08-switch-dev"
assert_eq "prev" "default" "$(echo "$OUT" | jv 'd.previous_profile')"
read_setting "
const a = (s.permissions||{}).allow||[];
const d = (s.permissions||{}).deny||[];
console.assert(a.includes('Bash(curl *)'), 'dev curl missing');
console.assert(!a.includes('Bash(cat *)'), 'default cat should be gone');
console.assert(!d.includes('Bash(git push *)'), 'default deny should be gone');
console.assert(a.includes('Bash(gh repo:*)'), 'user gh lost');
console.assert(a.includes('Bash(my-deploy-script *)'), 'user deploy lost');
console.assert(d.includes('Bash(rm -rf /home/*)'), 'user rm deny lost');
console.assert(s.myCustomKey==='should-survive', 'custom key lost');
console.log('ok');
"
[[ "$(read_setting 'console.log("ok")')" == "ok" ]] && { echo "  PASS: dev applied, user config preserved"; ((PASS++)) || true; } || { echo "  FAIL: switch dev"; ((FAIL++)) || true; }

# ═══════════════════════════════════════════════════════
# 9. Switch dev → dangerously-open
# ═══════════════════════════════════════════════════════

echo "=== 9. switch to dangerously-open ==="
node "$CLI" sandbox apply dangerously-open > /dev/null
snapshot "09-switch-open"
read_setting "
const a = (s.permissions||{}).allow||[];
console.assert(s.sandbox.enabled===false, 'sandbox should be off');
console.assert(s.permissions.defaultMode==='bypassPermissions', 'mode wrong');
console.assert(!a.includes('Bash(curl *)'), 'dev curl should be gone');
console.assert(a.includes('Bash(gh repo:*)'), 'user gh lost');
console.assert(a.includes('Bash(my-deploy-script *)'), 'user deploy lost');
console.assert(s.myCustomKey==='should-survive', 'custom key lost');
console.log('ok');
"
[[ "$(read_setting 'console.log("ok")')" == "ok" ]] && { echo "  PASS: dangerously-open, user rules survive"; ((PASS++)) || true; } || { echo "  FAIL: dangerously-open"; ((FAIL++)) || true; }

# ═══════════════════════════════════════════════════════
# 10. Reset
# ═══════════════════════════════════════════════════════

echo "=== 10. reset ==="
node "$CLI" sandbox reset > /dev/null
snapshot "10-reset"
read_setting "
const a = (s.permissions||{}).allow||[];
const d = (s.permissions||{}).deny||[];
console.assert(!s.sandbox, 'sandbox should be gone');
console.assert(a.includes('Bash(gh repo:*)'), 'user gh lost');
console.assert(a.includes('Bash(my-deploy-script *)'), 'user deploy lost');
console.assert(d.includes('Bash(rm -rf /home/*)'), 'user rm deny lost');
console.assert(s.myCustomKey==='should-survive', 'custom key lost');
console.assert(s.effortLevel==='high', 'effortLevel lost');
console.log('ok');
"
[[ "$(read_setting 'console.log("ok")')" == "ok" ]] && { echo "  PASS: reset preserves user config"; ((PASS++)) || true; } || { echo "  FAIL: reset"; ((FAIL++)) || true; }

# ═══════════════════════════════════════════════════════
# 11-15. Custom profile CRUD
# ═══════════════════════════════════════════════════════

echo "=== 11. create custom ==="
OUT=$(node "$CLI" sandbox create mytest dev)
CUSTOM_PATH=$(echo "$OUT" | jv 'd.path')
assert_eq "in home dir" "true" "$(echo "$CUSTOM_PATH" | grep -q '.claude/channels/feishu' && echo true || echo false)"
assert_eq "file exists" "true" "$([[ -f "$CUSTOM_PATH" ]] && echo true || echo false)"

echo "=== 12. list includes custom ==="
assert_eq "mytest in list" "true" "$(node "$CLI" sandbox list | jv 'd.profiles.some(p=>p.name==="mytest")')"

echo "=== 13. apply custom ==="
node "$CLI" sandbox apply mytest > /dev/null
snapshot "13-apply-custom"
assert_eq "active" "mytest" "$(node "$CLI" sandbox list | jv 'd.active_profile')"

echo "=== 14. delete preset fails ==="
assert_exit "delete default" 1 node "$CLI" sandbox delete default
assert_exit "delete dev" 1 node "$CLI" sandbox delete dev
assert_exit "delete dangerously-open" 1 node "$CLI" sandbox delete dangerously-open

echo "=== 15. delete custom ==="
node "$CLI" sandbox reset > /dev/null
OUT=$(node "$CLI" sandbox delete mytest)
assert_eq "deleted" "true" "$(echo "$OUT" | jv 'd.message.includes("deleted")')"
assert_eq "file gone" "false" "$([[ -f "$CUSTOM_PATH" ]] && echo true || echo false)"

echo "=== 16. list (custom gone) ==="
assert_eq "3 presets" "3" "$(node "$CLI" sandbox list | jv 'd.profiles.length')"

# ═══════════════════════════════════════════════════════
# 17. Multi-step: user adds rules across switches
# ═══════════════════════════════════════════════════════

echo "=== 17. multi-step user interaction ==="
node "$CLI" sandbox apply default > /dev/null
node -e "const fs=require('fs'); const s=JSON.parse(fs.readFileSync('$SETTINGS','utf-8')); s.permissions.allow.push('Bash(terraform *)'); fs.writeFileSync('$SETTINGS',JSON.stringify(s,null,2));"
node "$CLI" sandbox apply dev > /dev/null
node -e "const fs=require('fs'); const s=JSON.parse(fs.readFileSync('$SETTINGS','utf-8')); s.permissions.allow.push('Bash(kubectl *)'); fs.writeFileSync('$SETTINGS',JSON.stringify(s,null,2));"
node "$CLI" sandbox apply default > /dev/null
snapshot "17-multi-step"
read_setting "
const a = (s.permissions||{}).allow||[];
console.assert(a.includes('Bash(terraform *)'), 'terraform lost');
console.assert(a.includes('Bash(kubectl *)'), 'kubectl lost');
console.assert(a.includes('Bash(cat *)'), 'default cat missing');
console.assert(!a.includes('Bash(curl *)'), 'dev curl should be gone');
console.assert(a.includes('Bash(gh repo:*)'), 'user gh lost');
console.log('ok');
"
[[ "$(read_setting 'console.log("ok")')" == "ok" ]] && { echo "  PASS: multi-step all rules preserved"; ((PASS++)) || true; } || { echo "  FAIL: multi-step"; ((FAIL++)) || true; }

# ═══════════════════════════════════════════════════════
# 18. Multi-project isolation
# ═══════════════════════════════════════════════════════

echo "=== 18. multi-project isolation ==="
node "$CLI" sandbox reset > /dev/null
node "$CLI" sandbox apply default > /dev/null
PROJECT_A="$TEST_DIR"
PROJECT_B=$(mktemp -d)
mkdir -p "$PROJECT_B/.claude"
cd "$PROJECT_B"
node "$CLI" sandbox apply dev > /dev/null
# Reset B should not affect A
node "$CLI" sandbox reset > /dev/null
cd "$PROJECT_A"
assert_eq "A still default" "default" "$(node "$CLI" sandbox list | jv 'd.active_profile')"
read_setting "console.assert(s.sandbox.enabled===true); console.log('ok');"
[[ "$(read_setting 'console.log("ok")')" == "ok" ]] && { echo "  PASS: project A unaffected by B reset"; ((PASS++)) || true; } || { echo "  FAIL: isolation"; ((FAIL++)) || true; }
rm -rf "$PROJECT_B"

# ═══════════════════════════════════════════════════════
# 19. Reset without active record (fallback)
# ═══════════════════════════════════════════════════════

echo "=== 19. reset fallback (no active record) ==="
node "$CLI" sandbox apply default > /dev/null
rm -rf "$TEST_HOME/.claude/channels/feishu/sandbox-profile/active"
node "$CLI" sandbox reset > /dev/null
snapshot "19-reset-fallback"
read_setting "
console.assert(!s.sandbox, 'sandbox should be gone');
console.assert(!(s.permissions||{}).defaultMode, 'defaultMode should be gone');
console.log('ok');
"
[[ "$(read_setting 'console.log("ok")')" == "ok" ]] && { echo "  PASS: fallback reset clean"; ((PASS++)) || true; } || { echo "  FAIL: fallback reset"; ((FAIL++)) || true; }

# ═══════════════════════════════════════════════════════
# 20. Reset force clean (no active, no sandbox match)
# ═══════════════════════════════════════════════════════

echo "=== 20. reset force clean ==="
# Write custom sandbox config that won't match any preset
node -e "
const fs=require('fs');
const s=JSON.parse(fs.readFileSync('$SETTINGS','utf-8'));
s.sandbox={enabled:true,custom:true};
s.permissions={allow:['Bash(mystery *)'],deny:['Bash(secret *)'],defaultMode:'dontAsk'};
fs.writeFileSync('$SETTINGS',JSON.stringify(s,null,2));
"
node "$CLI" sandbox reset > /dev/null
snapshot "20-force-clean"
read_setting "
console.assert(!s.sandbox, 'sandbox should be gone');
console.assert(!(s.permissions||{}).allow, 'allow should be gone');
console.assert(!(s.permissions||{}).deny, 'deny should be gone');
console.assert(!(s.permissions||{}).defaultMode, 'defaultMode should be gone');
console.log('ok');
"
[[ "$(read_setting 'console.log("ok")')" == "ok" ]] && { echo "  PASS: force clean all"; ((PASS++)) || true; } || { echo "  FAIL: force clean"; ((FAIL++)) || true; }

# ── Cleanup ──
node "$CLI" sandbox reset > /dev/null 2>&1 || true

echo ""
echo "========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "========================================="
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
