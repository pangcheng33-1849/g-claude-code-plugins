#!/usr/bin/env bash
# Automated tests for sandbox_profile.py
# Run from project root: bash plugins/feishu-channel-sandbox/tests/test-sandbox-profile.sh

set -euo pipefail

SCRIPT="plugins/feishu-channel-sandbox/skills/sandbox-profile/scripts/sandbox_profile.py"
SETTINGS=".claude/settings.local.json"
ACTIVE="$HOME/.claude/channels/feishu/sandbox-profile/active"
PASS=0
FAIL=0

assert_eq() {
  local desc="$1" expected="$2" actual="$3"
  if [[ "$expected" == "$actual" ]]; then
    echo "  PASS: $desc"
    ((PASS++)) || true
  else
    echo "  FAIL: $desc"
    echo "    expected: $expected"
    echo "    actual:   $actual"
    ((FAIL++)) || true
  fi
}

assert_contains() {
  local desc="$1" needle="$2" haystack="$3"
  if echo "$haystack" | grep -q "$needle" 2>/dev/null; then
    echo "  PASS: $desc"
    ((PASS++)) || true
  else
    echo "  FAIL: $desc"
    echo "    expected to contain: $needle"
    echo "    actual: $haystack"
    ((FAIL++)) || true
  fi
}

assert_exit() {
  local desc="$1" expected_code="$2"
  shift 2
  set +e
  "$@" > /dev/null 2>&1
  local code=$?
  set -e
  assert_eq "$desc" "$expected_code" "$code"
}

jq_val() {
  python3 -c "import sys,json; d=json.load(sys.stdin); print($1)"
}

read_setting() {
  python3 -c "
import json,pathlib
s=json.loads(pathlib.Path('$SETTINGS').read_text()) if pathlib.Path('$SETTINGS').exists() else {}
$1
"
}

# ── Setup ──
echo "=== Setup: reset ==="
python3 "$SCRIPT" reset > /dev/null 2>&1 || true
# Remove any leftover settings.local.json from previous test runs
rm -f "$SETTINGS"

# ── 1. list: no active profile ──
echo "=== 1. list (no active) ==="
OUT=$(python3 "$SCRIPT" list)
assert_eq "active is null" "None" "$(echo "$OUT" | jq_val 'd["active_profile"]')"
assert_eq "has default" "True" "$(echo "$OUT" | jq_val '"default" in [p["name"] for p in d["profiles"]]')"
assert_eq "has dev" "True" "$(echo "$OUT" | jq_val '"dev" in [p["name"] for p in d["profiles"]]')"
assert_eq "has dangerously-open" "True" "$(echo "$OUT" | jq_val '"dangerously-open" in [p["name"] for p in d["profiles"]]')"

# ── 2. show: no args = current config ──
echo "=== 2. show (current, empty) ==="
OUT=$(python3 "$SCRIPT" show)
assert_eq "active is null" "None" "$(echo "$OUT" | jq_val 'd["active_profile"]')"
assert_eq "sandbox is None" "None" "$(echo "$OUT" | jq_val 'd["sandbox"]')"

# ── 3. show preset templates ──
echo "=== 3. show preset templates ==="
assert_eq "default enabled" "True" "$(python3 "$SCRIPT" show default | jq_val 'd["config"]["sandbox"]["enabled"]')"
assert_eq "dev enabled" "True" "$(python3 "$SCRIPT" show dev | jq_val 'd["config"]["sandbox"]["enabled"]')"
assert_eq "dangerously-open disabled" "False" "$(python3 "$SCRIPT" show dangerously-open | jq_val 'd["config"]["sandbox"]["enabled"]')"

# ── 4. show nonexistent ──
echo "=== 4. show nonexistent ==="
assert_exit "nonexistent exits 1" 1 python3 "$SCRIPT" show nonexistent

# ── 5. apply default ──
echo "=== 5. apply default ==="
python3 "$SCRIPT" apply default > /dev/null
assert_eq "active file has absolute path" "1" "$(grep -c '^/' "$ACTIVE" 2>/dev/null || echo 0)"
read_setting "
a=s.get('permissions',{}).get('allow',[])
d=s.get('permissions',{}).get('deny',[])
sb=s.get('sandbox',{})
assert 'Bash(cat *)' in a, 'cat not in allow'
assert 'Bash(curl *)' not in a, 'curl should not be in allow'
assert 'Bash(git push *)' in d, 'git push not in deny'
assert sb.get('allowUnsandboxedCommands') == False, 'escape should be False'
assert sb.get('enabled') == True, 'sandbox should be enabled'
print('all assertions passed')
"
LAST=$?; [[ $LAST -eq 0 ]] && { echo "  PASS: default rules correct"; ((PASS++)); } || { echo "  FAIL: default rules"; ((FAIL++)); }

# ── 6. list shows default active ──
echo "=== 6. list shows active ==="
assert_eq "active is default" "default" "$(python3 "$SCRIPT" list | jq_val 'd["active_profile"]')"

# ── 7. switch default → dev ──
echo "=== 7. switch default → dev ==="
OUT=$(python3 "$SCRIPT" apply dev)
assert_eq "prev is default" "default" "$(echo "$OUT" | jq_val 'd["previous_profile"]')"
read_setting "
a=s.get('permissions',{}).get('allow',[])
d=s.get('permissions',{}).get('deny',[])
sb=s.get('sandbox',{})
assert 'Bash(curl *)' in a, 'curl not in allow'
assert 'Bash(cat *)' not in a, 'cat should be removed'
assert 'Bash(git push *)' not in d, 'git push deny should be removed'
assert sb.get('allowUnsandboxedCommands') == True, 'escape should be True'
print('all assertions passed')
"
LAST=$?; [[ $LAST -eq 0 ]] && { echo "  PASS: dev rules correct, default rules removed"; ((PASS++)); } || { echo "  FAIL: dev switch"; ((FAIL++)); }

# ── 8. switch dev → dangerously-open ──
echo "=== 8. switch dev → dangerously-open ==="
python3 "$SCRIPT" apply dangerously-open > /dev/null
read_setting "
sb=s.get('sandbox',{})
pm=s.get('permissions',{})
a=pm.get('allow',[])
assert sb.get('enabled') == False, 'sandbox should be disabled'
assert pm.get('defaultMode') == 'bypassPermissions', 'mode should be bypass'
assert 'Bash(curl *)' not in a, 'dev curl rule should be removed'
assert 'Bash(git *)' not in a, 'dev git rule should be removed'
print('all assertions passed')
"
LAST=$?; [[ $LAST -eq 0 ]] && { echo "  PASS: dangerously-open correct, dev rules removed"; ((PASS++)); } || { echo "  FAIL: dangerously-open"; ((FAIL++)); }

# ── 9. reset from dangerously-open ──
echo "=== 9. reset ==="
python3 "$SCRIPT" reset > /dev/null
read_setting "
assert s.get('sandbox') is None, 'sandbox should be gone'
assert s.get('permissions') is None, 'permissions should be gone'
print('all assertions passed')
"
LAST=$?; [[ $LAST -eq 0 ]] && { echo "  PASS: reset clean"; ((PASS++)); } || { echo "  FAIL: reset"; ((FAIL++)); }
assert_eq "active file removed" "false" "$([ -f "$ACTIVE" ] && echo true || echo false)"

# ── 10. create custom profile ──
echo "=== 10. create custom profile ==="
OUT=$(python3 "$SCRIPT" create mytest dev)
CUSTOM_PATH=$(echo "$OUT" | jq_val 'd["path"]')
assert_contains "stored in home dir" ".claude/channels/feishu" "$CUSTOM_PATH"
assert_eq "custom file exists" "true" "$([ -f "$CUSTOM_PATH" ] && echo true || echo false)"

# ── 11. list includes custom ──
echo "=== 11. list includes custom ==="
assert_eq "mytest in list" "True" "$(python3 "$SCRIPT" list | jq_val '"mytest" in [p["name"] for p in d["profiles"]]')"

# ── 12. apply custom ──
echo "=== 12. apply custom ==="
python3 "$SCRIPT" apply mytest > /dev/null
assert_eq "active is mytest" "mytest" "$(python3 "$SCRIPT" list | jq_val 'd["active_profile"]')"

# ── 13. delete preset fails ──
echo "=== 13. delete preset fails ==="
assert_exit "delete default fails" 1 python3 "$SCRIPT" delete default
assert_exit "delete dev fails" 1 python3 "$SCRIPT" delete dev
assert_exit "delete dangerously-open fails" 1 python3 "$SCRIPT" delete dangerously-open

# ── 14. delete custom ──
echo "=== 14. delete custom ==="
python3 "$SCRIPT" reset > /dev/null
OUT=$(python3 "$SCRIPT" delete mytest)
assert_contains "deleted message" "deleted" "$OUT"
assert_eq "custom file gone" "false" "$([ -f "$CUSTOM_PATH" ] && echo true || echo false)"

# ── 15. list no custom ──
echo "=== 15. list (custom gone) ==="
PROFILES=$(python3 "$SCRIPT" list | jq_val '[p["name"] for p in d["profiles"]]')
assert_eq "only 3 presets" "['dangerously-open', 'default', 'dev']" "$PROFILES"

# ── 16. user rules preserved across switch ──
echo "=== 16. user rules preserved ==="
python3 "$SCRIPT" apply default > /dev/null
# Manually add a user rule
python3 -c "
import json,pathlib
p=pathlib.Path('$SETTINGS')
s=json.loads(p.read_text())
s['permissions']['allow'].append('Bash(my-custom-tool *)')
p.write_text(json.dumps(s,indent=2))
"
python3 "$SCRIPT" apply dev > /dev/null
read_setting "
a=s.get('permissions',{}).get('allow',[])
assert 'Bash(my-custom-tool *)' in a, 'user rule should survive switch'
assert 'Bash(curl *)' in a, 'dev rule should be added'
assert 'Bash(cat *)' not in a, 'default rule should be removed'
print('all assertions passed')
"
LAST=$?; [[ $LAST -eq 0 ]] && { echo "  PASS: user rules preserved"; ((PASS++)); } || { echo "  FAIL: user rules"; ((FAIL++)); }

# ── Cleanup ──
python3 "$SCRIPT" reset > /dev/null 2>&1 || true

echo ""
echo "========================================="
echo "Results: $PASS passed, $FAIL failed"
echo "========================================="
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
