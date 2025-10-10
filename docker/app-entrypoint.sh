#!/usr/bin/env sh
set -e

# 自動偵測與套用時區（若未指定 TZ）
if [ -z "$TZ" ]; then
  if [ -f /etc/timezone ]; then
    TZ_FROM_FILE=$(cat /etc/timezone 2>/dev/null || true)
    [ -n "$TZ_FROM_FILE" ] && export TZ="$TZ_FROM_FILE"
  fi
fi
if [ -z "$TZ" ] && [ -L /etc/localtime ]; then
  TZ_LINK=$(readlink /etc/localtime 2>/dev/null || true)
  # 取出 IANA 名稱
  TZ_GUESS=$(echo "$TZ_LINK" | sed 's#.*/zoneinfo/##')
  [ -n "$TZ_GUESS" ] && export TZ="$TZ_GUESS"
fi
# 若已取得 TZ，嘗試套用到 /etc/localtime（需要 tzdata）
if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
  ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime || true
fi

MODE="${MODE:-web}"
PORT="${PORT:-7860}"

if [ "$MODE" = "web" ]; then
  exec gunicorn "app:APP" --bind "0.0.0.0:${PORT}" --workers "1" --threads "8" --timeout "120"
else
  exec python main.py
fi
