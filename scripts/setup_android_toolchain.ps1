param(
    [string]$Root = (Resolve-Path "$PSScriptRoot\..").Path
)

$ErrorActionPreference = "Stop"

function Download-File($Url, $OutFile) {
    if (Test-Path $OutFile) {
        Write-Host "Already downloaded: $OutFile"
        return
    }
    Write-Host "Downloading $Url"
    curl.exe -L $Url -o $OutFile
}

$tools = Join-Path $Root "tools"
$sdk = Join-Path $tools "android-sdk"
New-Item -ItemType Directory -Force -Path $tools | Out-Null

Download-File "https://aka.ms/download-jdk/microsoft-jdk-17-windows-x64.zip" (Join-Path $tools "microsoft-jdk-17-windows-x64.zip")
Download-File "https://services.gradle.org/distributions/gradle-8.10.2-bin.zip" (Join-Path $tools "gradle-8.10.2-bin.zip")
Download-File "https://dl.google.com/android/repository/commandlinetools-win-13114758_latest.zip" (Join-Path $tools "commandlinetools-win-latest.zip")

if (-not (Test-Path (Join-Path $tools "jdk17"))) {
    Expand-Archive -LiteralPath (Join-Path $tools "microsoft-jdk-17-windows-x64.zip") -DestinationPath (Join-Path $tools "jdk17") -Force
}

if (-not (Test-Path (Join-Path $tools "gradle-8.10.2\bin\gradle.bat"))) {
    Expand-Archive -LiteralPath (Join-Path $tools "gradle-8.10.2-bin.zip") -DestinationPath $tools -Force
}

$sdkManager = Join-Path $sdk "cmdline-tools\latest\bin\sdkmanager.bat"
if (-not (Test-Path $sdkManager)) {
    $tmp = Join-Path $sdk "cmdline-tools\_tmp"
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    tar.exe -xf (Join-Path $tools "commandlinetools-win-latest.zip") -C $tmp
    New-Item -ItemType Directory -Force -Path (Join-Path $sdk "cmdline-tools\latest") | Out-Null
    Move-Item -Force (Join-Path $tmp "cmdline-tools\*") (Join-Path $sdk "cmdline-tools\latest\")
    Remove-Item -LiteralPath $tmp -Recurse -Force
}

New-Item -ItemType Directory -Force -Path (Join-Path $sdk "licenses") | Out-Null
@("24333f8a63b6825ea9c5514f83c2829b004d1fee", "d56f5187479451eabf01fb78af6dfcb131a6481e") |
    Set-Content -Path (Join-Path $sdk "licenses\android-sdk-license") -Encoding ASCII
@("84831b9409646a918e30573bab4c9c91346d8abd") |
    Set-Content -Path (Join-Path $sdk "licenses\android-sdk-preview-license") -Encoding ASCII

$jdkHome = (Get-ChildItem (Join-Path $tools "jdk17") -Directory | Select-Object -First 1).FullName
$env:JAVA_HOME = $jdkHome
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
$env:ANDROID_HOME = $sdk
$env:ANDROID_SDK_ROOT = $sdk

& $sdkManager --sdk_root=$sdk "platforms;android-35" "build-tools;35.0.0" "platform-tools"

Write-Host "Android toolchain ready."
