# =============================================================================
# install_offline.ps1 - OFFLINE TARGET MACHINE installer.
#
# This script MUST NOT use the network. It installs the pinned dependency
# set from the LOCAL wheelhouse using pip with:
#       --no-index
#       --find-links <LOCAL_WHEELHOUSE>
# There is NO fallback to PyPI. If a required wheel is missing, the install
# FAILS with OFFLINE_DEPENDENCY_MISSING (it never "tries the internet").
#
# Interpreter selection is EXACT and fail-closed:
#   3.10 -> wheels/310      3.12 -> wheels/312      3.14 -> wheels/314
# A missing exact-tag wheelhouse is OFFLINE_DEPENDENCY_MISSING - the
# installer NEVER substitutes a different interpreter directory (ABI-specific
# wheels make that unsafe).
#
# Python invocation is unambiguous (separated executable + launcher args,
# safe with spaces in paths):
#   -PythonExe python
#   -PythonExe py -PythonArgs "-3.12"
#   -PythonExe "C:\Program Files\Python 3.12\python.exe"
#
# Usage (from the bundle root):
#   powershell -ExecutionPolicy Bypass -File install-offline.ps1
#   powershell -ExecutionPolicy Bypass -File install-offline.ps1 -PythonExe py -PythonArgs "-3.12"
# =============================================================================

[CmdletBinding()]
param(
    [string]$BundleRoot = "",
    [string]$PythonExe = "python",
    [string[]]$PythonArgs = @(),
    [switch]$AlsoTestRunner
)
if (-not $BundleRoot) {
    $BundleRoot = if ($PSScriptRoot) { $PSScriptRoot } else { (Get-Location).Path }
}
$ErrorActionPreference = "Stop"

function Fail([string]$code, [string]$message) {
    $obj = [ordered]@{ ok = $false; status = "FAIL"; errorCode = $code; error = $message }
    $obj | ConvertTo-Json
    exit 1
}

function Invoke-Python([string[]]$PyArgs) {
    # Single, unambiguous invocation helper (handles spaces in paths).
    # Returns ONLY the numeric exit code. The child process stdout/stderr are
    # routed to the console (Out-Host) so they never pollute the function's
    # return value (a native command's output would otherwise be captured as
    # pipeline objects and returned alongside the exit code).
    & $PythonExe @PythonArgs @PyArgs 2>&1 | Out-Host
    if ($LASTEXITCODE -eq $null) { return 0 }
    return [int]$LASTEXITCODE
}

Write-Host "== install_offline (network FORBIDDEN) =="
Write-Host "bundle    : $BundleRoot"
Write-Host "python    : '$PythonExe' $($PythonArgs -join ' ')"

$wheelsDir  = Join-Path $BundleRoot "wheels"
$testWheels = Join-Path $BundleRoot "test-wheels"
$appDir     = Join-Path $BundleRoot "app"
if (-not (Test-Path $wheelsDir))  { Fail "OFFLINE_DEPENDENCY_MISSING" "local wheelhouse not found: $wheelsDir" }
if (-not (Test-Path $appDir))    { Fail "OFFLINE_DEPENDENCY_MISSING" "bundle app/ not found: $appDir" }

# --- exact interpreter tag (fail-closed, no substitution) --------------------
$verLine = (& $PythonExe @PythonArgs -c "import sys; print('%d%d' % (sys.version_info[0], sys.version_info[1]))").Trim()
$ver = $verLine | Select-Object -Last 1
if ($ver -notmatch '^\d{3}$') {
    Fail "OFFLINE_DEPENDENCY_RESOLUTION_ERROR" "could not determine the target interpreter tag (got: '$ver')"
}
$exactTagDir = Join-Path $wheelsDir $ver
if (-not (Test-Path $exactTagDir)) {
    Fail "OFFLINE_DEPENDENCY_MISSING" "no wheelhouse for CPython tag '$ver' (required: $exactTagDir). Exact-tag policy: the installer never substitutes another interpreter directory."
}
Write-Host "wheelhouse: $exactTagDir (exact tag $ver)"

# --- load the lock manifest ---------------------------------------------------
$manifestPath = Join-Path $appDir "runtime\runtime-dependencies.json"
if (-not (Test-Path $manifestPath)) { Fail "OFFLINE_RUNTIME_INCOMPLETE" "lock manifest not found in app/: $manifestPath" }
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
$locked = @{}
foreach ($dep in $manifest.dependencies) {
    foreach ($key in $dep.hashes.PSObject.Properties) { $locked[$key.Name] = $key.Value }
}

# --- REQUIRED-SET verification (fail-closed) ---------------------------------
# 1) every locked wheel that applies to this tag must be present,
# 2) every present wheel must be listed in the lock with a matching SHA256,
# 3) unlisted wheels are a failure (a locked set is a locked set).
function Wheel-MatchesTag([string]$filename, [string]$tag) {
    $base = [IO.Path]::GetFileNameWithoutExtension($filename)
    $parts = $base.Split('-')
    if ($parts.Length -lt 5) { return $false }
    $pyTags  = $parts[-3].Split('.')
    $abiTags = $parts[-2].Split('.')
    $plat    = $parts[-1].Split('.')
    if (-not ('any' -in $plat -or 'win_amd64' -in $plat)) { return $false }
    $cp = 'cp' + $tag
    if ('py3' -in $pyTags -or 'py2' -in $pyTags -or 'any' -in $pyTags) { return $true }
    if ($cp -in $pyTags) { return $true }
    if ('abi3' -in $abiTags) {
        $floor = @($pyTags | Where-Object { $_ -like 'cp*' })
        if ($floor.Count -gt 0 -and $floor[0].Substring(2) -match '^\d+$' -and $tag -match '^\d+$') {
            return [int]$floor[0].Substring(2) -le [int]$tag
        }
        return $true
    }
    return $false
}

$problems = @()
$expected = @{}
foreach ($name in $locked.Keys) {
    if (Wheel-MatchesTag $name $ver) { $expected[$name] = $locked[$name] }
}
$actual = @{}
foreach ($f in Get-ChildItem $exactTagDir -Filter *.whl) {
    $actual[$f.Name] = (Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower()
}
# required - actual  -> missing (OFFLINE_DEPENDENCY_MISSING)
foreach ($name in $expected.Keys) {
    if (-not $actual.ContainsKey($name)) {
        $problems += [ordered]@{ file = $name; problem = "missing wheel"; code = "OFFLINE_DEPENDENCY_MISSING" }
    }
}
foreach ($name in $actual.Keys) {
    if ($expected.ContainsKey($name)) {
        if ($actual[$name] -ne $expected[$name].ToLower()) {
            $problems += [ordered]@{ file = $name; problem = "hash mismatch"; code = "OFFLINE_DEPENDENCY_HASH_MISMATCH"; expected = $expected[$name]; actual = $actual[$name] }
        }
    } else {
        $problems += [ordered]@{ file = $name; problem = "unlisted wheel (not in lock)"; code = "OFFLINE_DEPENDENCY_HASH_MISMATCH" }
    }
}
if ($problems.Count -gt 0) {
    Fail "OFFLINE_DEPENDENCY_HASH_MISMATCH" ($problems | ConvertTo-Json -Depth 4)
}
Write-Host ("SHA256 verification: OK ({0} wheels; exact expected set present, all hashes match the lock)" -f $actual.Count)

# --- install from the LOCAL wheelhouse ONLY (no index, no network) -----------
$specs = @(
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
$pipInstall = @("-m", "pip", "install", "--no-index", "--find-links", $exactTagDir) + $specs
Write-Host "== $($PythonExe) $($PythonArgs -join ' ') $($pipInstall -join ' ')"
$rc = Invoke-Python $pipInstall
if ($rc -ne 0) {
    Fail "OFFLINE_DEPENDENCY_MISSING" "pip --no-index install failed (exit $rc) - a required wheel is missing from the local wheelhouse"
}

# --- optional: test runner from the local TEST wheelhouse (still no index) ---
if ($AlsoTestRunner) {
    if (-not (Test-Path $testWheels)) { Fail "OFFLINE_DEPENDENCY_MISSING" "local test-wheelhouse not found: $testWheels" }
    $tTagDir = Join-Path $testWheels $ver
    if (-not (Test-Path $tTagDir)) {
        Fail "OFFLINE_DEPENDENCY_MISSING" "no test wheelhouse for CPython tag '$ver' (required: $tTagDir)"
    }
    # NOTE: build the argument list in a VARIABLE first. In an argument
    # position `@(array) + $more` is parsed as SPLATTING and drops $more.
    $testPipArgs = @("-m", "pip", "install", "--no-index", "--find-links", $tTagDir, "pytest==9.1.1")
    $rc = Invoke-Python $testPipArgs
    if ($rc -ne 0) {
        Fail "OFFLINE_DEPENDENCY_MISSING" "test-runner install from local test wheelhouse failed (exit $rc)"
    }
    Write-Host "test runner installed from local test wheelhouse (--no-index)"
}

# --- verify the installed offline runtime ------------------------------------
$verifyScript = Join-Path $BundleRoot "scripts\verify_offline_runtime.py"
if (-not (Test-Path $verifyScript)) { $verifyScript = Join-Path $appDir "scripts\verify_offline_runtime.py" }
if (Test-Path $verifyScript) {
    $rc = Invoke-Python @($verifyScript, "--root", $appDir)
    if ($rc -ne 0) { Fail "OFFLINE_RUNTIME_INCOMPLETE" "offline runtime verification failed after install" }
}

$ok = [ordered]@{
    ok = $true
    status = "PASS"
    networkPolicy = "FORBIDDEN"
    pipNoIndex = $true
    wheelhouse = $exactTagDir
    verifiedHashes = $true
    exactTag = $ver
    note = "installed exclusively from the local wheelhouse (--no-index --find-links); no PyPI, no network"
}
$ok | ConvertTo-Json
Write-Host "OFFLINE INSTALL OK"
exit 0
