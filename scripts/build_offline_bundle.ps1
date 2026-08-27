# =============================================================================
# build_offline_bundle.ps1 - MAINTAINER / BUILD MACHINE tool.
#
# Network use here is ALLOWED (this is the build-time plane). It produces a
# self-contained offline bundle under dist/ that a machine WITHOUT internet
# can install from, using ONLY scripts/install_offline.ps1.
#
# Steps:
#   1. resolve the locked dependency set (runtime/runtime-dependencies.json)
#   2. download exactly the pinned wheels for the target Python(s), Windows
#   3. verify SHA256 of every wheel against the lock manifest
#   4. copy the toolchain runtime (src/, tools/dbfbridge, tools/dbf_anonymizer)
#   5. copy knowledge files (config.json, docs, language)
#   6. write the bundle manifest (wheels + vendored tree SHA256s)
#   7. emit the final offline bundle layout:
#        dist/mcp-vfp9sp2-toolchain-offline/
#            app/
#            wheels/
#            knowledge/
#            manifests/
#            install-offline.ps1
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\build_offline_bundle.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\build_offline_bundle.ps1 -PythonVersions 3.10,3.12
#
# This script is NEVER run by the offline target machine.
# =============================================================================

[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string[]]$PythonVersions = @("3.10", "3.12", "3.14"),
    [string]$DistDir = "",
    [string]$PyExe = "py"
)
if (-not $RepoRoot) {
    if ($PSScriptRoot) {
        $RepoRoot = Split-Path -Parent $PSScriptRoot
    } else {
        $RepoRoot = (Get-Location).Path
    }
}
if (-not $DistDir) { $DistDir = Join-Path $RepoRoot "dist" }

$ErrorActionPreference = "Stop"
$BundleName = "mcp-vfp9sp2-toolchain-offline"
$BundleDir  = Join-Path $DistDir $BundleName

function Fail([string]$code, [string]$message) {
    $obj = [ordered]@{ ok = $false; status = "FAIL"; errorCode = $code; error = $message }
    $obj | ConvertTo-Json
    exit 1
}

Write-Host "== build_offline_bundle =="
Write-Host "repo root   : $RepoRoot"
Write-Host "pythons     : $($PythonVersions -join ', ')"
Write-Host "bundle dir  : $BundleDir"

# --- 0. prerequisites (maintainer machine) ----------------------------------
if (-not (Get-Command $PyExe -ErrorAction SilentlyContinue)) {
    Fail "OFFLINE_DEPENDENCY_MISSING" "python launcher '$PyExe' not found on build machine"
}
$manifestPath = Join-Path $RepoRoot "runtime\runtime-dependencies.json"
if (-not (Test-Path $manifestPath)) {
    Fail "OFFLINE_DEPENDENCY_MISSING" "lock manifest not found: $manifestPath"
}

# --- 1. clean staging --------------------------------------------------------
if (Test-Path $BundleDir) { Remove-Item $BundleDir -Recurse -Force }
$appDir     = Join-Path $BundleDir "app"
$wheelsDir  = Join-Path $BundleDir "wheels"
$knowledge  = Join-Path $BundleDir "knowledge"
$manifests  = Join-Path $BundleDir "manifests"
foreach ($d in @($appDir, $wheelsDir, $knowledge, $manifests)) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}
foreach ($py in $PythonVersions) {
    New-Item -ItemType Directory -Path (Join-Path $wheelsDir ($py -replace '\.', '')) -Force | Out-Null
}

# --- 2. download exactly the pinned wheels ----------------------------------
$specs = @(
    "dbfread==2.0.7"
    "dbf==0.99.11"
    "aenum==3.1.17"
    "openpyxl==3.1.5"
    "et_xmlfile==2.0.0"
    "xlsxwriter==3.2.9"
    "orjson==3.12.0"
    "polars==1.44.1"
    "polars_runtime_32==1.44.1"
)

$lock = Get-Content $manifestPath -Raw | ConvertFrom-Json
$lockedHashes = @{}
foreach ($dep in $lock.dependencies) {
    foreach ($key in $dep.hashes.PSObject.Properties) {
        $lockedHashes[$key.Name] = $key.Value
    }
}

foreach ($py in $PythonVersions) {
    $pyTag  = $py -replace '\.', ''     # 310 / 312 / 314
    $target = Join-Path $wheelsDir $pyTag
    Write-Host "== $PyExe -3.14 -m pip download for py$py =="
    $pyArgs = @(
        "-m", "pip", "download"
    ) + $specs + @(
        "--only-binary=:all:",
        "--python-version", $pyTag,
        "--platform", "win_amd64",
        "--implementation", "cp",
        "--abi", "cp$pyTag",
        "--abi", "cp310",
        "--abi", "abi3",
        "--abi", "none",
        "-d", $target,
        "-q"
    )
    & $PyExe -3.14 @pyArgs
    if ($LASTEXITCODE -ne 0) {
        Fail "OFFLINE_DEPENDENCY_MISSING" "pip download failed for python $py (exit $LASTEXITCODE)"
    }
}

# --- 3. verify SHA256 of every downloaded wheel against the lock ------------
$hashFailures = @()
foreach ($py in $PythonVersions) {
    $pyTag = $py -replace '\.', ''
    $target = Join-Path $wheelsDir $pyTag
    foreach ($file in Get-ChildItem $target -Filter *.whl) {
        $expected = $lockedHashes[$file.Name]
        if (-not $expected) {
            $hashFailures += [ordered]@{ file = $file.Name; problem = "not in lock manifest" }
            continue
        }
        $actual = (Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower()
        if ($actual -ne $expected.ToLower()) {
            $hashFailures += [ordered]@{ file = $file.Name; problem = "hash mismatch"; expected = $expected; actual = $actual }
        }
    }
}
if ($hashFailures.Count -gt 0) {
    Fail "OFFLINE_DEPENDENCY_HASH_MISMATCH" ($hashFailures | ConvertTo-Json -Depth 4)
}
Write-Host "SHA256 verification: OK (all wheels match the lock manifest)"

# --- 4. copy the toolchain runtime ------------------------------------------
# The core service imports first-party root modules (vfp_protocol, vfp_common,
# vfp_safety, vfp_dbf_export, ...) — the full runtime closure must ship.
Copy-Item -Recurse -Force (Join-Path $RepoRoot "src") (Join-Path $appDir "src")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "vfp_driver.py") (Join-Path $appDir "vfp_driver.py")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "vfp_protocol.py") (Join-Path $appDir "vfp_protocol.py")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "vfp_common.py") (Join-Path $appDir "vfp_common.py")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "vfp_safety.py") (Join-Path $appDir "vfp_safety.py")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "vfp_dbf_export.py") (Join-Path $appDir "vfp_dbf_export.py")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "vfp_encoding.py") (Join-Path $appDir "vfp_encoding.py")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "vfp_indexer.py") (Join-Path $appDir "vfp_indexer.py")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "vfp_cdx.py") (Join-Path $appDir "vfp_cdx.py")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "vfp_audit.py") (Join-Path $appDir "vfp_audit.py")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "conftest.py") (Join-Path $appDir "conftest.py")
New-Item -ItemType Directory -Path (Join-Path $appDir "tools") -Force | Out-Null
Copy-Item -Recurse -Force (Join-Path $RepoRoot "tools\dbfbridge") (Join-Path $appDir "tools\dbfbridge")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "tools\dbf_anonymizer") (Join-Path $appDir "tools\dbf_anonymizer")
Copy-Item -Force (Join-Path $RepoRoot "tools\VENDORED_DEPENDENCIES.json") (Join-Path $appDir "tools\VENDORED_DEPENDENCIES.json")
New-Item -ItemType Directory -Path (Join-Path $appDir "runtime") -Force | Out-Null
Copy-Item -Force $manifestPath (Join-Path $appDir "runtime\runtime-dependencies.json")
New-Item -ItemType Directory -Path (Join-Path $appDir "tests") -Force | Out-Null
Copy-Item -Recurse -Force (Join-Path $RepoRoot "tests") (Join-Path $appDir "tests")

# --- 5. copy knowledge files --------------------------------------------------
Copy-Item -Force (Join-Path $RepoRoot "config.json") (Join-Path $knowledge "config.json")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "docs") (Join-Path $knowledge "docs")
if (Test-Path (Join-Path $RepoRoot "language")) {
    Copy-Item -Recurse -Force (Join-Path $RepoRoot "language") (Join-Path $knowledge "language")
}
Copy-Item -Force (Join-Path $RepoRoot "README.md") (Join-Path $knowledge "README.md")
Copy-Item -Force (Join-Path $RepoRoot "THANKS.md") (Join-Path $knowledge "THANKS.md")

# --- 6. write the bundle manifest (wheels + vendored tree hashes) ------------
function Tree-SHA256([string]$dir) {
    # Deterministic tree digest: sorted "relpath sha256" lines -> SHA256.
    $files = Get-ChildItem $dir -Recurse -File | Sort-Object -Property FullName
    $lines = foreach ($f in $files) {
        $rel = $f.FullName.Substring($dir.Length).TrimStart('\').Replace('\', '/')
        "{0} {1}" -f $rel, ((Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower())
    }
    $text = ($lines -join "`n") + "`n"
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
    $alg = [System.Security.Cryptography.SHA256]::Create()
    $hash = $alg.ComputeHash($bytes)
    return ([System.BitConverter]::ToString($hash).ToLower() -replace '-', '')
}

$bundleManifest = [ordered]@{
    schemaVersion = 2
    bundle = $BundleName
    builtAt = (Get-Date).ToString("o")
    pythonVersions = $PythonVersions
    targetPlatform = "windows"
    networkRequiredAtRuntime = $false
    app = [ordered]@{
        dbfbridgeTreeSha256  = (Tree-SHA256 (Join-Path $appDir "tools\dbfbridge"))
        dbfAnonymizerTreeSha256 = (Tree-SHA256 (Join-Path $appDir "tools\dbf_anonymizer"))
    }
    wheels = @{}
}
foreach ($py in $PythonVersions) {
    $pyTag = $py -replace '\.', ''
    $w = @{}
    foreach ($file in Get-ChildItem (Join-Path $wheelsDir $pyTag) -Filter *.whl) {
        $w[$file.Name] = (Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower()
    }
    $bundleManifest.wheels[$pyTag] = $w
}
$bundleManifest | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $manifests "bundle-manifest.json") -Encoding UTF8

# --- 7. copy the offline installer + verifier into the bundle ----------------
Copy-Item (Join-Path $RepoRoot "scripts\install_offline.ps1") (Join-Path $BundleDir "install-offline.ps1")
New-Item -ItemType Directory -Path (Join-Path $BundleDir "scripts") -Force | Out-Null
Copy-Item (Join-Path $RepoRoot "scripts\verify_offline_runtime.py") (Join-Path $BundleDir "scripts\verify_offline_runtime.py")

# --- done ---------------------------------------------------------------------
$summary = [ordered]@{
    ok = $true
    status = "PASS"
    bundle = $BundleDir
    wheels = ($bundleManifest.wheels | ConvertTo-Json -Depth 4)
    note = "SHA256-verified against runtime/runtime-dependencies.json"
}
$summary | ConvertTo-Json -Depth 6
Write-Host "OFFLINE BUNDLE READY: $BundleDir"
exit 0
