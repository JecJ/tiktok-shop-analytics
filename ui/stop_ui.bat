@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist logs\ui.pid (
  echo 未找到由后台启动器创建的进程记录。若在此窗口运行看板，请按 Ctrl+C 停止。
  pause
  exit /b 0
)
set /p UI_PID=<logs\ui.pid
powershell -NoProfile -Command "$proc = Get-Process -Id %UI_PID% -ErrorAction SilentlyContinue; if ($proc) { Stop-Process -Id %UI_PID% -Force; Write-Output 'TikTok Shop 看板已停止。' } else { Write-Output '看板进程已经停止。' }; Remove-Item logs\ui.pid -ErrorAction SilentlyContinue"
pause
