# NASAS 09 — flujo completo (tu PC, con internet y APS + OpenAI).
# 1) Genera el merge CAD de todos los DWG del proyecto en la carpeta indicada.
# 2) Ejecuta las tres corridas (PPR, PP, P) reutilizando ese merge (sin repetir APS).
# 3) Abre el Preliminary Budget (referencia, con hoja GENERAL) y los Excel de cada corrida.
#
# Uso (PowerShell, desde la raíz del repo):
#   .\scripts\run_nasas09_full_local.ps1

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Repo

$env:PYTHONUNBUFFERED = "1"
$OutCad = "aps_integration/NASAS 09/outputs/corridas/_cad_merge"

Write-Host "=== 1) CAD multi-DWG (NASAS) -> $OutCad ===" -ForegroundColor Cyan
& python (Join-Path $Repo "scripts/run_multi_dwg_project_cad.py") `
  --pattern "aps_integration/NASAS 09/NASAS arquitectura/PLANOS RECIBIDOS/**/*.dwg" `
  --output-dir $OutCad `
  --project-id nasas_09 `
  --project-name "NASAS 09" `
  --bc3 "data/TGIU.bc3"
if ($LASTEXITCODE -ne 0) { throw "Paso 1 (CAD) falló con código $LASTEXITCODE" }

Write-Host "=== 2) Corridas PPR, PP, P (visión + informes) ===" -ForegroundColor Cyan
& python (Join-Path $Repo "scripts/run_nasas09_corridas.py") `
  --reuse-cad $OutCad `
  --open-excels
if ($LASTEXITCODE -ne 0) { throw "Paso 2 (corridas) falló con código $LASTEXITCODE" }

Write-Host "Listo. Revisa aps_integration/NASAS 09/outputs/corridas/" -ForegroundColor Green
