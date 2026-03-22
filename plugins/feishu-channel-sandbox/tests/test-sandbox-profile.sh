#!/usr/bin/env bash
# Automated tests for sandbox_profile.py
# Run from repo root: bash plugins/feishu-channel-sandbox/tests/test-sandbox-profile.sh
# Uses temp directories — does NOT modify user settings or HOME.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SCRIPT="$REPO_ROOT/plugins/feishu-channel-sandbox/skills/sandbox-profile/scripts/sandbox_profile.py"

# Create isolated test environment
TEST_DIR=$(mktemp -d)
TEST_HOME=$(mktemp -d)
mkdir -p "$TEST_DIR/.claude"

export HOME="$TEST_HOME"
cd "$TEST_DIR"

SETTINGS=".claude/settings.local.json"
ACTIVE="$TEST_HOME/.claude/channels/feishu/sandbox-profile/active"
PASS=0
FAIL=0

# Snapshots
SNAPSHOTS="$REPO_ROOT/plugins/feishu-channel-sandbox/tests/snapshots"
rm -rf "$SNAPSHOTS"
mkdir -p "$SNAPSHOTS"

snapshot() {
  local dir="$SNAPSHOTS/$1"
  mkdir -p "$dir"
  cp "$SETTINGS" "$dir/settings.local.json" 2>/dev/null || echo '(not exists)' > "$dir/settings.local.json"
  cp "$ACTIVE" "$dir/active" 2>/dev/null || echo '(not set)' > "$dir/active"
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

assert_contains() {
  local desc="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -q "$needle" 2>/dev/null; then
    echo "  PASS: $desc"; ((PASS++)) || true
  else
    echo "  FAIL: $desc"; echo "    needle: $needle"; echo "    haystack: $haystack"; ((FAIL++)) || true
  fi
}

assert_exit() {
  local desc="$1" expected_code="$2"; shift 2
  set +e; "$@" > /dev/null 2>&1; local code=$?; set -e
  assert_eq "$desc" "$expected_code" "$code"
}

jv() { python3 -c "import sys,json; d=json.load(sys.stdin); print($1)"; }

read_setting() {
  python3 -c "
import json,pathlib
s=json.loads(pathlib.Path('$SETTINGS').read_text()) if pathlib.Path('$SETTINGS').exists() else {}
$1
"
}

# ═══════════════════════════════════════════════════════
# Setup: simulate realistic user settings.local.json
# ═══════════════════════════════════════════════════════

FIXTURES="$REPO_ROOT/plugins/feishu-channel-sandbox/tests/fixtures"

echo "=== 0. Setup: write initial user config ==="
mkdir -p .claude
cp "$FIXTURES/initial-user-settings.json" "$SETTINGS"
snapshot "00-initial-user-config"

# ═══════════════════════════════════════════════════════
# 1-4. Basic list/show
# ═══════════════════════════════════════════════════════

echo "=== 1. list (no active profile) ==="
OUT=$(python3 "$SCRIPT" list)
assert_eq "active is null" "None" "$(echo "$OUT" | jv 'd["active_profile"]')"
assert_eq "has 3 presets" "True" "$(echo "$OUT" | jv 'all(n in [p["name"] for p in d["profiles"]] for n in ["default","dev","dangerously-open"])')"
# Verify user config visible
assert_eq "user allow visible" "True" "$(echo "$OUT" | jv '"Bash(gh repo:*)" in (d.get("current_permissions_allow") or [])')"

echo "=== 2. show (current config with user data) ==="
OUT=$(python3 "$SCRIPT" show)
assert_eq "defaultMode preserved" "default" "$(echo "$OUT" | jv 'd["permissions"]["defaultMode"]')"

echo "=== 3. show presets ==="
assert_eq "default enabled" "True" "$(python3 "$SCRIPT" show default | jv 'd["config"]["sandbox"]["enabled"]')"
assert_eq "dev enabled" "True" "$(python3 "$SCRIPT" show dev | jv 'd["config"]["sandbox"]["enabled"]')"
assert_eq "open disabled" "False" "$(python3 "$SCRIPT" show dangerously-open | jv 'd["config"]["sandbox"]["enabled"]')"

echo "=== 4. show nonexistent ==="
assert_exit "exits 1" 1 python3 "$SCRIPT" show nonexistent

# ═══════════════════════════════════════════════════════
# 5-6. Apply default — user config preserved
# ═══════════════════════════════════════════════════════

echo "=== 5. apply default ==="
python3 "$SCRIPT" apply default > /dev/null
snapshot "05-apply-default"
read_setting "
a = s.get('permissions',{}).get('allow',[])
d = s.get('permissions',{}).get('deny',[])
# Profile rules added
assert 'Bash(cat *)' in a, 'default cat missing'
assert 'Bash(git push *)' in d, 'default deny missing'
# User rules preserved
assert 'Bash(gh repo:*)' in a, 'user gh rule lost'
assert 'WebFetch(domain:www.npmjs.com)' in a, 'user webfetch lost'
# User non-permission config preserved
assert s.get('enabledPlugins',{}).get('skill-creator@claude-plugins-official') == True, 'enabledPlugins lost'
assert s.get('effortLevel') == 'high', 'effortLevel lost'
assert s.get('permissions',{}).get('defaultMode') == 'default', 'defaultMode changed'
# Sandbox applied
assert s['sandbox']['enabled'] == True, 'sandbox not enabled'
assert s['sandbox']['allowUnsandboxedCommands'] == False, 'escape not false'
print('all assertions passed')
"
LAST=$?; [[ $LAST -eq 0 ]] && { echo "  PASS: default applied, user config preserved"; ((PASS++)); } || { echo "  FAIL: apply default"; ((FAIL++)); }

echo "=== 6. list shows active ==="
assert_eq "active" "default" "$(python3 "$SCRIPT" list | jv 'd["active_profile"]')"

# ═══════════════════════════════════════════════════════
# 7. User manually adds config between profiles
# ═══════════════════════════════════════════════════════

echo "=== 7. user adds manual config ==="
python3 -c "
import json,pathlib
p=pathlib.Path('$SETTINGS'); s=json.loads(p.read_text())
s['permissions']['allow'].append('Bash(my-deploy-script *)')
s['permissions']['deny'].append('Bash(rm -rf /home/*)')
s['myCustomKey'] = 'should-survive'
p.write_text(json.dumps(s,indent=2))
"
snapshot "07-user-manual-adds"

# ═══════════════════════════════════════════════════════
# 8. Switch default → dev — user manual rules survive
# ═══════════════════════════════════════════════════════

echo "=== 8. switch default → dev ==="
python3 "$SCRIPT" apply dev > /dev/null
snapshot "08-switch-to-dev"
read_setting "
a = s.get('permissions',{}).get('allow',[])
d = s.get('permissions',{}).get('deny',[])
# Dev rules present
assert 'Bash(curl *)' in a, 'dev curl missing'
assert 'Bash(npm *)' in a, 'dev npm missing'
# Default rules removed
assert 'Bash(cat *)' not in a, 'default cat should be gone'
assert 'Bash(git push *)' not in d, 'default git push deny should be gone'
# User original rules survive
assert 'Bash(gh repo:*)' in a, 'user gh rule lost'
assert 'WebFetch(domain:www.npmjs.com)' in a, 'user webfetch lost'
# User manual rules survive
assert 'Bash(my-deploy-script *)' in a, 'user deploy rule lost'
assert 'Bash(rm -rf /home/*)' in d, 'user rm deny lost'
# User non-permission config survives
assert s.get('myCustomKey') == 'should-survive', 'myCustomKey lost'
assert s.get('enabledPlugins',{}).get('skill-creator@claude-plugins-official') == True, 'enabledPlugins lost'
assert s.get('effortLevel') == 'high', 'effortLevel lost'
print('all assertions passed')
"
LAST=$?; [[ $LAST -eq 0 ]] && { echo "  PASS: dev applied, all user config preserved"; ((PASS++)); } || { echo "  FAIL: switch to dev"; ((FAIL++)); }

# ═══════════════════════════════════════════════════════
# 9. Switch dev → dangerously-open
# ═══════════════════════════════════════════════════════

echo "=== 9. switch dev → dangerously-open ==="
python3 "$SCRIPT" apply dangerously-open > /dev/null
snapshot "09-switch-to-dangerously-open"
read_setting "
sb = s.get('sandbox',{})
pm = s.get('permissions',{})
a = pm.get('allow',[])
d = pm.get('deny',[])
assert sb.get('enabled') == False, 'sandbox should be off'
assert pm.get('defaultMode') == 'bypassPermissions', 'mode should be bypass'
# Dev rules removed
assert 'Bash(curl *)' not in a, 'dev curl should be gone'
# User rules survive
assert 'Bash(gh repo:*)' in a, 'user gh lost'
assert 'Bash(my-deploy-script *)' in a, 'user deploy lost'
assert 'Bash(rm -rf /home/*)' in d, 'user rm deny lost'
assert s.get('myCustomKey') == 'should-survive', 'myCustomKey lost'
print('all assertions passed')
"
LAST=$?; [[ $LAST -eq 0 ]] && { echo "  PASS: dangerously-open, user rules survive"; ((PASS++)); } || { echo "  FAIL: dangerously-open"; ((FAIL++)); }

# ═══════════════════════════════════════════════════════
# 10. Reset — restore to initial user state
# ═══════════════════════════════════════════════════════

echo "=== 10. reset ==="
python3 "$SCRIPT" reset > /dev/null
snapshot "10-reset"
read_setting "
# Sandbox gone
assert s.get('sandbox') is None, 'sandbox should be gone'
# Profile permissions gone (defaultMode removed because dangerously-open set it)
# But user's original defaultMode was 'default' — it was overwritten by dangerously-open
# User manual rules should survive
pm = s.get('permissions',{})
a = pm.get('allow',[])
d = pm.get('deny',[])
assert 'Bash(gh repo:*)' in a, 'user gh lost after reset'
assert 'WebFetch(domain:www.npmjs.com)' in a, 'user webfetch lost after reset'
assert 'Bash(my-deploy-script *)' in a, 'user deploy lost after reset'
assert 'Bash(rm -rf /home/*)' in d, 'user rm deny lost after reset'
# Non-permission config preserved
assert s.get('enabledPlugins',{}).get('skill-creator@claude-plugins-official') == True, 'enabledPlugins lost'
assert s.get('effortLevel') == 'high', 'effortLevel lost'
assert s.get('myCustomKey') == 'should-survive', 'myCustomKey lost'
print('all assertions passed')
"
LAST=$?; [[ $LAST -eq 0 ]] && { echo "  PASS: reset preserves user config"; ((PASS++)); } || { echo "  FAIL: reset"; ((FAIL++)); }
assert_eq "active file removed" "false" "$([ -f "$ACTIVE" ] && echo true || echo false)"

# ═══════════════════════════════════════════════════════
# 11-14. Custom profile CRUD
# ═══════════════════════════════════════════════════════

echo "=== 11. create custom profile ==="
OUT=$(python3 "$SCRIPT" create mytest dev)
CUSTOM_PATH=$(echo "$OUT" | jv 'd["path"]')
assert_contains "in home dir" ".claude/channels/feishu" "$CUSTOM_PATH"
assert_eq "file exists" "true" "$([ -f "$CUSTOM_PATH" ] && echo true || echo false)"

echo "=== 12. list includes custom ==="
assert_eq "mytest in list" "True" "$(python3 "$SCRIPT" list | jv '"mytest" in [p["name"] for p in d["profiles"]]')"

echo "=== 13. apply custom ==="
python3 "$SCRIPT" apply mytest > /dev/null
snapshot "13-apply-custom"
assert_eq "active is mytest" "mytest" "$(python3 "$SCRIPT" list | jv 'd["active_profile"]')"

echo "=== 14. delete preset fails ==="
assert_exit "delete default" 1 python3 "$SCRIPT" delete default
assert_exit "delete dev" 1 python3 "$SCRIPT" delete dev
assert_exit "delete dangerously-open" 1 python3 "$SCRIPT" delete dangerously-open

echo "=== 15. delete custom ==="
python3 "$SCRIPT" reset > /dev/null
OUT=$(python3 "$SCRIPT" delete mytest)
assert_contains "deleted" "deleted" "$OUT"
assert_eq "file gone" "false" "$([ -f "$CUSTOM_PATH" ] && echo true || echo false)"

echo "=== 16. list (custom gone) ==="
assert_eq "3 presets" "['dangerously-open', 'default', 'dev']" "$(python3 "$SCRIPT" list | jv '[p["name"] for p in d["profiles"]]')"

# ═══════════════════════════════════════════════════════
# 17. Apply → user adds more → apply another → user adds still there
# ═══════════════════════════════════════════════════════

echo "=== 17. multi-step user interaction ==="
python3 "$SCRIPT" apply default > /dev/null
# User adds a rule while in default
python3 -c "
import json,pathlib
p=pathlib.Path('$SETTINGS'); s=json.loads(p.read_text())
s['permissions']['allow'].append('Bash(terraform *)')
p.write_text(json.dumps(s,indent=2))
"
# Switch to dev
python3 "$SCRIPT" apply dev > /dev/null
# User adds another rule while in dev
python3 -c "
import json,pathlib
p=pathlib.Path('$SETTINGS'); s=json.loads(p.read_text())
s['permissions']['allow'].append('Bash(kubectl *)')
p.write_text(json.dumps(s,indent=2))
"
# Switch back to default
python3 "$SCRIPT" apply default > /dev/null
snapshot "17-multi-step"
read_setting "
a = s.get('permissions',{}).get('allow',[])
# Both user-added rules survive
assert 'Bash(terraform *)' in a, 'terraform lost'
assert 'Bash(kubectl *)' in a, 'kubectl lost'
# Default rules present
assert 'Bash(cat *)' in a, 'default cat missing'
# Dev rules gone
assert 'Bash(curl *)' not in a, 'dev curl should be gone'
# Original user rules survive
assert 'Bash(gh repo:*)' in a, 'original gh lost'
print('all assertions passed')
"
LAST=$?; [[ $LAST -eq 0 ]] && { echo "  PASS: multi-step user rules all preserved"; ((PASS++)); } || { echo "  FAIL: multi-step"; ((FAIL++)); }

# ── Cleanup ──
python3 "$SCRIPT" reset > /dev/null 2>&1 || true

echo ""
echo "========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "========================================="
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
