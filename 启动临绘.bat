@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Please create .venv and install dependencies using README.md.
  pause
  exit /b 1
)
.venv\Scripts\python.exe run.py %*
