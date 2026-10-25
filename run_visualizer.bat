@echo off
cd /d "%~dp0"
echo Starting Phase 4 Standalone Visualizer on http://127.0.0.1:8090 ...
start http://127.0.0.1:8090
.\backend\venv\Scripts\python.exe -m http.server 8090 -d visualizer --bind 127.0.0.1
pause
