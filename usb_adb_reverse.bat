@echo off
setlocal

set "ADB="
if exist "%~dp0platform-tools\adb.exe" set "ADB=%~dp0platform-tools\adb.exe"
if not defined ADB if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" set "ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
if not defined ADB if exist "C:\Android\platform-tools\adb.exe" set "ADB=C:\Android\platform-tools\adb.exe"

if not defined ADB (
  echo No encuentro adb.exe.
  echo.
  echo Descarga Android SDK Platform-Tools oficial:
  echo https://developer.android.com/tools/releases/platform-tools
  echo.
  echo Extrae el ZIP aqui, de forma que exista:
  echo %~dp0platform-tools\adb.exe
  echo.
  pause
  exit /b 1
)

echo Usando ADB:
echo %ADB%
echo.

"%ADB%" start-server
echo.
echo Dispositivos detectados:
"%ADB%" devices
echo.

echo Creando tunel USB:
"%ADB%" reverse tcp:8876 tcp:8876
if errorlevel 1 (
  echo.
  echo No se pudo crear el tunel. Revisa que:
  echo - Depuracion USB esta activada en el Xiaomi.
  echo - Has aceptado la huella RSA en el movil.
  echo - El cable USB permite datos, no solo carga.
  pause
  exit /b 1
)

echo.
echo Tunel listo.
echo Abriendo la pagina local en el movil:
"%ADB%" shell am start -a android.intent.action.VIEW -d http://localhost:8876/phone
echo.
echo Si no se abre sola, abre en Chrome del movil:
echo http://localhost:8876/phone
echo.
pause
