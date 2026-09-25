param(
  [Parameter(Mandatory=$true)]
  [string]$InstallPath
)

$ErrorActionPreference = "Stop"
$PackageUrl = "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/release/v1.3.25-bootstrap-v3-package.json"
$PackageSha256 = "c1ecc7dbf7f5deca115ee6a05e1dce598aca9c1b94e940ce7691e444152a65f5"
$ExpectedSourceVersion = "1.3.25"
$ExpectedSourceBuild = "1.3.25-release"
$ExpectedTargetVersion = "1.3.25"
$ExpectedTargetBuild = "1.3.25-bootstrap-release-v3"

function Get-Sha256Bytes([byte[]]$Bytes) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace("-","").ToLowerInvariant()
  } finally { $sha.Dispose() }
}

function Assert-SafePath([string]$Path) {
  $root = @("manifest.json","build.json","background.js","popup.html","popup.js","icon128.png","integrity-manifest.json")
  if ($root -contains $Path) { return }
  if ($Path -match '^js/[A-Za-z0-9._-]+\.js$') { return }
  throw "Ruta no autorizada en package: $Path"
}

$InstallPath = [System.IO.Path]::GetFullPath($InstallPath)
if (-not (Test-Path -LiteralPath $InstallPath -PathType Container)) {
  throw "La carpeta no existe: $InstallPath"
}

$manifestPath = Join-Path $InstallPath "manifest.json"
$buildPath = Join-Path $InstallPath "build.json"
if (-not (Test-Path -LiteralPath $manifestPath) -or -not (Test-Path -LiteralPath $buildPath)) {
  throw "La carpeta no parece una instalación de VIENA NOC Tools."
}

$sourceManifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$sourceBuild = Get-Content -LiteralPath $buildPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($sourceManifest.version -ne $ExpectedSourceVersion -or $sourceBuild.build -ne $ExpectedSourceBuild -or $sourceBuild.channel -ne "RELEASE") {
  throw "Este rescate sólo se permite sobre RELEASE $ExpectedSourceVersion / $ExpectedSourceBuild. Detectado: v$($sourceManifest.version) / $($sourceBuild.build) / $($sourceBuild.channel)"
}

$temp = Join-Path $env:TEMP ("viena-bootstrap-" + [Guid]::NewGuid().ToString("N") + ".json")
$backup = Join-Path (Split-Path -Parent $InstallPath) ((Split-Path -Leaf $InstallPath) + "_BACKUP_" + (Get-Date -Format "yyyyMMdd_HHmmss"))

Write-Host "Descargando bootstrap verificado..."
Invoke-WebRequest -Uri ($PackageUrl + "?_=" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) -OutFile $temp -UseBasicParsing
$downloadBytes = [System.IO.File]::ReadAllBytes($temp)
$downloadSha = Get-Sha256Bytes $downloadBytes
if ($downloadSha -ne $PackageSha256) {
  Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
  throw "SHA-256 del package incorrecto. Esperado $PackageSha256, obtenido $downloadSha"
}

$pkg = [System.Text.Encoding]::UTF8.GetString($downloadBytes) | ConvertFrom-Json
if ($pkg.schema -ne 1 -or $pkg.app -ne "VIENA NOC Tools" -or $pkg.version -ne $ExpectedTargetVersion -or $pkg.build -ne $ExpectedTargetBuild -or $pkg.channel -ne "RELEASE") {
  throw "Identidad del bootstrap inválida."
}

$seen = @{}
$decoded = @{}
foreach ($item in $pkg.files) {
  $p = [string]$item.path
  Assert-SafePath $p
  if ($seen.ContainsKey($p)) { throw "Archivo duplicado: $p" }
  $seen[$p] = $true
  $bytes = [Convert]::FromBase64String([string]$item.content_base64)
  if ($bytes.Length -ne [int64]$item.size) { throw "Tamaño inválido: $p" }
  $sha = Get-Sha256Bytes $bytes
  if ($sha -ne ([string]$item.sha256).ToLowerInvariant()) { throw "SHA inválido: $p" }
  $decoded[$p] = $bytes
}

foreach ($required in @("manifest.json","build.json","background.js","popup.html","popup.js","icon128.png","integrity-manifest.json")) {
  if (-not $decoded.ContainsKey($required)) { throw "Falta archivo requerido: $required" }
}

Write-Host "Creando backup completo en: $backup"
Copy-Item -LiteralPath $InstallPath -Destination $backup -Recurse

$identityLast = @("manifest.json","integrity-manifest.json","build.json")
$normal = @($decoded.Keys | Where-Object { $identityLast -notcontains $_ } | Sort-Object)
$order = @($normal + $identityLast)

try {
  foreach ($p in $order) {
    $target = Join-Path $InstallPath ($p -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    $dir = Split-Path -Parent $target
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $tmpTarget = $target + ".viena-new"
    [System.IO.File]::WriteAllBytes($tmpTarget, $decoded[$p])
    Move-Item -LiteralPath $tmpTarget -Destination $target -Force
  }

  foreach ($p in $decoded.Keys) {
    $target = Join-Path $InstallPath ($p -replace '/', [System.IO.Path]::DirectorySeparatorChar)
    $got = Get-Sha256Bytes ([System.IO.File]::ReadAllBytes($target))
    $want = ([string]($pkg.files | Where-Object { $_.path -eq $p } | Select-Object -First 1).sha256).ToLowerInvariant()
    if ($got -ne $want) { throw "Verificación posterior falló: $p" }
  }

  $finalBuild = Get-Content -LiteralPath $buildPath -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($finalBuild.build -ne $ExpectedTargetBuild -or $finalBuild.channel -ne "RELEASE") {
    throw "La identidad final no coincide con el bootstrap."
  }

  Write-Host ""
  Write-Host "RESCATE OK" -ForegroundColor Green
  Write-Host "Build instalada: $($finalBuild.build)"
  Write-Host "Backup conservado: $backup"
  Write-Host "Ahora recargá la extensión desde chrome://extensions."
} catch {
  Write-Host "Falló la migración. Restaurando backup..." -ForegroundColor Red
  try {
    Get-ChildItem -LiteralPath $InstallPath -Force | Remove-Item -Recurse -Force
    Copy-Item -Path (Join-Path $backup "*") -Destination $InstallPath -Recurse -Force
    Write-Host "Rollback restaurado desde $backup" -ForegroundColor Yellow
  } catch {
    Write-Host "ATENCIÓN: el rollback automático también falló. No borres el backup: $backup" -ForegroundColor Red
  }
  throw
} finally {
  Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
}
