param(
    [string[]]$DwgPaths,
    [ValidateSet("improved", "legacy")]
    [string]$AreaMode = "improved",
    [string]$RunLabel
)

$ErrorActionPreference = "Stop"

function Get-DotEnvMap {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $values = @{}
    foreach ($line in Get-Content -Path $Path) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith("#")) {
            continue
        }

        $parts = $line -split "=", 2
        if ($parts.Count -eq 2) {
            $values[$parts[0].Trim()] = $parts[1].Trim()
        }
    }

    return $values
}

function Invoke-ApsMultipartUpload {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        $FormData,
        [Parameter(Mandatory = $true)]
        [string]$FilePath
    )

    Add-Type -AssemblyName System.Net.Http

    $client = [System.Net.Http.HttpClient]::new()
    try {
        $content = [System.Net.Http.MultipartFormDataContent]::new()
        foreach ($property in $FormData.PSObject.Properties) {
            $content.Add([System.Net.Http.StringContent]::new([string]$property.Value), $property.Name)
        }

        $bytes = [System.IO.File]::ReadAllBytes($FilePath)
        $fileContent = [System.Net.Http.ByteArrayContent]::new($bytes)
        $fileContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("application/octet-stream")
        $content.Add($fileContent, "file", [System.IO.Path]::GetFileName($FilePath))

        $response = $client.PostAsync($Url, $content).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            throw "Multipart upload failed: $($response.StatusCode) $body"
        }
    }
    finally {
        $client.Dispose()
    }
}

function Send-FileToUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [string]$FilePath
    )

    Add-Type -AssemblyName System.Net.Http

    $client = [System.Net.Http.HttpClient]::new()
    try {
        $bytes = [System.IO.File]::ReadAllBytes($FilePath)
        $content = [System.Net.Http.ByteArrayContent]::new($bytes)
        $content.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("application/octet-stream")

        $response = $client.PutAsync($Url, $content).GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            throw "Binary upload failed: $($response.StatusCode) $body"
        }
    }
    finally {
        $client.Dispose()
    }
}

function Receive-FileFromUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [string]$FilePath
    )

    Add-Type -AssemblyName System.Net.Http

    $client = [System.Net.Http.HttpClient]::new()
    try {
        $bytes = $client.GetByteArrayAsync($Url).GetAwaiter().GetResult()
        [System.IO.File]::WriteAllBytes($FilePath, $bytes)
    }
    finally {
        $client.Dispose()
    }
}

function Invoke-ApsJson {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Method,
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $false)]
        $Body,
        [Parameter(Mandatory = $false)]
        [hashtable]$Headers
    )

    $params = @{
        Method = $Method
        Uri = $Url
    }

    if ($Headers) {
        $params.Headers = $Headers
    }

    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 20)
    }

    return Invoke-RestMethod @params
}

function Get-SignedUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseOssUrl,
        [Parameter(Mandatory = $true)]
        [string]$Bucket,
        [Parameter(Mandatory = $true)]
        [string]$ObjectName,
        [Parameter(Mandatory = $true)]
        [string]$Access,
        [Parameter(Mandatory = $true)]
        [hashtable]$Headers
    )

    $payload = @{
        minutesExpiration = 60
    }

    if ($Access -eq "write") {
        $payload.singleUse = $true
    }
    elseif ($Access -eq "readWrite") {
        $payload.singleUse = $false
    }

    $encodedObject = [System.Uri]::EscapeDataString($ObjectName)
    $url = "$BaseOssUrl/buckets/$Bucket/objects/$encodedObject/signed?access=$Access"
    $response = Invoke-ApsJson -Method "Post" -Url $url -Body $payload -Headers $Headers
    return $response.signedUrl
}

function Ensure-Bucket {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseOssUrl,
        [Parameter(Mandatory = $true)]
        [string]$Bucket,
        [Parameter(Mandatory = $true)]
        [hashtable]$Headers
    )

    $payload = @{
        bucketKey = $Bucket
        policyKey = "transient"
    }

    try {
        Invoke-ApsJson -Method "Post" -Url "$BaseOssUrl/buckets" -Body $payload -Headers $Headers | Out-Null
    }
    catch {
        if (-not $_.Exception.Message.Contains("409")) {
            throw
        }
    }
}

function Upsert-AppBundle {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseDaUrl,
        [Parameter(Mandatory = $true)]
        [string]$ClientId,
        [Parameter(Mandatory = $true)]
        [string]$AppBundleName,
        [Parameter(Mandatory = $true)]
        [string]$EngineId,
        [Parameter(Mandatory = $true)]
        [string]$ZipPath,
        [Parameter(Mandatory = $true)]
        [hashtable]$Headers
    )

    $payload = @{
        id = $AppBundleName
        engine = $EngineId
        description = "Extractor de metricas de bloques y polilineas para Dupla"
    }

    try {
        $response = Invoke-ApsJson -Method "Post" -Url "$BaseDaUrl/appbundles" -Body $payload -Headers $Headers
    }
    catch {
        if (-not $_.Exception.Message.Contains("409")) {
            throw
        }

        $response = Invoke-ApsJson -Method "Post" -Url "$BaseDaUrl/appbundles/$AppBundleName/versions" -Body @{ engine = $EngineId } -Headers $Headers
    }

    Invoke-ApsMultipartUpload -Url $response.uploadParameters.endpointURL -FormData $response.uploadParameters.formData -FilePath $ZipPath

    $aliasPayload = @{
        id = "dev"
        version = $response.version
    }

    try {
        Invoke-ApsJson -Method "Post" -Url "$BaseDaUrl/appbundles/$AppBundleName/aliases" -Body $aliasPayload -Headers $Headers | Out-Null
    }
    catch {
        if (-not $_.Exception.Message.Contains("409")) {
            throw
        }

        Invoke-ApsJson -Method "Patch" -Url "$BaseDaUrl/appbundles/$AppBundleName/aliases/dev" -Body @{ version = $response.version } -Headers $Headers | Out-Null
    }

    return "$ClientId.$AppBundleName+dev"
}

function Upsert-Activity {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseDaUrl,
        [Parameter(Mandatory = $true)]
        [string]$ClientId,
        [Parameter(Mandatory = $true)]
        [string]$ActivityName,
        [Parameter(Mandatory = $true)]
        [string]$EngineId,
        [Parameter(Mandatory = $true)]
        [string]$AppBundleId,
        [Parameter(Mandatory = $true)]
        [hashtable]$Headers
    )

    $payload = @{
        id = $ActivityName
        commandLine = @("`$(engine.path)\accoreconsole.exe /i `"`$(args[inputFile].path)`" /al `"`$(appbundles[DuplaExtractor].path)`" /s `"`$(settings[script].path)`"")
        parameters = @{
            inputFile = @{
                verb = "get"
                description = "El DWG a procesar"
                required = $true
                localName = "`$(inputFile)"
            }
            outputJson = @{
                verb = "put"
                description = "El JSON resultante con las mediciones"
                required = $true
                localName = "resultados.json"
            }
            outputAreasJson = @{
                verb = "put"
                description = "JSON enfocado en el analisis de areas"
                required = $false
                localName = "resultados_areas.json"
            }
            areaModeConfig = @{
                verb = "get"
                description = "Configuracion del modo de calculo de areas"
                required = $false
                localName = "dupla_area_mode.txt"
            }
        }
        engine = $EngineId
        appbundles = @($AppBundleId)
        description = "Extrae polilineas, bloques y superficies a JSON."
        settings = @{
            script = @{
                value = "EXTRACTDUPLADATA`n"
            }
        }
    }

    try {
        $response = Invoke-ApsJson -Method "Post" -Url "$BaseDaUrl/activities" -Body $payload -Headers $Headers
    }
    catch {
        if (-not $_.Exception.Message.Contains("409")) {
            throw
        }

        $versionPayload = $payload.Clone()
        $null = $versionPayload.Remove("id")
        $response = Invoke-ApsJson -Method "Post" -Url "$BaseDaUrl/activities/$ActivityName/versions" -Body $versionPayload -Headers $Headers
    }

    $aliasPayload = @{
        id = "dev"
        version = $response.version
    }

    try {
        Invoke-ApsJson -Method "Post" -Url "$BaseDaUrl/activities/$ActivityName/aliases" -Body $aliasPayload -Headers $Headers | Out-Null
    }
    catch {
        if (-not $_.Exception.Message.Contains("409")) {
            throw
        }

        Invoke-ApsJson -Method "Patch" -Url "$BaseDaUrl/activities/$ActivityName/aliases/dev" -Body @{ version = $response.version } -Headers $Headers | Out-Null
    }

    return "$ClientId.$ActivityName+dev"
}

function Wait-WorkItem {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseDaUrl,
        [Parameter(Mandatory = $true)]
        [string]$WorkItemId,
        [Parameter(Mandatory = $true)]
        [hashtable]$Headers
    )

    while ($true) {
        $state = Invoke-ApsJson -Method "Get" -Url "$BaseDaUrl/workitems/$WorkItemId" -Headers $Headers
        Write-Host ("   Estado actual: {0}" -f $state.status)
        if ($state.status -in @("success", "failed", "cancelled", "failedDownload", "failedUpload", "failedInstructions")) {
            return $state
        }
        Start-Sleep -Seconds 3
    }
}

$repoRoot = "C:\Users\Enrique Casanova\Dupla"
$envMap = Get-DotEnvMap -Path (Join-Path $repoRoot ".env")
$clientId = $envMap["CLIENT_ID"]
$clientSecret = $envMap["CLIENT_SECRET"]
$bucket = if ($envMap.ContainsKey("APS_BUCKET_NAME")) { $envMap["APS_BUCKET_NAME"] } else { "dupla_dwg_bucket_test_01" }

$authBody = @{
    client_id = $clientId
    client_secret = $clientSecret
    grant_type = "client_credentials"
    scope = "data:read data:write data:create bucket:create bucket:read code:all viewables:read"
}

$auth = Invoke-RestMethod -Method Post -Uri "https://developer.api.autodesk.com/authentication/v2/token" -ContentType "application/x-www-form-urlencoded" -Body $authBody
$token = $auth.access_token
$headers = @{
    Authorization = "Bearer $token"
}

$baseDaUrl = "https://developer.api.autodesk.com/da/us-east/v3"
$baseOssUrl = "https://developer.api.autodesk.com/oss/v2"
$engineId = "Autodesk.AutoCAD+24_3"
$appBundleName = "DuplaExtractor"
$activityName = "DuplaExtractActivity"
$zipPath = Join-Path $repoRoot "aps_integration\DuplaExtractor.zip"

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$labelParts = @($AreaMode)
if (-not [string]::IsNullOrWhiteSpace($RunLabel)) {
    $labelParts += $RunLabel
}
$safeLabel = (($labelParts -join "_") -replace "[^A-Za-z0-9_-]", "_")
$outputDir = Join-Path $repoRoot ("analysis_output\aps_area_run_" + $stamp + "_" + $safeLabel)
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$modeConfigPath = Join-Path $outputDir "dupla_area_mode.txt"
Set-Content -LiteralPath $modeConfigPath -Value $AreaMode -Encoding ASCII
$modeObject = "$stamp-$safeLabel-dupla_area_mode.txt"

Write-Host "Publicando AppBundle..."
$appBundleId = Upsert-AppBundle -BaseDaUrl $baseDaUrl -ClientId $clientId -AppBundleName $appBundleName -EngineId $engineId -ZipPath $zipPath -Headers $headers

Write-Host "Publicando Activity..."
$activityId = Upsert-Activity -BaseDaUrl $baseDaUrl -ClientId $clientId -ActivityName $activityName -EngineId $engineId -AppBundleId $appBundleId -Headers $headers

Write-Host "Asegurando bucket OSS..."
Ensure-Bucket -BaseOssUrl $baseOssUrl -Bucket $bucket -Headers $headers

Write-Host ("Subiendo configuracion de modo de areas: {0}" -f $AreaMode)
$modeWriteUrl = Get-SignedUrl -BaseOssUrl $baseOssUrl -Bucket $bucket -ObjectName $modeObject -Access "write" -Headers $headers
Send-FileToUrl -Url $modeWriteUrl -FilePath $modeConfigPath
$modeReadUrl = Get-SignedUrl -BaseOssUrl $baseOssUrl -Bucket $bucket -ObjectName $modeObject -Access "read" -Headers $headers

$dwgPaths = if ($DwgPaths -and $DwgPaths.Count -gt 0) {
    $DwgPaths
}
else {
    @(
        (Join-Path $repoRoot "2- PLANTAS ARQUITECTONICAS.dwg"),
        (Join-Path $repoRoot "ACAD-04-PLANTA DIMENSIONADA-Model.dwg")
    )
}

$summary = @()

foreach ($dwgPath in $dwgPaths) {
    if (-not (Test-Path $dwgPath)) {
        continue
    }

    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($dwgPath)
    $safeName = ($baseName -replace "[^A-Za-z0-9_-]", "_")
    $inputObject = "$stamp-$safeName.dwg"
    $jsonObject = "$stamp-$safeName-resultados.json"
    $areasObject = "$stamp-$safeName-resultados_areas.json"

    Write-Host ("Subiendo DWG: {0}" -f $dwgPath)
    $inputWriteUrl = Get-SignedUrl -BaseOssUrl $baseOssUrl -Bucket $bucket -ObjectName $inputObject -Access "write" -Headers $headers
    Send-FileToUrl -Url $inputWriteUrl -FilePath $dwgPath

    $inputReadUrl = Get-SignedUrl -BaseOssUrl $baseOssUrl -Bucket $bucket -ObjectName $inputObject -Access "read" -Headers $headers
    $outputJsonWriteUrl = Get-SignedUrl -BaseOssUrl $baseOssUrl -Bucket $bucket -ObjectName $jsonObject -Access "write" -Headers $headers
    $outputAreasWriteUrl = Get-SignedUrl -BaseOssUrl $baseOssUrl -Bucket $bucket -ObjectName $areasObject -Access "write" -Headers $headers

    $workItemPayload = @{
        activityId = $activityId
        arguments = @{
            inputFile = @{
                url = $inputReadUrl
            }
            areaModeConfig = @{
                verb = "get"
                url = $modeReadUrl
            }
            outputJson = @{
                verb = "put"
                url = $outputJsonWriteUrl
            }
            outputAreasJson = @{
                verb = "put"
                url = $outputAreasWriteUrl
            }
        }
    }

    $workItem = Invoke-ApsJson -Method "Post" -Url "$baseDaUrl/workitems" -Body $workItemPayload -Headers $headers
    Write-Host ("WorkItem enviado: {0}" -f $workItem.id)
    $finalState = Wait-WorkItem -BaseDaUrl $baseDaUrl -WorkItemId $workItem.id -Headers $headers

    $reportPath = Join-Path $outputDir ($safeName + "-report.json")
    $finalState | ConvertTo-Json -Depth 20 | Set-Content -Path $reportPath -Encoding UTF8

    $runSummary = [ordered]@{
        drawing = $dwgPath
        areaMode = $AreaMode
        workItemId = $workItem.id
        status = $finalState.status
        reportUrl = $finalState.reportUrl
        outputJsonPath = $null
        outputAreasJsonPath = $null
    }

    if ($finalState.status -eq "success") {
        $outputJsonReadUrl = Get-SignedUrl -BaseOssUrl $baseOssUrl -Bucket $bucket -ObjectName $jsonObject -Access "read" -Headers $headers
        $outputAreasReadUrl = Get-SignedUrl -BaseOssUrl $baseOssUrl -Bucket $bucket -ObjectName $areasObject -Access "read" -Headers $headers

        $jsonPath = Join-Path $outputDir ($safeName + "-resultados.json")
        $areasPath = Join-Path $outputDir ($safeName + "-resultados_areas.json")

        Receive-FileFromUrl -Url $outputJsonReadUrl -FilePath $jsonPath
        Receive-FileFromUrl -Url $outputAreasReadUrl -FilePath $areasPath

        $runSummary.outputJsonPath = $jsonPath
        $runSummary.outputAreasJsonPath = $areasPath
    }

    $summary += [pscustomobject]$runSummary
}

$summaryPath = Join-Path $outputDir "summary.json"
$summary | ConvertTo-Json -Depth 20 | Set-Content -Path $summaryPath -Encoding UTF8
Write-Host ("Resumen guardado en: {0}" -f $summaryPath)
