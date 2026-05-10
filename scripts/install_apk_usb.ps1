param(
    [string]$Root = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

$adb = Join-Path $Root "platform-tools\adb.exe"
if (-not (Test-Path $adb)) {
    $adb = Join-Path $Root "tools\android-sdk\platform-tools\adb.exe"
}
if (-not (Test-Path $adb)) {
    & (Join-Path $PSScriptRoot "setup_android_toolchain.ps1") -Root $Root
    $adb = Join-Path $Root "tools\android-sdk\platform-tools\adb.exe"
}

$apk = Join-Path $Root "android-sensor-sender\app\build\outputs\apk\debug\app-debug.apk"
if (-not (Test-Path $apk)) {
    & (Join-Path $PSScriptRoot "build_apk.ps1") -Root $Root
}

& $adb devices -l
& $adb reverse tcp:8876 tcp:8876
& $adb install -r $apk
& $adb shell monkey -p local.codex.redmisensors 1

Write-Host "If Android blocks installation, enable Developer options > Install via USB."
