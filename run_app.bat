@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
echo Starting Streamlit on http://127.0.0.1:8501 ...
start http://127.0.0.1:8501
python -m streamlit run backend/app.py --server.address 127.0.0.1 --server.port 8501
if %ERRORLEVEL% NEQ 0 (
    .\backend\venv\Scripts\python.exe -m streamlit run backend/app.py --server.address 127.0.0.1 --server.port 8501
)
pause
