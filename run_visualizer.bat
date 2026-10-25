@echo off
cd /d "%~dp0"
echo =====================================================================
echo Launching Phase 4 Native Streamlit Visualizer on http://127.0.0.1:8502
echo =====================================================================
start http://127.0.0.1:8502
.\backend\venv\Scripts\streamlit.exe run backend/icg_app.py --server.address 127.0.0.1 --server.port 8502
pause
