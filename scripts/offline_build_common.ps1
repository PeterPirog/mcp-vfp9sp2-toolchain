# =============================================================================
# offline_build_common.ps1 - shared helpers for the offline bundle plane.
#
# Dotted into by scripts/build_offline_bundle.ps1 AND by the regression test
# (tests/test_offline_builder_versions.py) so the version-resolution contract
# has exactly ONE implementation.
#
# Contract (build_offline_bundle.ps1 parameter):
#   -PythonVersions is a SINGLE STRING. Empty => the manifest's
#   supportedPython list is the source of truth. Non-empty => comma-separated
#   maintainer override. Every resolved version must match ^\d+\.\d+$;
#   otherwise resolution fails with OFFLINE_DEPENDENCY_RESOLUTION_ERROR
#   BEFORE any pip invocation.
# =============================================================================

# Resolve the build-target Python versions.
#   -ManifestPath : runtime/runtime-dependencies.json (supportedPython default)
#   -Override     : "" (use manifest) or "3.12" / "3.10,3.14"
# Returns a hashtable:
#   resolved : [string]   sorted-unique valid versions
#   rejected : [string]   invalid entries (must be non-empty => caller FAILs)
#   source   : "manifest supportedPython" | "override -PythonVersions"
function Resolve-BuildPythonVersions(
    [Parameter(Mandatory)][string]$ManifestPath,
    [string]$Override = ""
) {
    if (-not (Test-Path $ManifestPath)) {
        throw "OFFLINE_DEPENDENCY_RESOLUTION_ERROR: manifest not found: $ManifestPath"
    }
    $lock = Get-Content $ManifestPath -Raw | ConvertFrom-Json
    $manifestPythons = @($lock.supportedPython | Where-Object { $_ -match '^\d+\.\d+$' })
    if ($manifestPythons.Count -eq 0) {
        throw "OFFLINE_DEPENDENCY_RESOLUTION_ERROR: supportedPython missing/invalid in $ManifestPath"
    }

    if ([string]::IsNullOrWhiteSpace($Override)) {
        $source = "manifest supportedPython"
        $raw = $manifestPythons
    } else {
        $source = "override -PythonVersions"
        $raw = @($Override -split ',' | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
    }

    $resolved = @($raw | Where-Object { $_ -match '^\d+\.\d+$' } | Sort-Object -Unique)
    $rejected = @($raw | Where-Object { $_ -notmatch '^\d+\.\d+$' })

    if ($resolved.Count -eq 0) {
        throw "OFFLINE_DEPENDENCY_RESOLUTION_ERROR: no valid Python versions resolved (source: $source; raw: $($raw -join ','))"
    }
    [ordered]@{ resolved = $resolved; rejected = $rejected; source = $source }
}

# Derive the pip --python-version tag: "3.12" -> "312"
function Get-PythonTag([string]$py) {
    if ($py -notmatch '^\d+\.\d+$') { return "" }
    return ($py -replace '\.', '')
}

if ($MyInvocation.InvocationName -ne ".") {
    # executed directly: smoke self-test
    $here = Split-Path -Parent $MyInvocation.MyCommand.Path
    $r = Resolve-BuildPythonVersions (Join-Path (Split-Path -Parent $here) "runtime\runtime-dependencies.json")
    $r | ConvertTo-Json
}
