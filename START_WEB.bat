@echo off
echo ======================================
echo Starting SMTP Lab - Web Interface
echo ======================================
echo.

REM Change to the correct directory
cd /d "%~dp0"

echo [1/3] Starting SMTP Server (port 2525)...
start "SMTP Server" cmd /k "C:\Users\akash\Desktop\Networks sessional\.venv\Scripts\python.exe" server.py

echo [2/3] Starting WebSocket Server (port 8787)...
start "WebSocket Server" cmd /k "C:\Users\akash\Desktop\Networks sessional\.venv\Scripts\python.exe" web_server.py

echo [3/3] Waiting for servers to start...
timeout /t 3 /nobreak >nul

echo Opening Web Interface in browser...
start "" "index.html"

echo.
echo ======================================
echo All servers are running!
echo ======================================
echo SMTP Server:      localhost:2525
echo WebSocket Server: ws://localhost:8787
echo Web Interface:    index.html
echo ======================================
echo.
echo Press any key to stop all servers...
pause >nul

REM Stop the servers when user presses a key
echo.
echo Stopping servers...
taskkill /F /FI "WINDOWTITLE eq SMTP Server*" 2>nul
taskkill /F /FI "WINDOWTITLE eq WebSocket Server*" 2>nul

echo Servers stopped.
echo.
pause
