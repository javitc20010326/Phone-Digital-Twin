param(
    [string]$Root = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

$adb = Join-Path $Root "platform-tools\adb.exe"
if (-not (Test-Path $adb)) {
    $adb = Join-Path $Root "tools\android-sdk\platform-tools\adb.exe"
}
if (-not (Test-Path $adb)) {
    throw "adb.exe not found. Run scripts\setup_android_toolchain.ps1 first."
}

& $adb devices -l
& $adb reverse tcp:8876 tcp:8876
& $adb shell am force-stop com.android.chrome
& $adb shell am start -a android.intent.action.VIEW -d "http://localhost:8876/phone?mode=generic"
