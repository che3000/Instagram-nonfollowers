#!/bin/bash
# ================================================
# IG Non-Followers - macOS CLI 版本
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

echo "[INFO] 建立並啟動命令列容器中..."
docker compose -f docker/docker-compose.yml run --rm ig-cli

EXIT_CODE=$?
echo ""
echo "==============================================="
echo "[INFO] Container 結束，返回代碼: $EXIT_CODE"
if [ $EXIT_CODE -eq 0 ]; then
    echo "[OK] 命令列版執行完成，請在 data/ 資料夾中查看 CSV 檔。"
else
    echo "[WARN] 執行中發生錯誤，請檢查上方訊息。"
fi
echo "==============================================="

# 保持 Terminal 開啟，讓使用者能閱讀訊息
read -n 1 -s -r -p "按任意鍵關閉視窗..."