# IG Non-Followers — 跨平台 Web/CLI（Docker 一鍵執行）

用來分析你的 Instagram 追蹤關係，找出「你追蹤但對方沒回追」與「對方追你但你沒回追」的用戶，並輸出成 CSV。
支援互動式登入（含 2FA 驗證碼）、自動儲存 Session、即時進度與錯誤重試。

## ✨ 最新功能亮點
- 🎨 **全新分頁式 Web 介面**：四個標籤頁清楚分類不同類型的用戶
- 📊 **互動式圓餅圖**：使用 Plotly.js 呈現美觀的統計圖表
- 📁 **智能檔案管理**：按日期自動整理 CSV 檔案到 `IGID_YYYYMMDDHHMMSS` 資料夾
- 🔄 **三階段身份驗證**：智慧檢測並處理 Instagram 登入流程
- 🌍 **時區本地化**：Docker 容器自動配置為台北時間

—

## 功能總覽
- 🐳 **一鍵 Docker**：Windows/macOS/Linux 皆可執行
- 🖥️ **兩種模式**：現代化 Web 介面（Flask）與指令列 CLI
- 🔐 **完整身份驗證**：支援 2FA、自動保存 Session 以免重複輸入密碼
- 📊 **視覺化統計**：互動式圓餅圖顯示追蹤關係分析
- 📁 **智能檔案組織**：CSV 檔案按日期分類存放
- 📈 **即時進度顯示**：WebSocket 即時更新分析進度
- 🛡️ **智能錯誤處理**：自動重試與速率限制處理

—

## 快速開始（建議使用 Docker）

### 1) 安裝 Docker Desktop
- 下載安裝：https://www.docker.com/products/docker-desktop/
- 專案安裝：https://github.com/che3000/Instagram-nonfollowers/releases
依照裝置版本選擇Docker版本
![image](/readme_picture/1.png)
—

### 2) 執行方式
- Web 介面（推薦）：
  - Windows：雙擊 `run_docker_web.bat`
  - macOS：雙擊 `run_docker_web.command`（首次若出現「無法打開」請到安全性與隱私允許）
  - Linux：`bash run_docker_web.sh`
  - 預設網址 `http://localhost:7860`；若 7860 已被占用，腳本會詢問改用其他 Port。
  - macOS/Linux 首次執行若無權限：`chmod +x run_docker_*.command run_docker_*.sh`
  ![image](/readme_picture/3.png)

- 指令列 CLI：
  - Windows：雙擊 `run_docker_cli.bat`
  - macOS：雙擊 `run_docker_cli.command`
  - Linux：`bash run_docker_cli.sh`
  - 注意：CLI 需要互動式終端機；若自行使用 docker 指令，請用 `docker compose -f docker/docker-compose.yml run --rm ig-cli`

這些腳本會自動檢查 Docker、建置映像、啟動容器，並把本機 `./data` 掛載到容器的 `/app/data`。
![image](/readme_picture/2.png)

—

### 3) 登入流程（互動模式）
- 依提示輸入 Instagram 帳號與密碼
- 若需要會再輸入 2FA 驗證碼
- 之後會建立 `data/session-<username>`，下次可免輸入密碼
![image](/readme_picture/3.png)

—

### 4) 輸出結果與檔案位置
 `data/` 資料夾會產生四份csv，網頁上也會根據csv產生及時結果。

- **共同檔案**
  - `session-<username>`：已登入的 Session（後續可重用）

- **Web 版（app.py）全新功能**
  - 📁 **智能檔案組織**：檔案自動存放到 `data/<username>_YYYYMMDDHHMMSS/` 資料夾
  - 📊 **互動式統計**：四個標籤頁 + Plotly.js 圓餅圖視覺化
  - 🎯 **標籤頁分類**：
    - **追蹤中**：你追蹤的所有人
    - **追蹤者**：追蹤你的所有人  
    - **沒回追你**：你追蹤但對方沒回追的人（重點關注）
    - **你沒回追**：對方追蹤你但你沒回追的人
  - 📈 **圓餅圖分析**：
    - 左側：你追蹤的人（有回追 vs 沒回追）
    - 右側：追蹤你的人（你也追蹤 vs 你沒追蹤）
  - 💾 **CSV 檔案**：
    - `following_users_YYYYMMDDHHMMSS.csv`
    - `followers_users_YYYYMMDDHHMMSS.csv` 
    - `non_followers_YYYYMMDDHHMMSS.csv`
    - `fans_you_dont_follow_YYYYMMDDHHMMSS.csv`

- **CLI 版（main.py）**
  - 會輸出兩種格式：
    - **固定檔名**（向後相容）：
      - `non_followers.csv`（你追蹤但對方沒回追）
      - `fans_you_dont_follow.csv`（對方追你但你沒回追）
    - **含帳號與時間戳**：
      - `following_users_<username>_<YYYYMMDDHHMMSS>.csv`
      - `followers_users_<username>_<YYYYMMDDHHMMSS>.csv`
      - `non_followers_<username>_<YYYYMMDDHHMMSS>.csv`
      - `fans_you_dont_follow_<username>_<YYYYMMDDHHMMSS>.csv`

—

## CSV 欄位說明
- `username`：Instagram 帳號
- `full_name`：公開顯示名稱（可能為空）
- `profile_url`：個人頁面 URL

所有 CSV 皆為 UTF-8（含 BOM），可直接用 Excel 開啟。

—

## 🎨 Web 介面功能展示

### **現代化分頁介面**
- 🏠 **首頁**：登入與開始分析
- 📊 **統計頁面**：互動式圓餅圖 + 四個標籤頁
  - **追蹤中** (👥)：顯示你追蹤的所有人
  - **追蹤者** (👤)：顯示追蹤你的所有人  
  - **沒回追你** (💔)：重點！你追蹤但對方沒回追
  - **你沒回追** (❤️)：對方追蹤你但你沒回追

### **互動式圓餅圖**
- 📈 **左側圖表**：你追蹤的人分析
  - 🟢 綠色：有回追的人數 + 百分比
  - 🔴 紅色：沒回追的人數 + 百分比
- 📈 **右側圖表**：追蹤你的人分析  
  - 🟢 綠色：你也追蹤的人數 + 百分比
  - 🔵 藍色：你沒追蹤的人數 + 百分比
- ✨ **互動功能**：懸停顯示詳細數據，可縮放與篩選

### **檔案管理系統**
- 📁 自動建立 `data/<username>_YYYYMMDDHHMMSS/` 資料夾
- 🔍 智能檢測歷史分析結果
- 📥 一鍵載入過往資料進行檢視

—

## 🛠️ 不用 Docker（原生執行）
安裝相依套件：

```bash
# Web 版（包含所有功能）
python -m pip install -r requirements-web.txt

# CLI 版（最小相依套件）
python -m pip install -r requirements-cli.txt
```

- **啟動 Web 介面**：

```bash
python app.py
# 或使用 gunicorn（需自行安裝）：
gunicorn "app:APP" --bind 0.0.0.0:7860 --workers 1 --threads 8 --timeout 120
```

- **執行 CLI**：

```bash
python main.py
```

**檔案輸出說明**：
- **Web 版**：檔案存放在 `./data/<username>_YYYYMMDDHHMMSS/` 資料夾，具備分頁介面與圖表分析
- **CLI 版**：產生固定檔名與時間戳檔名兩種格式，適合批次處理

—

## ⚙️ 進階設定與環境變數
- **Docker Compose 服務**：
  - `ig-web`：現代化 Web 介面，對外埠預設 `7860`（可用環境變數 `PORT` 覆蓋）
  - `ig-cli`：互動式 CLI（`docker compose -f docker/docker-compose.yml run --rm ig-cli`）
- **環境變數**：
  - `DATA_DIR`：資料存放目錄（預設 `./data`）
  - `TZ=Asia/Taipei`：時區設定（Docker 容器已預設台北時間）
- **維護工具**：
  - 重新建置映像：`docker compose -f docker/docker-compose.yml build --no-cache`

—

## ❓ 常見問題（FAQ）

### 🔐 **登入與驗證問題**
- **登入被擋 / 要求驗證**：
  - 請至 Instagram App「安全性」→「登入活動」確認「這是我」後重試
  - 程式現在具備**三階段身份驗證**，會自動處理大部分驗證流程
  - 若遇到 Challenge/Checkpoint，依提示確認後按 Enter 繼續（CLI）

### 🚀 **效能與速率問題**  
- **速率限制 Too Many Requests**：
  - 程式會自動等待後重試，具備智能速率控制
- **API 呼叫優化**：已修復 `custom_query_waittime()` 的呼叫方式

### 🌐 **網路與埠口問題**
- **Port 被占用**：
  - 啟動腳本會自動檢測並引導改用其他 Port（例如 7861）
- **圖表無法顯示**：
  - 確保網路連線正常（需載入 Plotly.js CDN）
  - 已更新至最新版本 Plotly.js v2.26.2

### 📁 **檔案與資料問題**
- **載入既有資料（Web）**：
  - 程式會自動偵測 `data/` 下的歷史資料夾
  - 可選擇特定日期的分析結果進行檢視
  - 支援載入 CLI 產生的 CSV 檔案
- **檔案找不到**：
  - Web 版檔案現在存放在 `data/<username>_YYYYMMDDHHMMSS/` 資料夾中
  - 可透過 Web 介面的資料夾選擇功能載入

### 🐳 **Docker 相關問題**
- **時區顯示錯誤**：
  - Docker 容器已預設台北時間（TZ=Asia/Taipei）
  - 如需重新建置：`docker compose -f docker/docker-compose.yml build --no-cache`

—

## 🔒 安全說明
- 🔐 **密碼安全**：密碼僅用於與 Instagram 建立 Session，不會保存在任何地方
- 💾 **Session 管理**：Session 存於 `data/session-<username>`；不需要時可自行刪除
- 🌐 **網路安全**：所有通訊透過 Instagram 官方 API，不經過第三方伺服器
- 🔒 **本地運行**：所有資料處理都在本機進行，保護您的隱私

## 🛠️ 技術架構
- **後端**：Python Flask + instaloader + gunicorn
- **前端**：HTML5 + CSS3 + JavaScript + Plotly.js v2.26.2  
- **容器化**：Docker + Docker Compose
- **資料格式**：CSV (UTF-8 with BOM)
- **圖表引擎**：Plotly.js 互動式圖表
- **即時通訊**：Server-Sent Events (SSE)
- **檔案結構**：Docker 相關檔案整理至 `docker/` 目錄，相依套件分離為 Web/CLI 版本

—

© 2025 黃靖元 (Ching‑Yuan Huang)
