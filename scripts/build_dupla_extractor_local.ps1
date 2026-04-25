$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$project = Join-Path $repoRoot "aps_integration\DuplaExtractor\DuplaExtractor.csproj"
$dotnet = "C:\Program Files\dotnet\dotnet.exe"
$bundleContents = Join-Path $repoRoot "aps_integration\DuplaExtractor.bundle\Contents"

if (-not (Test-Path $project)) {
    throw "No se encontro el proyecto $project"
}

if (-not (Test-Path $dotnet)) {
    throw "No se encontro dotnet.exe en $dotnet"
}

$env:DOTNET_CLI_HOME = Join-Path $repoRoot ".dotnet_cli_home"
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = "1"
$env:DOTNET_CLI_TELEMETRY_OPTOUT = "1"
$env:NUGET_PACKAGES = Join-Path $repoRoot ".nuget_cache"

& $dotnet build $project -c Release

if ($LASTEXITCODE -ne 0) {
    throw "La compilacion de DuplaExtractor fallo con exit code $LASTEXITCODE"
}

$buildOut = Join-Path $repoRoot "aps_integration\DuplaExtractor\bin\Release\net10.0-windows"
New-Item -ItemType Directory -Force -Path $bundleContents | Out-Null
Copy-Item -Path (Join-Path $buildOut "*") -Destination $bundleContents -Force

Write-Host "Compilado:" (Join-Path $buildOut "DuplaExtractor.dll")
Write-Host "Bundle sincronizado:" $bundleContents
