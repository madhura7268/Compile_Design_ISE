@echo off
cd /d "%~dp0"
echo Starting Streamlit on http://127.0.0.1:8501 ...
start http://127.0.0.1:8501
.\backend\venv\Scripts\streamlit.exe run backend/app.py --server.address 127.0.0.1 --server.port 8501
pause
