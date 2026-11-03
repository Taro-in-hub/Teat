@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Run 01_SETUP_WINDOWS.cmd first.& pause & exit /b 1)
.venv\Scripts\python.exe -m streamlit run app.py
pause
