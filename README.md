# IG Non-Followers – 互動版

## 使用（Docker，跨平台建議）
1) 安裝 Docker Desktop
2) Windows：雙擊 `run_docker.bat`
   macOS/Linux：`chmod +x run_docker.sh && ./run_docker.sh`
3) 輸入帳號、密碼（不顯示）、需要時輸入 備用驗證碼
4) 完成後 `data/` 會有：`session-<username>`、`non_followers.csv`、`fans_you_dont_follow.csv`

## 直接用 Python（非必要）
```bash
python -m pip install -r requirements.txt
python main.py
```
輸出與 session 會在 `./data`。
