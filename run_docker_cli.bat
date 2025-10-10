@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
if not exist "data" mkdir data

echo [INFO] 啟動 IG Non-Followers 命令列版本...
echo [INFO] 建立/更新 Docker 映像中，請稍候。

REM 啟動 CLI 服務（使用互動式終端機）
docker compose run --rm ig-cli

set "CODE=%ERRORLEVEL%"
echo.
echo [INFO] Docker compose exited with code: %CODE%

if not "%CODE%"=="0" (
  echo [WARN] 發生錯誤，請查看上方日誌。
) else (
  echo [OK] IG Non-Followers 命令列版本已結束。
)

pause
endlocal