@echo off
cd /d "%~dp0"
"%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -u web_digital_twin_server.py > web_twin.out.log 2> web_twin.err.log
