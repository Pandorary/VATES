@echo off
chcp 65001 >nul
echo ============================================
echo   VATES 开发环境启动脚本
echo ============================================

REM 脚本位于 scripts/ 子目录，项目根目录为上一级
set ROOT=%~dp0..

echo [1/3] 清理旧进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001.*LISTENING" 2^>nul') do taskkill /f /pid %%a 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING" 2^>nul') do taskkill /f /pid %%a 2>nul
echo.

echo [2/3] 启动后端 (端口 8001)...
start "VATES-Backend" cmd /c "cd /d %ROOT% && set PYTHONPATH=%ROOT%;%ROOT%backend && uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload"
echo     后端启动中，请稍候...

echo [3/3] 启动前端 (端口 5173)...
start "VATES-Frontend" cmd /c "cd /d %ROOT%frontend && npm run dev"
echo     前端启动中，请稍候...

echo.
echo ============================================
echo   启动完成！
echo   后端: http://localhost:8001
echo   前端: http://localhost:5173
echo ============================================
pause
