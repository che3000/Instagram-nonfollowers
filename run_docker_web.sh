#!/usr/bin/env bash
# ================================================
# IG Non-Followers - Linux Web GUI 版本
# ================================================

set -euo pipefail
cd "$(dirname "$0")"
mkdir -p data

# 檢查 port 使用狀況
if netstat -tuln | grep -q ":7860 "; then
    echo "[WARN] Port 7860 已被占用"
    echo "[INFO] 建議使用其他 port 來啟動服務"
    echo ""
    read -p "請輸入新的 port 或直接按 Enter 使用預設值 7861: " NEW_PORT
    export PORT=${NEW_PORT:-7861}
    if [ -z "$NEW_PORT" ]; then
        echo "[INFO] 已選擇預設 port: 7861"
    fi
else
    export PORT=7860
fi

echo "[INFO] 使用 Port: $PORT"
echo "[INFO] 啟動 Web 版容器..."

# 如果有 xdg-open，在背景啟動瀏覽器
if command -v xdg-open > /dev/null; then
    (sleep 5 && xdg-open "http://localhost:$PORT") &
fi

set +e
docker compose up --build ig-web
CODE=$?
set -e

echo
echo "[INFO] 容器已結束，退出代碼：$CODE"
if [ "$CODE" -ne 0 ]; then
    echo "[WARN] 發生錯誤，請查看上面的錯誤訊息。"
else
    echo "[OK] Web 版執行完成"
    echo "[提示] 請在瀏覽器開啟：http://localhost:$PORT"
fi

echo
read -r -p "按 Enter 關閉視窗..." _