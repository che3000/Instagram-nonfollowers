@echo off
setlocal
if not exist "data" mkdir data

echo [INFO] Starting interactive container...
docker compose run --rm --build ig-nonfollowers
set "CODE=%ERRORLEVEL%"
echo.
echo [INFO] Container exited with code: %CODE%
if not "%CODE%"=="0" (
  echo [WARN] Error occurred. See logs above.
) else (
  echo [OK] Done. Check data\ for CSV and session.
)
echo.
pause
endlocal
