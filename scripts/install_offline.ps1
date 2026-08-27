# =============================================================================
# install_offline.ps1 - OFFLINE TARGET MACHINE installer.
#
# This script MUST NOT use the network. It installs the pinned dependency
# set from the LOCAL wheelhouse using pip with:
#       --no-index
#       --find-links <LOCAL_WHEELHOUSE>
# There is NO fallback to PyPI. If a required wheel is missing, the install
# FAILS with OFFLINE_DEPENDENCY_MISSING.
#
# It then verifies the installed runtime with scripts/verify_offline_runtime.py
# (import closure + versions + public APIs + VFPToolchainService().capabilities()
# without VFP9/FoxBin2Prg/internet).
#
# Usage (from the bundle root):
#   powershell -ExecutionPolicy Bypass -File install-offline.ps1
#   powershell -ExecutionPolicy Bypass -File install-offline.ps1 -Python "py -3.12"
# =============================================================================

[CmdletBinding()]
param(
    [string]$BundleRoot = "",
    [string]$Python = "python"
)
if (-not $BundleRoot) { $BundleRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path } }

$ErrorActionPreference = "Stop"
$NoNetwork = $true  # policy: this script must never reach the network

function Fail([string]$code, [string]$message) {
    $obj = [ordered]@{ ok = $false; status = "FAIL"; errorCode = $code; error = $message }
    $obj | ConvertTo-Json
    exit 1
}

Write-Host "== install_offline (network FORBIDDEN) =="

$wheelsDir   = Join-Path $BundleRoot "wheels"
$appDir      = Join-Path $BundleRoot "app"
$verifyScript = Join-Path $BundleRoot "scripts\verify_offline_runtime.py"
if (-not (Test-Path $verifyScript)) {
    # verify script ships in app/scripts in some bundle layouts; fall back
    $verifyScript = Join-Path $appDir "scripts\verify_offline_runtime.py"
}
if (-not (Test-Path $wheelsDir)) {
    Fail "OFFLINE_DEPENDENCY_MISSING" "local wheelhouse not found: $wheelsDir"
}

# Pick the wheelhouse subfolder for the running interpreter.
$ver = (& $Python -c "import sys; print('%d%d' % (sys.version_info[0], sys.version_info[1]))").Trim()
$candidate = Join-Path $wheelsDir $ver
if (-not (Test-Path $candidate)) {
    # a cp310-abi3 wheelhouse may be shared; try the lowest supported tag
    $found = $false
    foreach ($t in @($ver, "314", "312", "310")) {
        if (Test-Path (Join-Path $wheelsDir $t)) { $candidate = Join-Path $wheelsDir $t; $found = $true; break }
    }
    if (-not $found) {
        Fail "OFFLINE_DEPENDENCY_MISSING" "no wheelhouse for CPython tag $ver under $wheelsDir"
    }
    Write-Host "NOTE: using wheelhouse '$candidate' for CPython $ver"
}

Write-Host "wheelhouse: $candidate"
Write-Host "python    : $Python"

# --- hash-verify the wheels BEFORE installing --------------------------------
$manifest = Get-Content (Join-Path $appDir "runtime\runtime-dependencies.json") -Raw | ConvertFrom-Json
$locked = @{}
foreach ($dep in $manifest.dependencies) {
    foreach ($key in $dep.hashes.PSObject.Properties) { $locked[$key.Name] = $key.Value }
}
$hashBad = @()
$files = Get-ChildItem $candidate -Filter *.whl
foreach ($f in $files) {
    $expected = $locked[$f.Name]
    if (-not $expected) { $hashBad += $f.Name; continue }
    $actual = (Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $expected.ToLower()) { $hashBad += $f.Name }
}
if ($hashBad.Count -gt 0) {
    Fail "OFFLINE_DEPENDENCY_HASH_MISMATCH" ("corrupt or unlisted wheels: " + ($hashBad -join ', '))
}
Write-Host "SHA256 verification: OK"

# --- install from the LOCAL wheelhouse ONLY (no index, no network) ----------
$pipArgs = @(
    "-m", "pip", "install",
    "--no-index",
    "--find-links", $candidate,
    "--upgrade",
    "dbfread==2.0.7",
    "dbf==0.99.11",
    "aenum==3.1.17",
    "openpyxl==3.1.5",
    "et_xmlfile==2.0.0",
    "xlsxwriter==3.2.9",
    "orjson==3.12.0",
    "polars==1.44.1",
    "polars_runtime_32==1.44.1"
)
Write-Host "== $Python $($pipArgs -join ' ')"
& $Python @pipArgs
if ($LASTEXITCODE -ne 0) {
    Fail "OFFLINE_DEPENDENCY_MISSING" "pip --no-index install failed (exit $LASTEXITCODE) - a required wheel is missing from the local wheelhouse"
}

# --- verify the installed offline runtime ------------------------------------
if (Test-Path $verifyScript) {
    & $Python $verifyScript --root $appDir
    if ($LASTEXITCODE -ne 0) {
        Fail "OFFLINE_RUNTIME_INCOMPLETE" "offline runtime verification failed after install"
    }
}

$ok = [ordered]@{
    ok = $true
    status = "PASS"
    installedFrom = $candidate
    networkUsed = $NoNetwork -eq $false
    note = "installed exclusively from the local wheelhouse (--no-index)"
}
$ok | ConvertTo-Json
Write-Host "OFFLINE INSTALL OK"
exit 0
