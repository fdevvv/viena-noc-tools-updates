param(
  [Parameter(Mandatory=$true)]
  [string]$InstallPath,

  # Sólo para validación/integración controlada. En uso normal se descarga el
  # bootstrap inmutable desde GitHub y se verifica contra PackageSha256.
  [string]$PackagePath = ""
)

$ErrorActionPreference = "Stop"
$PackageUrl = "https://raw.githubusercontent.com/fdevvv/viena-noc-tools-updates/refs/heads/main/release/v1.3.25-bootstrap-v3-package.json"
$PackageSha256 = "c1ecc7dbf7f5deca115ee6a05e1dce598aca9c1b94e940ce7691e444152a65f5"
$ExpectedSourceVersion = "1.3.25"
$ExpectedSourceBuild = "1.3.25-release"
$ExpectedSourceChannel = "RELEASE"
$AllowedSourceUpdaterSha256 = @(
  "8c7f72f1f25aae048bbb82024384797b359c03fce4fb5a493eee92bf98309f7f",
  "a83d37f077e466ac9591eee48cf52dcdacb62fe264be3476eba65616763d61f4"
)
$ExpectedTargetVersion = "1.3.25"
$ExpectedTargetBuild = "1.3.25-bootstrap-release-v3"
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
$sourceUpdaterPath = Join-Path $InstallPath (Join-Path "js" "95-local-updater.js")

if (-not (Test-Path -LiteralPath $manifestPath) -or -not (Test-Path -LiteralPath $buildPath)) {
  throw "La carpeta no parece una instalación de VIENA NOC Tools."
}
if (-not (Test-Path -LiteralPath $sourceUpdaterPath -PathType Leaf)) {
  throw "No se encontró el updater histórico a verificar."
}

$sourceManifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$sourceBuild = Get-Content -LiteralPath $buildPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (
  $sourceManifest.version -ne $ExpectedSourceVersion -or
  $sourceBuild.version -ne $ExpectedSourceVersion -or
  $sourceBuild.build -ne $ExpectedSourceBuild -or
  ([string]$sourceBuild.channel).ToUpperInvariant() -ne $ExpectedSourceChannel
) {
  throw "Este rescate sólo se permite sobre RELEASE $ExpectedSourceVersion / $ExpectedSourceBuild. Detectado: v$($sourceManifest.version) / $($sourceBuild.build) / $($sourceBuild.channel)"
}

$sourceUpdaterBytes = [System.IO.File]::ReadAllBytes($sourceUpdaterPath)
$sourceUpdaterSha = Get-Sha256Bytes $sourceUpdaterBytes
if ($AllowedSourceUpdaterSha256 -notcontains $sourceUpdaterSha) {
  throw "Updater histórico no reconocido. SHA-256 detectado: $sourceUpdaterSha"
}

$temp = $null
$removeTemp = $false
if ([string]::IsNullOrWhiteSpace($PackagePath)) {
  $temp = Join-Path $env:TEMP ("viena-bootstrap-" + [Guid]::NewGuid().ToString("N") + ".json")
  $removeTemp = $true
  Write-Host "Descargando bootstrap verificado..."
  Invoke-WebRequest -Uri ($PackageUrl + "?_=" + [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) -OutFile $temp -UseBasicParsing
} else {
  $temp = [System.IO.Path]::GetFullPath($PackagePath)
  if (-not (Test-Path -LiteralPath $temp -PathType Leaf)) {
    throw "PackagePath no existe: $temp"
  }
  Write-Host "Usando bootstrap local para validación controlada: $temp"
}

$backup = Join-Path (Split-Path -Parent $InstallPath) ((Split-Path -Leaf $InstallPath) + "_BACKUP_" + (Get-Date -Format "yyyyMMdd_HHmmss_fff"))

try {
  $downloadBytes = [System.IO.File]::ReadAllBytes($temp)
  $downloadSha = Get-Sha256Bytes $downloadBytes
  if ($downloadSha -ne $PackageSha256) {
    throw "SHA-256 del package incorrecto. Esperado $PackageSha256, obtenido $downloadSha"
  }

  $pkg = [System.Text.Encoding]::UTF8.GetString($downloadBytes) | ConvertFrom-Json
  if (
    $pkg.schema -ne 1 -or
    $pkg.app -ne "VIENA NOC Tools" -or
    $pkg.version -ne $ExpectedTargetVersion -or
    $pkg.build -ne $ExpectedTargetBuild -or
    ([string]$pkg.channel).ToUpperInvariant() -ne $ExpectedTargetChannel -or
    ([string]$pkg.mode) -ne "full"
  ) {
    throw "Identidad del bootstrap inválida."
  }

  $patchCount = 0
  if ($null -ne $pkg.PSObject.Properties["patches"] -and $null -ne $pkg.patches) {
    $patchCount = [int]$pkg.patches.Count
  }
  $removeCount = 0
  if ($null -ne $pkg.PSObject.Properties["remove"] -and $null -ne $pkg.remove) {
    $removeCount = [int]$pkg.remove.Count
  }
  if ($patchCount -gt 0 -or $removeCount -gt 0) {
    throw "El bootstrap de rescate no puede contener patches ni remove."
  }

  $seen = @{}
  $decoded = @{}
  $declaredHashes = @{}

  foreach ($item in $pkg.files) {
    $p = [string]$item.path
    Assert-SafePath $p
    if ($seen.ContainsKey($p)) {
      throw "Archivo duplicado: $p"
    }
    $seen[$p] = $true

    try {
      $bytes = [Convert]::FromBase64String([string]$item.content_base64)
    } catch {
      throw "Base64 inválido: $p"
    }

    if ($bytes.Length -ne [int64]$item.size) {
      throw "Tamaño inválido: $p"
    }

    $sha = Get-Sha256Bytes $bytes
    $want = ([string]$item.sha256).ToLowerInvariant()
    if ($sha -ne $want) {
      throw "SHA inválido: $p"
    }

    $decoded[$p] = $bytes
    $declaredHashes[$p] = $want
  }

  foreach ($required in @("manifest.json","build.json","background.js","popup.html","popup.js","icon128.png","integrity-manifest.json")) {
    if (-not $decoded.ContainsKey($required)) {
      throw "Falta archivo requerido: $required"
    }
  }

  $targetManifest = Read-JsonBytes $decoded["manifest.json"] "manifest.json"
  $targetBuild = Read-JsonBytes $decoded["build.json"] "build.json"
  $targetIntegrity = Read-JsonBytes $decoded["integrity-manifest.json"] "integrity-manifest.json"

  if ($targetManifest.version -ne $ExpectedTargetVersion) {
    throw "manifest.json no coincide con la versión objetivo."
  }
  if (
    $targetBuild.version -ne $ExpectedTargetVersion -or
    $targetBuild.build -ne $ExpectedTargetBuild -or
    ([string]$targetBuild.channel).ToUpperInvariant() -ne $ExpectedTargetChannel
  ) {
    throw "build.json no coincide con la identidad objetivo."
  }
  if (
    $targetIntegrity.version -ne $ExpectedTargetVersion -or
    $targetIntegrity.build -ne $ExpectedTargetBuild -or
    ([string]$targetIntegrity.channel).ToUpperInvariant() -ne $ExpectedTargetChannel
  ) {
    throw "integrity-manifest.json no coincide con la identidad objetivo."
  }
  if ([int]$targetBuild.updater_contract -lt 2) {
    throw "El bootstrap objetivo no tiene updater_contract >= 2."
  }
  if ([string]$targetBuild.release_compatibility_floor -ne "1.3.24") {
    throw "El bootstrap objetivo perdió release_compatibility_floor=1.3.24."
  }
  if ([string]$targetBuild.update_channel -ne $ExpectedModernPointer) {
    throw "El bootstrap objetivo no apunta al canal moderno esperado."
  }

  $backgroundText = [System.Text.Encoding]::UTF8.GetString($decoded["background.js"])
  $popupText = [System.Text.Encoding]::UTF8.GetString($decoded["popup.js"])
  if ($backgroundText -notlike "*$ExpectedModernPointer*" -or $popupText -notlike "*$ExpectedModernPointer*") {
    throw "El bootstrap objetivo no usa release/latest.json en background/popup."
  }

  if ($null -eq $targetIntegrity.files) {
    throw "integrity-manifest.json no contiene inventario."
  }

  $integritySeen = @{}
  foreach ($prop in $targetIntegrity.files.PSObject.Properties) {
    $p = [string]$prop.Name
    $want = ([string]$prop.Value).ToLowerInvariant()
    Assert-SafePath $p
    if (-not $decoded.ContainsKey($p)) {
      throw "Integrity referencia archivo ausente: $p"
    }
    if ((Get-Sha256Bytes $decoded[$p]) -ne $want) {
      throw "Integrity mismatch: $p"
    }
    $integritySeen[$p] = $true
  }

  foreach ($p in $decoded.Keys) {
    if ($p -eq "integrity-manifest.json") { continue }
    if (-not $integritySeen.ContainsKey($p)) {
      throw "Archivo fuera del inventario de integridad: $p"
    }
  }

  Write-Host "Fuente histórica verificada: $sourceUpdaterSha"
  Write-Host "Creando backup completo en: $backup"
  Copy-Item -LiteralPath $InstallPath -Destination $backup -Recurse

  $identityLast = @("manifest.json","integrity-manifest.json","build.json")
  $normal = @($decoded.Keys | Where-Object { $identityLast -notcontains $_ } | Sort-Object)
  $order = @($normal + $identityLast)

  try {
    foreach ($p in $order) {
      $target = Join-Path $InstallPath ($p -replace '/', [System.IO.Path]::DirectorySeparatorChar)
      $dir = Split-Path -Parent $target
      if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
      }

      $tmpTarget = $target + ".viena-new"
      [System.IO.File]::WriteAllBytes($tmpTarget, $decoded[$p])
      Move-Item -LiteralPath $tmpTarget -Destination $target -Force
    }

    foreach ($p in $decoded.Keys) {
      $target = Join-Path $InstallPath ($p -replace '/', [System.IO.Path]::DirectorySeparatorChar)
      $got = Get-Sha256Bytes ([System.IO.File]::ReadAllBytes($target))
      $want = [string]$declaredHashes[$p]
      if ($got -ne $want) {
        throw "Verificación posterior falló: $p"
      }
    }

    $finalManifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $finalBuild = Get-Content -LiteralPath $buildPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (
      $finalManifest.version -ne $ExpectedTargetVersion -or
      $finalBuild.version -ne $ExpectedTargetVersion -or
      $finalBuild.build -ne $ExpectedTargetBuild -or
      ([string]$finalBuild.channel).ToUpperInvariant() -ne $ExpectedTargetChannel
    ) {
      throw "La identidad final no coincide con el bootstrap."
    }

    Write-Host ""
    Write-Host "RESCATE OK" -ForegroundColor Green
    Write-Host "Origen validado: $ExpectedSourceBuild / updater $sourceUpdaterSha"
    Write-Host "Build instalada: $($finalBuild.build)"
    Write-Host "Canal siguiente: $ExpectedModernPointer"
    Write-Host "Backup conservado: $backup"
    Write-Host "Ahora recargá la extensión desde chrome://extensions."
  } catch {
    Write-Host "Falló la migración. Restaurando backup..." -ForegroundColor Red
    try {
      Get-ChildItem -LiteralPath $InstallPath -Force | Remove-Item -Recurse -Force
      Copy-Item -Path (Join-Path $backup "*") -Destination $InstallPath -Recurse -Force
      Write-Host "Rollback restaurado desde $backup" -ForegroundColor Yellow
    } catch {
      Write-Host "ATENCIÓN: el Rollback automático también falló. No borres el backup: $backup" -ForegroundColor Red
    }
    throw
  }
} finally {
  if ($removeTemp -and $temp) {
    Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
  }
}
