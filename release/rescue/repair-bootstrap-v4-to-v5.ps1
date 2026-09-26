param(
  [Parameter(Mandatory=$true)]
  [string]$InstallPath,

  # Sólo para CI/integración controlada. En uso normal descarga el target inmutable.
  [string]$PackagePath = ""
)

$ErrorActionPreference = "Stop"
$PackageUrl = "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/release/rescue/v1.3.25-bootstrap-release-v5-runtime-coherence-fix-package.json"
$PackageSha256 = "05eee4b9942eda3e98cc123f14bde0a16494c7f4bbffd9736044e2cc4c29ece2"

$ExpectedSourceVersion = "1.3.25"
$ExpectedSourceBuild = "1.3.25-bootstrap-release-v4-channel-fix"
$ExpectedSourceChannel = "RELEASE"
$ExpectedSourceIntegritySha256 = "bf4c79fd6971cd94379a936ca29c3c1c3545e9d137863d4f2bff2efeea76e568"

$ExpectedTargetVersion = "1.3.25"
$ExpectedTargetBuild = "1.3.25-bootstrap-release-v5-runtime-coherence-fix"
$ExpectedTargetChannel = "RELEASE"
$ExpectedModernPointer = "release/latest.json"

function Get-Sha256Bytes([byte[]]$Bytes) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace("-","").ToLowerInvariant()
  } finally {
    $sha.Dispose()
  }
}

function Assert-SafePath([string]$Path) {
  $root = @(
    "manifest.json","build.json","background.js","popup.html","popup.js",
    "icon128.png","integrity-manifest.json"
  )
  if ($root -contains $Path) { return }
  if ($Path -match '^js/[A-Za-z0-9._-]+\.js$') { return }
  throw "Ruta no autorizada en package: $Path"
}

function Read-JsonBytes([byte[]]$Bytes, [string]$Label) {
  try {
    return ([System.Text.Encoding]::UTF8.GetString($Bytes) | ConvertFrom-Json)
  } catch {
    throw "JSON inválido en $Label"
  }
}

$InstallPath = [System.IO.Path]::GetFullPath($InstallPath)
if (-not (Test-Path -LiteralPath $InstallPath -PathType Container)) {
  throw "La carpeta no existe: $InstallPath"
}

$manifestPath = Join-Path $InstallPath "manifest.json"
$buildPath = Join-Path $InstallPath "build.json"
$integrityPath = Join-Path $InstallPath "integrity-manifest.json"

foreach ($required in @($manifestPath,$buildPath,$integrityPath)) {
  if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
    throw "La carpeta no parece una instalación reparable de VIENA NOC Tools."
  }
}

$sourceManifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$sourceBuild = Get-Content -LiteralPath $buildPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (
  $sourceManifest.version -ne $ExpectedSourceVersion -or
  $sourceBuild.version -ne $ExpectedSourceVersion -or
  $sourceBuild.build -ne $ExpectedSourceBuild -or
  ([string]$sourceBuild.channel).ToUpperInvariant() -ne $ExpectedSourceChannel
) {
  throw "Esta reparación sólo se permite sobre $ExpectedSourceBuild. Detectado: v$($sourceManifest.version) / $($sourceBuild.build) / $($sourceBuild.channel)"
}

$sourceIntegrityBytes = [System.IO.File]::ReadAllBytes($integrityPath)
$sourceIntegritySha = Get-Sha256Bytes $sourceIntegrityBytes
if ($sourceIntegritySha -ne $ExpectedSourceIntegritySha256) {
  throw "El integrity-manifest del bootstrap v4 no coincide con el artifact auditado. SHA detectado: $sourceIntegritySha"
}
$sourceIntegrity = Read-JsonBytes $sourceIntegrityBytes "integrity-manifest.json"
if (
  $sourceIntegrity.version -ne $ExpectedSourceVersion -or
  $sourceIntegrity.build -ne $ExpectedSourceBuild -or
  ([string]$sourceIntegrity.channel).ToUpperInvariant() -ne $ExpectedSourceChannel
) {
  throw "La identidad del integrity-manifest fuente no coincide con bootstrap v4."
}

foreach ($prop in $sourceIntegrity.files.PSObject.Properties) {
  $p = [string]$prop.Name
  Assert-SafePath $p
  $full = Join-Path $InstallPath ($p -replace '/', [System.IO.Path]::DirectorySeparatorChar)
  if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
    throw "La instalación v4 está incompleta: falta $p"
  }
  $got = Get-Sha256Bytes ([System.IO.File]::ReadAllBytes($full))
  $want = ([string]$prop.Value).ToLowerInvariant()
  if ($got -ne $want) {
    throw "La instalación v4 fue modificada o está corrupta: $p"
  }
}

$temp = $null
$removeTemp = $false
if ([string]::IsNullOrWhiteSpace($PackagePath)) {
  $temp = Join-Path $env:TEMP ("viena-bootstrap-v5-" + [Guid]::NewGuid().ToString("N") + ".json")
  $removeTemp = $true
  Write-Host "Descargando reparación v5 verificada..."
  Invoke-WebRequest -Uri ($PackageUrl + "?_=" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) -OutFile $temp -UseBasicParsing
} else {
  $temp = [System.IO.Path]::GetFullPath($PackagePath)
  if (-not (Test-Path -LiteralPath $temp -PathType Leaf)) {
    throw "PackagePath no existe: $temp"
  }
  Write-Host "Usando package v5 local para validación controlada: $temp"
}

$backup = Join-Path (Split-Path -Parent $InstallPath) ((Split-Path -Leaf $InstallPath) + "_BACKUP_BEFORE_V5_" + (Get-Date -Format "yyyyMMdd_HHmmss_fff"))

try {
  $downloadBytes = [System.IO.File]::ReadAllBytes($temp)
  $downloadSha = Get-Sha256Bytes $downloadBytes
  if ($downloadSha -ne $PackageSha256) {
    throw "SHA-256 del package v5 incorrecto. Esperado $PackageSha256, obtenido $downloadSha"
  }

  $pkg = Read-JsonBytes $downloadBytes "package v5"
  if (
    $pkg.schema -ne 1 -or
    $pkg.app -ne "VIENA NOC Tools" -or
    $pkg.version -ne $ExpectedTargetVersion -or
    $pkg.build -ne $ExpectedTargetBuild -or
    ([string]$pkg.channel).ToUpperInvariant() -ne $ExpectedTargetChannel -or
    ([string]$pkg.mode) -ne "full"
  ) {
    throw "Identidad del package v5 inválida."
  }

  $patchCount = 0
  if ($null -ne $pkg.PSObject.Properties["patches"] -and $null -ne $pkg.patches) { $patchCount = [int]$pkg.patches.Count }
  $removeCount = 0
  if ($null -ne $pkg.PSObject.Properties["remove"] -and $null -ne $pkg.remove) { $removeCount = [int]$pkg.remove.Count }
  if ($patchCount -gt 0 -or $removeCount -gt 0) {
    throw "La reparación v5 no admite patches ni remove."
  }

  $seen = @{}
  $decoded = @{}
  $declaredHashes = @{}

  foreach ($item in $pkg.files) {
    $p = [string]$item.path
    Assert-SafePath $p
    if ($seen.ContainsKey($p)) { throw "Archivo duplicado: $p" }
    $seen[$p] = $true

    try { $bytes = [Convert]::FromBase64String([string]$item.content_base64) }
    catch { throw "Base64 inválido: $p" }

    if ($bytes.Length -ne [int64]$item.size) { throw "Tamaño inválido: $p" }
    $sha = Get-Sha256Bytes $bytes
    $want = ([string]$item.sha256).ToLowerInvariant()
    if ($sha -ne $want) { throw "SHA inválido: $p" }

    $decoded[$p] = $bytes
    $declaredHashes[$p] = $want
  }

  foreach ($required in @(
    "manifest.json","build.json","background.js","popup.html","popup.js",
    "icon128.png","integrity-manifest.json","js/80-update-banner.js","js/90-runtime-status.js"
  )) {
    if (-not $decoded.ContainsKey($required)) { throw "Falta archivo requerido: $required" }
  }

  $targetManifest = Read-JsonBytes $decoded["manifest.json"] "manifest.json"
  $targetBuild = Read-JsonBytes $decoded["build.json"] "build.json"
  $targetIntegrity = Read-JsonBytes $decoded["integrity-manifest.json"] "integrity-manifest.json"

  if ($targetManifest.version -ne $ExpectedTargetVersion) { throw "manifest.json no coincide con la versión objetivo." }
  if (
    $targetBuild.version -ne $ExpectedTargetVersion -or
    $targetBuild.build -ne $ExpectedTargetBuild -or
    ([string]$targetBuild.channel).ToUpperInvariant() -ne $ExpectedTargetChannel
  ) { throw "build.json no coincide con la identidad objetivo." }
  if (
    $targetIntegrity.version -ne $ExpectedTargetVersion -or
    $targetIntegrity.build -ne $ExpectedTargetBuild -or
    ([string]$targetIntegrity.channel).ToUpperInvariant() -ne $ExpectedTargetChannel
  ) { throw "integrity-manifest.json no coincide con la identidad objetivo." }
  if ([int]$targetBuild.updater_contract -lt 2) { throw "El target perdió updater_contract >= 2." }
  if ([string]$targetBuild.release_compatibility_floor -ne "1.3.24") { throw "El target perdió release_compatibility_floor=1.3.24." }
  if ([string]$targetBuild.update_channel -ne $ExpectedModernPointer) { throw "El target no usa release/latest.json." }

  $backgroundText = [System.Text.Encoding]::UTF8.GetString($decoded["background.js"])
  $runtimeStatusText = [System.Text.Encoding]::UTF8.GetString($decoded["js/90-runtime-status.js"])
  $updateBannerText = [System.Text.Encoding]::UTF8.GetString($decoded["js/80-update-banner.js"])
  if ($backgroundText -notlike "*const VIENA_BUILD_ID = '$ExpectedTargetBuild'*") { throw "background.js no lleva el build v5 esperado." }
  if ($runtimeStatusText -notlike "*const BUILD_ID = '$ExpectedTargetBuild'*") { throw "runtime-status no lleva el build v5 esperado." }
  if ($updateBannerText -notlike "*const CONTENT_BUILD_ID='$ExpectedTargetBuild'*") { throw "update-banner no lleva el build v5 esperado." }

  $integritySeen = @{}
  foreach ($prop in $targetIntegrity.files.PSObject.Properties) {
    $p = [string]$prop.Name
    $want = ([string]$prop.Value).ToLowerInvariant()
    Assert-SafePath $p
    if (-not $decoded.ContainsKey($p)) { throw "Integrity referencia archivo ausente: $p" }
    if ((Get-Sha256Bytes $decoded[$p]) -ne $want) { throw "Integrity mismatch: $p" }
    $integritySeen[$p] = $true
  }
  foreach ($p in $decoded.Keys) {
    if ($p -eq "integrity-manifest.json") { continue }
    if (-not $integritySeen.ContainsKey($p)) { throw "Archivo fuera del inventario de integridad: $p" }
  }

  Write-Host "Bootstrap v4 verificado completamente."
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
      if ($got -ne [string]$declaredHashes[$p]) { throw "Verificación posterior falló: $p" }
    }

    $finalBuild = Get-Content -LiteralPath $buildPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (
      $finalBuild.version -ne $ExpectedTargetVersion -or
      $finalBuild.build -ne $ExpectedTargetBuild -or
      ([string]$finalBuild.channel).ToUpperInvariant() -ne $ExpectedTargetChannel
    ) { throw "La identidad final no coincide con v5." }

    Write-Host ""
    Write-Host "REPARACION V4 -> V5 OK" -ForegroundColor Green
    Write-Host "Build instalada: $($finalBuild.build)"
    Write-Host "Canal siguiente: $ExpectedModernPointer"
    Write-Host "Backup conservado: $backup"
    Write-Host "Ahora recargá la extensión desde chrome://extensions."
  } catch {
    Write-Host "Falló la reparación. Restaurando backup..." -ForegroundColor Red
    try {
      Get-ChildItem -LiteralPath $InstallPath -Force | Remove-Item -Recurse -Force
      Copy-Item -Path (Join-Path $backup "*") -Destination $InstallPath -Recurse -Force
      Write-Host "Rollback restaurado desde $backup" -ForegroundColor Yellow
    } catch {
      Write-Host "ATENCIÓN: el rollback automático también falló. No borres el backup: $backup" -ForegroundColor Red
    }
    throw
  }
} finally {
  if ($removeTemp -and $temp) { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}
