# Offline Runtime Deployment

The Python runtime of this toolchain is **closed and reproducible**: after the
offline bundle is installed on a Windows machine, **no internet access is
required at runtime** — not for imports, not for DBF PURE READ, not for
capability discovery.

## What "offline" means here

| Plane | Network | Who |
|---|---|---|
| **Build time** (resolving pinned wheels, downloading from PyPI) | ALLOWED | maintainer machine only |
| **Runtime** (import, DBF read, conversion, anonymization status) | FORBIDDEN | target Windows machine |

The toolchain runtime never runs `pip install`, `pip download`, `git
clone/pull`, HTTP requests or package-registry lookups. This is enforced by a
test (`test_core_package_has_no_network_or_package_manager_calls`).

## Bundle layout

Built by `scripts/build_offline_bundle.ps1` (maintainer tool, network allowed):

```text
dist/mcp-vfp9sp2-toolchain-offline/
  app/                          # toolchain runtime (src/, vfp_*.py, tools/, runtime/)
    src/vfp_toolchain/          # Core Service
    tools/dbfbridge/            # VENDORED pinned snapshot (addbadb928…)
    tools/dbf_anonymizer/       # VENDORED pinned snapshot (ed79154978…)
    runtime/runtime-dependencies.json
  wheels/
    310/  312/  314/            # pinned wheels (SHA256-verified against the lock)
  knowledge/                    # config.json, docs, language catalog
  manifests/bundle-manifest.json
  install-offline.ps1
  scripts/verify_offline_runtime.py
```

`dist/` is **never committed** (maintainer artifact; GitHub Actions publishes
it as an artifact).

## Installing offline (target machine)

```powershell
powershell -ExecutionPolicy Bypass -File install-offline.ps1
```

The installer:
1. verifies every wheel's SHA256 against `runtime/runtime-dependencies.json`
   (a bad hash is `OFFLINE_DEPENDENCY_HASH_MISMATCH`, a missing wheel is
   `OFFLINE_DEPENDENCY_MISSING`),
2. installs with `pip --no-index --find-links <local wheelhouse>` — there is
   **no PyPI fallback**,
3. runs `scripts/verify_offline_runtime.py` and fails on any problem
   (`OFFLINE_RUNTIME_INCOMPLETE`).

## Verified dependency set (lock)

`runtime/runtime-dependencies.json` is the machine-readable lock (schema v1,
Windows, Python 3.10/3.12/3.14). One shared wheelhouse serves all three
Pythons: pure-Python wheels are interpreter-agnostic, `polars_runtime_32` is
`cp310-abi3`, and `orjson` is the only per-ABI wheel.

| name | version | mandatory | purpose |
|---|---|---|---|
| dbfread | 2.0.7 | **YES** | DBF/FPT read (PURE READ) |
| dbf | 0.99.11 | no | DBF reconstruction |
| aenum | 3.1.17 | no | dbf dependency |
| openpyxl | 3.1.5 | no | XLSX read |
| et_xmlfile | 2.0.0 | no | openpyxl dependency |
| xlsxwriter | 3.2.9 | no | XLSX write |
| orjson | 3.12.0 | no | JSON speedup (stdlib fallback) |
| polars | 1.44.1 | no | tabular conversion |
| polars_runtime_32 | 1.44.1 | no | polars native runtime |

## Capability discovery report

`VFPToolchainService().capabilities()` includes:

```json
"offlineRuntime": {
  "dependencyClosure": true,
  "verified": true,
  "missing": [],
  "mismatched": [],
  "hashMismatched": [],
  "wheelhousePresent": false,
  "networkRequired": false
}
```

`offlineRuntime` is a **deployment property, not a new capability class** —
the Capability enum is unchanged.

## Stable diagnostic codes

| code | meaning |
|---|---|
| `OFFLINE_DEPENDENCY_MISSING` | a required wheel/package is absent |
| `OFFLINE_DEPENDENCY_VERSION_MISMATCH` | installed version differs from the lock (mandatory packages gate) |
| `OFFLINE_DEPENDENCY_HASH_MISMATCH` | wheel SHA256 does not match the lock — never installed |
| `OFFLINE_DEPENDENCY_ORIGIN_MISMATCH` | a vendored package resolved from a non-vendored origin (shadowing) |
| `OFFLINE_RUNTIME_INCOMPLETE` | the offline runtime verification as a whole did not pass |

These are distinct from the Phase 1 `DEPENDENCY_VERSION_MISMATCH` (vendored
snapshot pin checks) on purpose: different evidence, different remediation.

## Scope of this phase

- MCP: **not implemented yet**.
- Production anonymization (`vfp_anonymize`, `vfp_recover_data`): **not
  published** — only read-only status/preflight.
- FoxBin2Prg: remains `EXTERNAL_CONFIGURED`, BIN2PRG-only, not part of the
  offline bundle.
