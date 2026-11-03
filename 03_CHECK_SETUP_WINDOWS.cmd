@echo off
cd /d "%~dp0"
py -3 --version
if exist ".venv\Scripts\python.exe" .venv\Scripts\python.exe -m pip --version
if exist ".venv\Scripts\python.exe" .venv\Scripts\python.exe -m streamlit --version
pause
