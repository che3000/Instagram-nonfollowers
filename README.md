# IG Non-Followers – 互動版（跨平台一鍵執行）

本工具可自動比對 Instagram **誰沒回追你**、**誰你沒回追**，並輸出成 CSV。  
支援自動登入（含 2FA 備用碼）、自動儲存 Session、進度條顯示、錯誤重試。

---

## 🚀 使用方式（建議使用 Docker，一鍵執行）

### 1️⃣ 安裝 Docker Desktop
- [下載 Docker Desktop](https://www.docker.com/products/docker-desktop/)

---

### 2️⃣ 執行方式
- **Windows 使用者**：  
  ➤ 直接雙擊 `run_docker.bat`

- **macOS 使用者**：  
  ➤ 直接雙擊 `run_docker.command`  
  （第一次使用若出現「無法開啟」提示，請右鍵 → 開啟 → 允許執行）

> 💡 這兩個啟動器會自動檢查 Docker 狀態、build 映像、執行 container，無需手動操作。

---

### 3️⃣ 登入流程（自動互動）
執行後，依序輸入：
- Instagram 使用者名稱  
- 密碼（不顯示）  
- 若需要：輸入 **2FA 備用驗證碼**

登入成功後會建立 session 檔，之後不需再輸入密碼。

---

### 4️⃣ 完成後的輸出
執行結束後，請查看專案目錄下的 `data/` 資料夾：

| 檔案名稱 | 說明 |
|-----------|------|
| `session-<username>` | Instagram 登入 Session（下次自動使用） |
| `non_followers.csv` | 你追蹤但對方沒回追 |
| `fans_you_dont_follow.csv` | 對方追你但你沒回追 |

---

## 📄 CSV 欄位說明
所有輸出檔皆為 UTF-8（含 BOM），可直接以 Excel 開啟。

| 欄位 | 說明 |
|------|------|
| username | Instagram 帳號名稱 |
| full_name | 使用者公開顯示名稱（可能為中文） |
| profile_url | Instagram 個人頁面連結 |

---

## 🧰 進階使用（直接用 Python）
若你不想用 Docker，也可以直接執行 Python 版本：

```bash
python -m pip install -r requirements.txt
python main.py
```

輸出與 session 同樣會在 `./data/`。

---

## 🧩 常見問題

- **登入被擋下？**  
  請到 Instagram App → 安全性 → 登入活動 → 「這是我」後，再按 Enter 重試。

- **Docker 沒啟動？**  
  請先開啟 Docker Desktop，再執行 `.bat` / `.command`。

---

© 2025 黃靖元 (Ching-Yuan Huang)
