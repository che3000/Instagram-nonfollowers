#!/usr/bin/env bash
set -euo pipefail
mkdir -p data
echo "[INFO] 啟動互動式容器（可輸入帳號/密碼/2FA）…"
set +e
docker compose run --rm --build ig-nonfollowers
CODE=$?
set -e
echo
echo "[INFO] 容器已結束，退出代碼：$CODE"
if [ "$CODE" -ne 0 ]; then
  echo "[WARN] 發生錯誤，請查看上面的錯誤訊息。"
else
  echo "[OK] 完成。請到 data/ 目錄查看輸出與 session 檔。"
fi
echo
read -r -p "按 Enter 關閉視窗…" _
