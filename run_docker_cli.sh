#!/usr/bin/env bash
# ================================================
# IG Non-Followers - Linux CLI 版本
# ================================================

set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data

echo "[INFO] 啟動命令列版容器..."
set +e
docker compose -f docker/docker-compose.yml run --rm ig-cli
CODE=$?
set -e

echo
echo "[INFO] 容器已結束，退出代碼：$CODE"
if [ "$CODE" -ne 0 ]; then
    echo "[WARN] 發生錯誤，請查看上面的錯誤訊息。"
else
    echo "[OK] 命令列版完成。請到 data/ 目錄查看輸出與 session 檔。"
fi

echo
read -r -p "按 Enter 關閉視窗..." _