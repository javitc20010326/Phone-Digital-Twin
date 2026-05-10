@echo off
setlocal
set "PY=C:\Users\javit\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
cd /d "%~dp0"
"%PY%" redmi_desktop_twin.py
