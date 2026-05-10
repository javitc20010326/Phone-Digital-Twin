param(
    [string]$Root = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path (Join-Path $Root "tools\gradle-8.10.2\bin\gradle.bat"))) {
    & (Join-Path $PSScriptRoot "setup_android_toolchain.ps1") -Root $Root
}

$jdkHome = (Get-ChildItem (Join-Path $Root "tools\jdk17") -Directory | Select-Object -First 1).FullName
$env:JAVA_HOME = $jdkHome
$env:PATH = "$env:JAVA_HOME\bin;$(Join-Path $Root "tools\gradle-8.10.2\bin");$env:PATH"
$env:ANDROID_HOME = Join-Path $Root "tools\android-sdk"
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:GRADLE_USER_HOME = Join-Path $Root "tools\gradle-home"

Push-Location (Join-Path $Root "android-sensor-sender")
try {
    & (Join-Path $Root "tools\gradle-8.10.2\bin\gradle.bat") assembleDebug --no-daemon
}
finally {
    Pop-Location
}

Write-Host "APK built: $(Join-Path $Root "android-sensor-sender\app\build\outputs\apk\debug\app-debug.apk")"
