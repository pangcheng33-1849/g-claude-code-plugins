#!/bin/bash
# =============================================================================
# load-env.sh — SessionStart hook: load ~/.claude/channels/feishu/.env
# =============================================================================
# Reads the feishu channel .env file and exports its variables via
# CLAUDE_ENV_FILE so that all subsequent bash commands (including skill
# scripts like feishu_auth_helper.py) can access the credentials.
# =============================================================================

ENV_FILE="$HOME/.claude/channels/feishu/.env"
LOG_FILE="$HOME/.claude/channels/feishu/logs/load-env.log"

# Debug: log CLAUDE_ENV_FILE path and env file status
mkdir -p "$(dirname "$LOG_FILE")"
{
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%S.000Z')] load-env.sh started"
  echo "  CLAUDE_ENV_FILE=${CLAUDE_ENV_FILE:-<empty>}"
  echo "  ENV_FILE=$ENV_FILE exists=$([ -f "$ENV_FILE" ] && echo yes || echo no)"
} >> "$LOG_FILE" 2>/dev/null

# Guard: skip if CLAUDE_ENV_FILE not available or .env doesn't exist
if [ -z "$CLAUDE_ENV_FILE" ]; then
  echo "  SKIP: CLAUDE_ENV_FILE not set" >> "$LOG_FILE" 2>/dev/null
  exit 0
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "  SKIP: $ENV_FILE not found" >> "$LOG_FILE" 2>/dev/null
  exit 0
fi

# Read .env and write export statements to CLAUDE_ENV_FILE
COUNT=0
while IFS= read -r line; do
  # Skip comments and empty lines
  [[ "$line" =~ ^[[:space:]]*# ]] && continue
  [[ -z "${line// /}" ]] && continue

  # Match KEY=VALUE pattern
  if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
    KEY="${BASH_REMATCH[1]}"
    VALUE="${BASH_REMATCH[2]}"
    echo "export ${KEY}='${VALUE}'" >> "$CLAUDE_ENV_FILE"
    COUNT=$((COUNT + 1))
  fi
done < "$ENV_FILE"

echo "  exported $COUNT variables to $CLAUDE_ENV_FILE" >> "$LOG_FILE" 2>/dev/null
exit 0
