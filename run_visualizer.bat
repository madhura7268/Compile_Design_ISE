@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
echo =====================================================================
echo Launching Phase 4 Native Streamlit Visualizer on http://127.0.0.1:8502
echo =====================================================================
start http://127.0.0.1:8502
python -m streamlit run backend/icg_app.py --server.address 127.0.0.1 --server.port 8502
if %ERRORLEVEL% NEQ 0 (
    .\backend\venv\Scripts\python.exe -m streamlit run backend/icg_app.py --server.address 127.0.0.1 --server.port 8502
)
pause
