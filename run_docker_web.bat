@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
if not exist "data" mkdir data

REM 檢查 7860 port 是否被占用
netstat -ano | find ":7860" > nul
if !ERRORLEVEL! EQU 0 (
    echo [WARN] Port 7860 已被占用
    echo [INFO] 建議使用其他 port 來啟動服務
    echo.
    set /p NEW_PORT="請輸入新的 port 或直接按 Enter 使用預設值 7861: "
    if "!NEW_PORT!"=="" (
        set NEW_PORT=7861
        echo [INFO] 已選擇預設 port: 7861
    )
    set PORT=!NEW_PORT!
) else (
    set PORT=7860
)

echo [INFO] 使用 Port: !PORT!
echo [INFO] 啟動 IG Non-Followers Web 版...
echo [INFO] 建立/更新 Docker 映像中，請稍候。

REM 在背景啟動瀏覽器（等待 5 秒讓 Docker 容器有時間啟動）
start /b cmd /c "timeout /t 5 /nobreak > nul && start http://localhost:!PORT!"

REM 啟動 web 服務，使用動態 port
docker compose -f docker/docker-compose.yml up ig-web --build

set "CODE=%ERRORLEVEL%"
echo.
echo [INFO] Docker compose exited with code: %CODE%

if not "%CODE%"=="0" (
  echo [WARN] 發生錯誤，請查看上方日誌。
) else (
  echo [OK] IG Non-Followers Web 版已結束。
)

echo.
echo [提示] 若執行成功，請在瀏覽器開啟：
echo          http://localhost:!PORT!
echo.
pause
endlocal