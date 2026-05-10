param(
    [string]$DefaultRepoName = "Phone-Digital-Twin"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..").Path

$token = Read-Host "GitHub token with repo scope"
$owner = Read-Host "GitHub username or organization"
$repo = Read-Host "Repository name" 
if ([string]::IsNullOrWhiteSpace($repo)) { $repo = $DefaultRepoName }

$headers = @{
    "Authorization" = "Bearer $token"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

function Invoke-GitHub($Method, $Uri, $Body = $null) {
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers
    }
    return Invoke-RestMethod -Method $Method -Uri $Uri -Headers $headers -Body ($Body | ConvertTo-Json -Depth 20) -ContentType "application/json"
}

$repoUri = "https://api.github.com/repos/$owner/$repo"
try {
    Invoke-GitHub GET $repoUri | Out-Null
    Write-Host "Repository exists: $owner/$repo"
}
catch {
    Write-Host "Creating repository: $repo"
    Invoke-GitHub POST "https://api.github.com/user/repos" @{
        name = $repo
        description = "Android phone sensors driving a local PC digital twin."
        private = $false
        auto_init = $true
    } | Out-Null
    Start-Sleep -Seconds 3
}

$excludeDirs = @("\tools\", "\platform-tools\", "\__pycache__\", "\.git\", "\.gradle\", "\app\build\", "\build\")
$excludeFiles = @("platform-tools-latest-windows.zip")

$files = Get-ChildItem -Path $Root -Recurse -File | Where-Object {
    $path = $_.FullName
    foreach ($dir in $excludeDirs) {
        if ($path.Contains($dir)) { return $false }
    }
    foreach ($file in $excludeFiles) {
        if ($_.Name -eq $file) { return $false }
    }
    return $true
}

foreach ($file in $files) {
    $relative = $file.FullName.Substring($Root.Length + 1).Replace("\", "/")
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    $content = [Convert]::ToBase64String($bytes)
    $contentUri = "https://api.github.com/repos/$owner/$repo/contents/$relative"
    $sha = $null
    try {
        $existing = Invoke-GitHub GET $contentUri
        $sha = $existing.sha
    }
    catch {
        $sha = $null
    }

    $body = @{
        message = "Publish Phone Digital Twin project"
        content = $content
        branch = "main"
    }
    if ($sha) { $body.sha = $sha }

    Write-Host "Uploading $relative"
    Invoke-GitHub PUT $contentUri $body | Out-Null
}

Write-Host "Done: https://github.com/$owner/$repo"
