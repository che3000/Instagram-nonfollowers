#!/bin/bash
# ================================================
# IG Non-Followers - macOS Web GUI 版本
# ================================================

# 切換到腳本所在目錄
cd "$(dirname "$0")"

# 檢查 Docker 是否可用
if ! command -v docker &> /dev/null; then
  echo "[ERROR] 未偵測到 Docker，請先安裝 Docker Desktop for Mac。"
  echo "下載：https://www.docker.com/products/docker-desktop/"
  read -n 1 -s -r -p "按任意鍵結束..."
  exit 1
fi

# 檢查 Docker 是否正在運行
if ! docker info >/dev/null 2>&1; then
  echo "[ERROR] Docker 尚未啟動，請先打開 Docker Desktop。"
  read -n 1 -s -r -p "按任意鍵結束..."
  exit 1
fi

# 檢查 port 使用狀況
if lsof -Pi :7860 -sTCP:LISTEN -t >/dev/null ; then
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
echo "[INFO] 建立並啟動 Web 容器中..."

# 在背景啟動瀏覽器
(sleep 5 && open "http://localhost:$PORT") &

# 啟動 web 服務
docker compose -f docker/docker-compose.yml up --build ig-web

EXIT_CODE=$?
echo ""
echo "==============================================="
echo "[INFO] Container 結束，返回代碼: $EXIT_CODE"
if [ $EXIT_CODE -eq 0 ]; then
    echo "[OK] Web 版執行完成。"
    echo "[提示] 請在瀏覽器開啟: http://localhost:$PORT"
else
    echo "[WARN] 執行中發生錯誤，請檢查上方訊息。"
fi
echo "==============================================="

# 保持 Terminal 開啟，讓使用者能閱讀訊息
read -n 1 -s -r -p "按任意鍵關閉視窗..."