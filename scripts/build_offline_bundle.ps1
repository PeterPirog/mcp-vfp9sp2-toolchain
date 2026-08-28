# =============================================================================
# build_offline_bundle.ps1 - MAINTAINER / BUILD MACHINE tool.
#
# Network use here is ALLOWED (this is the build-time plane). It produces a
# self-contained offline bundle under dist/ that a machine WITHOUT internet
# can install from, using ONLY install-offline.ps1.
#
# Python version contract (ONE source of truth):
#   * the DEFAULT supported Python list is read from
#     runtime/runtime-dependencies.json -> supportedPython (manifest);
#   * -PythonVersions is an explicit maintainer override. It is a SINGLE
#     STRING (comma-separated), NOT a [string[]] param - `powershell -File`
#     passes CLI args as strings, and the script owns the split:
#         powershell -ExecutionPolicy Bypass -File scripts\build_offline_bundle.ps1
#         powershell -ExecutionPolicy Bypass -File scripts\build_offline_bundle.ps1 -PythonVersions "3.12"
#         powershell -ExecutionPolicy Bypass -File scripts\build_offline_bundle.ps1 -PythonVersions "3.10,3.14"
#   * every resolved version MUST match ^\d+\.\d+$; otherwise the build FAILs
#     with OFFLINE_DEPENDENCY_RESOLUTION_ERROR BEFORE any pip invocation.
#   * resolved versions are kept in $resolvedPythonVersions - the param
#     variable is never overwritten.
#
# Build host Python: the builder does NOT require a specific CPython on the
# build machine. `pip download --python-version/--platform/--abi` performs
# cross-resolving. -PythonExe + -PythonArgs select the build-host interpreter.
# Default: "py" (the Windows launcher works on maintainer machines where
# `python` is a broken MS-Store alias); CI passes "-PythonExe python" after
# actions/setup-python. Invocation is always:  & $PythonExe @PythonArgs @Args
# (separated executable + launcher args + command args — never a joined string).
#
# Steps:
#   0. resolve supported Python versions (manifest default or override)
#   1. download exactly the pinned wheels per tag (runtime + test wheelhouses)
#   2. verify SHA256 + EXACT wheel set per tag against the lock manifests
#   3. assemble the CANONICAL runtime root under app/ (config.json, src/,
#      tools/, runtime/, language/, docs/, tests/, notices) - no sibling
#      knowledge/ duplicate
#   4. copy third-party notices + extract wheel license metadata into licenses/
#   5. write the bundle manifest (wheels, test wheels, tree + file hashes)
#   6. verify mandatory knowledge files exist in app/
#   7. emit the final bundle layout:
#        dist/mcp-vfp9sp2-toolchain-offline/
#            app/                  (CANONICAL toolchain runtime root)
#            wheels/<py>/
#            test-wheels/<py>/
#            manifests/bundle-manifest.json
#            licenses/
#            install-offline.ps1
#            scripts/verify_offline_runtime.py
#
# This script is NEVER run by the offline target machine.
# =============================================================================

[CmdletBinding()]
param(
    [string]$RepoRoot = "",
    [string]$PythonVersions = "",
    [string]$DistDir = "",
    [string]$PythonExe = "py",
    [string[]]$PythonArgs = @()
)
# Sensible default launcher on Windows: `py -3` (newest installed CPython).
# Cross-resolving (--python-version etc.) does not need the newest CPython,
# so any modern build-host interpreter works. CI overrides with plain `python`
# after actions/setup-python.
if ($PythonArgs.Count -eq 0 -and $PythonExe -ieq "py") { $PythonArgs = @("-3") }
if (-not $RepoRoot) {
    if ($PSScriptRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }
    else { $RepoRoot = (Get-Location).Path }
}
if (-not $DistDir) { $DistDir = Join-Path $RepoRoot "dist" }

$ErrorActionPreference = "Stop"
$BundleName = "mcp-vfp9sp2-toolchain-offline"
$BundleDir  = Join-Path $DistDir $BundleName

# Ensure the zip API is available (needed for license extraction from wheels).
Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue

function Fail([string]$code, [string]$message) {
    $obj = [ordered]@{ ok = $false; status = "FAIL"; errorCode = $code; error = $message }
    $obj | ConvertTo-Json
    exit 1
}

function Tree-SHA256([string]$dir) {
    # Deterministic tree digest: sorted "relpath sha256" lines -> SHA256.
    if (-not (Test-Path $dir)) { return $null }
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

function File-SHA256([string]$path) {
    if (-not (Test-Path $path)) { return $null }
    return (Get-FileHash $path -Algorithm SHA256).Hash.ToLower()
}

# Shared version-resolution contract (dotted in; the regression test uses the
# SAME function so the CLI contract and the test cannot drift apart).
. (Join-Path $PSScriptRoot "offline_build_common.ps1")

# Does this wheel filename serve CPython tag $tag? (py3/py2/any tags; exact
# cpNN; abi3 with a cp floor <= tag; any/win_amd64 platform)
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

Write-Host "== build_offline_bundle =="
Write-Host "repo root   : $RepoRoot"
Write-Host "build pyexe : '$PythonExe' $($PythonArgs -join ' ')"

# --- 0. resolve the supported Python versions (ONE source of truth) ----------
$manifestPath = Join-Path $RepoRoot "runtime\runtime-dependencies.json"
$testManifestPath = Join-Path $RepoRoot "runtime\test-dependencies.json"
if (-not (Get-Command $PythonExe -ErrorAction SilentlyContinue)) {
    Fail "OFFLINE_DEPENDENCY_RESOLUTION_ERROR" "build-host python '$PythonExe' not found"
}
if (-not (Test-Path $manifestPath)) {
    Fail "OFFLINE_DEPENDENCY_RESOLUTION_ERROR" "runtime lock manifest not found: $manifestPath"
}
if (-not (Test-Path $testManifestPath)) {
    Fail "OFFLINE_DEPENDENCY_RESOLUTION_ERROR" "test lock manifest not found: $testManifestPath"
}

$manifestLock = Get-Content $manifestPath -Raw | ConvertFrom-Json
try {
    $versionResolution = Resolve-BuildPythonVersions -ManifestPath $manifestPath -Override $PythonVersions
} catch {
    Fail "OFFLINE_DEPENDENCY_RESOLUTION_ERROR" ([string]$_)
}
$resolvedPythonVersions = @($versionResolution.resolved)
$rejectedVersions = @($versionResolution.rejected)
$versionSource = $versionResolution.source
if ($rejectedVersions.Count -gt 0) {
    $rejMsg = "invalid Python version entries (must match ^\d+\.\d+$): " + ($rejectedVersions -join ', ')
    Fail "OFFLINE_DEPENDENCY_RESOLUTION_ERROR" $rejMsg
}
$pyList = $resolvedPythonVersions -join ', '
Write-Host "pythons     : $pyList (source: $versionSource)"
Write-Host "bundle dir  : $BundleDir"

# --- 1. clean staging --------------------------------------------------------
if (Test-Path $BundleDir) { Remove-Item $BundleDir -Recurse -Force }
$appDir      = Join-Path $BundleDir "app"
$wheelsDir   = Join-Path $BundleDir "wheels"
$testWheels  = Join-Path $BundleDir "test-wheels"
$manifests   = Join-Path $BundleDir "manifests"
$licensesDir = Join-Path $BundleDir "licenses"
foreach ($d in @($appDir, $wheelsDir, $testWheels, $manifests, $licensesDir)) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}
foreach ($py in $resolvedPythonVersions) {
    New-Item -ItemType Directory -Path (Join-Path $wheelsDir ($py -replace '\.', '')) -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $testWheels ($py -replace '\.', '')) -Force | Out-Null
}

# --- 2. download exactly the pinned wheels ----------------------------------
$runtimeSpecs = @(
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
$testSpecs = @(
    "pytest==9.1.1"
    "pluggy==1.6.0"
    "iniconfig==2.3.0"
    "packaging==26.3"
    "pygments==2.21.0"
    "colorama==0.4.6"
)

$lockedHashes = @{}
foreach ($dep in $manifestLock.dependencies) {
    foreach ($key in $dep.hashes.PSObject.Properties) { $lockedHashes[$key.Name] = $key.Value }
}
$testLock = Get-Content $testManifestPath -Raw | ConvertFrom-Json
$testLockedHashes = @{}
foreach ($dep in $testLock.dependencies) {
    foreach ($key in $dep.hashes.PSObject.Properties) { $testLockedHashes[$key.Name] = $key.Value }
}

function Invoke-BuildPython([string[]]$PyPyArgs) {
    # Single, unambiguous build-host python invocation (separated executable
    # + launcher args + command args; spaces in paths are safe).
    & $PythonExe @PythonArgs @PyPyArgs
    return $LASTEXITCODE
}

foreach ($py in $resolvedPythonVersions) {
    $pyTag = $py -replace '\.', ''
    if (-not $pyTag) {
        Fail "OFFLINE_DEPENDENCY_RESOLUTION_ERROR" "empty python tag derived from '$py' - not invoking pip"
    }
    $rtTarget = Join-Path $wheelsDir $pyTag
    $tsTarget = Join-Path $testWheels $pyTag

    # exact-ABI scope per tag: the exact cpNN wheel (orjson), abi3
    # (polars_runtime_32) and pure-Python (none) wheels - nothing else, so the
    # downloaded set is EXACTLY the locked set for that tag.
    $commonArgs = @(
        "-m", "pip", "download"
        "--only-binary=:all:",
        "--python-version", $pyTag,
        "--platform", "win_amd64",
        "--implementation", "cp",
        "--abi", "cp$pyTag",
        "--abi", "abi3",
        "--abi", "none",
        "-q"
    )

    Write-Host "== pip download [runtime] targetPython=$py pythonTag=$pyTag platform=win_amd64 wheelhouse=$rtTarget"
    $rc = Invoke-BuildPython ($commonArgs + $runtimeSpecs + @("-d", $rtTarget))
    if ($rc -ne 0) {
        Fail "OFFLINE_DEPENDENCY_MISSING" "pip download failed (runtime, python $py tag $pyTag, exit $rc)"
    }
    Write-Host "== pip download [test] targetPython=$py pythonTag=$pyTag platform=win_amd64 wheelhouse=$tsTarget"
    $rc = Invoke-BuildPython ($commonArgs + $testSpecs + @("-d", $tsTarget))
    if ($rc -ne 0) {
        Fail "OFFLINE_DEPENDENCY_MISSING" "pip download failed (test, python $py tag $pyTag, exit $rc)"
    }
}

# --- 3. verify SHA256 + completeness of every wheelhouse ---------------------
function Verify-Wheelhouse([string]$dir, [hashtable]$locked, [string]$tag, [string]$label) {
    $problems = @()
    $expected = @{}
    foreach ($k in $locked.Keys) { if (Wheel-MatchesTag $k $tag) { $expected[$k] = $locked[$k] } }
    $actual = @{}
    foreach ($f in Get-ChildItem $dir -Filter *.whl) {
        $actual[$f.Name] = (Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower()
    }
    # required - actual -> missing
    foreach ($name in $expected.Keys) {
        if (-not $actual.ContainsKey($name)) {
            $problems += [ordered]@{ file = $name; problem = "missing wheel" }
        }
    }
    # hash mismatches + unlisted wheels (fail closed)
    foreach ($name in $actual.Keys) {
        if ($expected.ContainsKey($name)) {
            if ($actual[$name] -ne $expected[$name].ToLower()) {
                $problems += [ordered]@{ file = $name; problem = "hash mismatch"; expected = $expected[$name]; actual = $actual[$name] }
            }
        } else {
            $problems += [ordered]@{ file = $name; problem = "unlisted wheel (not in lock manifest)" }
        }
    }
    if ($problems.Count -gt 0) {
        $whMsg = "${label}: " + ($problems | ConvertTo-Json -Depth 4)
        Fail "OFFLINE_DEPENDENCY_HASH_MISMATCH" $whMsg
    }
    $okMsg = "wheelhouse OK ({0}): {1} wheels, all SHA256-verified, exact set matches lock" -f $label, $actual.Count
    Write-Host $okMsg
}

foreach ($py in $resolvedPythonVersions) {
    $pyTag = $py -replace '\.', ''
    Verify-Wheelhouse (Join-Path $wheelsDir $pyTag) $lockedHashes $pyTag "runtime/$pyTag"
    Verify-Wheelhouse (Join-Path $testWheels $pyTag) $testLockedHashes $pyTag "test/$pyTag"
}

# --- 4. assemble the CANONICAL runtime root under app/ -----------------------
# app/ IS the toolchain runtime root: VFPToolchainService(root=<bundle>/app)
# must see the real shipped config.json, knowledge and code. There is exactly
# ONE canonical copy (no sibling knowledge/ duplicate).
$firstPartyRootModules = @(
    "vfp_driver.py", "vfp_protocol.py", "vfp_common.py", "vfp_safety.py",
    "vfp_dbf_export.py", "vfp_encoding.py", "vfp_indexer.py", "vfp_cdx.py",
    "vfp_audit.py", "conftest.py"
)
Copy-Item -Recurse -Force (Join-Path $RepoRoot "src") (Join-Path $appDir "src")
foreach ($m in $firstPartyRootModules) {
    Copy-Item -Force (Join-Path $RepoRoot $m) (Join-Path $appDir $m)
}
New-Item -ItemType Directory -Path (Join-Path $appDir "tools") -Force | Out-Null
Copy-Item -Recurse -Force (Join-Path $RepoRoot "tools\dbfbridge") (Join-Path $appDir "tools\dbfbridge")
Copy-Item -Recurse -Force (Join-Path $RepoRoot "tools\dbf_anonymizer") (Join-Path $appDir "tools\dbf_anonymizer")
Copy-Item -Force (Join-Path $RepoRoot "tools\VENDORED_DEPENDENCIES.json") (Join-Path $appDir "tools\VENDORED_DEPENDENCIES.json")
New-Item -ItemType Directory -Path (Join-Path $appDir "runtime") -Force | Out-Null
Copy-Item -Force $manifestPath (Join-Path $appDir "runtime\runtime-dependencies.json")
Copy-Item -Force $testManifestPath (Join-Path $appDir "runtime\test-dependencies.json")
New-Item -ItemType Directory -Path (Join-Path $appDir "tests") -Force | Out-Null
Copy-Item -Recurse -Force (Join-Path $RepoRoot "tests") (Join-Path $appDir "tests")

# real configuration + knowledge + docs inside app/ (canonical)
Copy-Item -Force (Join-Path $RepoRoot "config.json") (Join-Path $appDir "config.json")
if (Test-Path (Join-Path $RepoRoot "language")) {
    Copy-Item -Recurse -Force (Join-Path $RepoRoot "language") (Join-Path $appDir "language")
}
Copy-Item -Recurse -Force (Join-Path $RepoRoot "docs") (Join-Path $appDir "docs")
Copy-Item -Force (Join-Path $RepoRoot "README.md") (Join-Path $appDir "README.md")
Copy-Item -Force (Join-Path $RepoRoot "THANKS.md") (Join-Path $appDir "THANKS.md")

# --- 5. third-party notices + license extraction ------------------------------
$noticesSrc = Join-Path $RepoRoot "runtime\THIRD_PARTY_NOTICES.md"
if (Test-Path $noticesSrc) {
    Copy-Item $noticesSrc (Join-Path $licensesDir "THIRD_PARTY_NOTICES.md")
    Copy-Item $noticesSrc (Join-Path $appDir "THIRD_PARTY_NOTICES.md")
} else {
    Fail "OFFLINE_RUNTIME_INCOMPLETE" "runtime/THIRD_PARTY_NOTICES.md is required for the distributable bundle"
}

# extract the METADATA license of every wheel (provenance + license fields);
# the authoritative license texts travel with the wheels themselves.
foreach ($py in $resolvedPythonVersions) {
    $pyTag = $py -replace '\.', ''
    $perPy = Join-Path $licensesDir ("py" + $pyTag)
    New-Item -ItemType Directory -Path $perPy -Force | Out-Null
    foreach ($whl in Get-ChildItem (Join-Path $wheelsDir $pyTag) -Filter *.whl) {
        $zip = [System.IO.Compression.ZipFile]::OpenRead($whl.FullName)
        $meta = $zip.Entries | Where-Object { $_.FullName -match 'dist-info/METADATA$' } | Select-Object -First 1
        if ($meta) {
            $reader = New-Object System.IO.StreamReader($meta.Open())
            $text = $reader.ReadToEnd(); $reader.Close()
            $out = Join-Path $perPy ($whl.BaseName + ".license.txt")
            Set-Content -Path $out -Value $text -Encoding UTF8
        }
        $zip.Dispose()
    }
}
# vendored snapshots keep their in-repo license material (copied into app/ already)

# --- 6. write the bundle manifest (all hashes) -------------------------------
$bundleManifest = [ordered]@{
    schemaVersion = 3
    bundle = $BundleName
    builtAt = (Get-Date).ToString("o")
    pythonVersions = $resolvedPythonVersions
    targetPlatform = "windows"
    networkRequiredAtRuntime = $false
    canonicalRoot = "app"
    app = [ordered]@{
        configSha256            = (File-SHA256 (Join-Path $appDir "config.json"))
        knowledgeTreeSha256     = (Tree-SHA256 (Join-Path $appDir "language"))
        docsTreeSha256          = (Tree-SHA256 (Join-Path $appDir "docs"))
        runtimeManifestSha256   = (File-SHA256 (Join-Path $appDir "runtime\runtime-dependencies.json"))
        testManifestSha256      = (File-SHA256 (Join-Path $appDir "runtime\test-dependencies.json"))
        thirdPartyNoticesSha256 = (File-SHA256 (Join-Path $appDir "THIRD_PARTY_NOTICES.md"))
        dbfbridgeTreeSha256     = (Tree-SHA256 (Join-Path $appDir "tools\dbfbridge"))
        dbfAnonymizerTreeSha256 = (Tree-SHA256 (Join-Path $appDir "tools\dbf_anonymizer"))
    }
    licensesTreeSha256 = (Tree-SHA256 $licensesDir)
    wheels = @{}
    testWheels = @{}
}
foreach ($py in $resolvedPythonVersions) {
    $pyTag = $py -replace '\.', ''
    $w = @{}; $t = @{}
    foreach ($file in Get-ChildItem (Join-Path $wheelsDir $pyTag) -Filter *.whl) {
        $w[$file.Name] = (Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower()
    }
    foreach ($file in Get-ChildItem (Join-Path $testWheels $pyTag) -Filter *.whl) {
        $t[$file.Name] = (Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLower()
    }
    $bundleManifest.wheels[$pyTag] = $w
    $bundleManifest.testWheels[$pyTag] = $t
}
# JSON must be BOM-free (JSON consumers reject a UTF-8 BOM).
# -Encoding utf8NoBOM is a PS7-only name; use a .NET writer that works on
# both Windows PowerShell 5.1 and PowerShell 7.
$manifestJson = $bundleManifest | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText((Join-Path $manifests "bundle-manifest.json"), $manifestJson, (New-Object System.Text.UTF8Encoding($false)))

# --- 7. copy the offline installer + verifier into the bundle ----------------
Copy-Item (Join-Path $RepoRoot "scripts\install_offline.ps1") (Join-Path $BundleDir "install-offline.ps1")
New-Item -ItemType Directory -Path (Join-Path $BundleDir "scripts") -Force | Out-Null
Copy-Item (Join-Path $RepoRoot "scripts\verify_offline_runtime.py") (Join-Path $BundleDir "scripts\verify_offline_runtime.py")

# --- 8. verify mandatory knowledge files in the bundle -----------------------
$cfg = Get-Content (Join-Path $appDir "config.json") -Raw | ConvertFrom-Json
$missingKnowledge = @()
foreach ($rel in $cfg.knowledge.mandatory) {
    $p = Join-Path $appDir ($rel.Replace('/', '\'))
    if (-not (Test-Path $p)) { $missingKnowledge += $rel }
}
if ($missingKnowledge.Count -gt 0) {
    $mkMsg = "mandatory knowledge files missing from app/: " + ($missingKnowledge -join ', ')
    Fail "OFFLINE_RUNTIME_INCOMPLETE" $mkMsg
}
$mkCount = $cfg.knowledge.mandatory.Count
Write-Host "mandatory knowledge files: OK ($mkCount files present in app/)"

# --- done ---------------------------------------------------------------------
$summary = [ordered]@{
    ok = $true
    status = "PASS"
    bundle = $BundleDir
    pythonVersions = $resolvedPythonVersions
    wheels = $bundleManifest.wheels
    testWheels = $bundleManifest.testWheels
    note = "SHA256-verified against runtime/runtime-dependencies.json + runtime/test-dependencies.json"
}
$summary | ConvertTo-Json -Depth 8
Write-Host "OFFLINE BUNDLE READY: $BundleDir"
exit 0
