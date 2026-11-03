@echo off
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 (echo Python not found. Install Python 3.11+ then retry.& pause & exit /b 1)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed.& pause & exit /b 1)
echo SETUP COMPLETE. Run 02_RUN_APP_WINDOWS.cmd
pause
