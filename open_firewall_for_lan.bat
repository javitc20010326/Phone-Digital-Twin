@echo off
net session >nul 2>&1
if not "%errorlevel%"=="0" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

echo Opening Phone Digital Twin firewall rules...
netsh advfirewall firewall delete rule name="Phone Digital Twin TCP 8876" >nul 2>&1
netsh advfirewall firewall delete rule name="Phone Digital Twin UDP 5005" >nul 2>&1
netsh advfirewall firewall add rule name="Phone Digital Twin TCP 8876" dir=in action=allow protocol=TCP localport=8876 profile=any
netsh advfirewall firewall add rule name="Phone Digital Twin UDP 5005" dir=in action=allow protocol=UDP localport=5005 profile=any
netsh advfirewall firewall show rule name="Phone Digital Twin TCP 8876"
netsh advfirewall firewall show rule name="Phone Digital Twin UDP 5005"
echo.
echo Done. You can close this window.
pause
