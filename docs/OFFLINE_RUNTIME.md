# Offline Runtime Deployment

The Python runtime of this toolchain is **closed and reproducible**: after the
offline bundle is installed on a Windows machine, **no internet access is
required at runtime** - not for imports, not for DBF PURE READ, not for
capability discovery.

## What "offline" means here

| Plane | Network | Who |
|---|---|---|
| **Build time** (resolving pinned wheels, downloading from PyPI) | ALLOWED | maintainer machine / CI builder only |
| **Runtime** (import, DBF read, conversion, anonymization status) | FORBIDDEN | target Windows machine |

The toolchain runtime never runs `pip install`, `pip download`, `git
clone/pull`, HTTP requests or package-registry lookups. This is enforced by a
test (`test_core_package_has_no_network_or_package_manager_calls`).

## Bundle layout

Built by `scripts/build_offline_bundle.ps1` (maintainer tool, network allowed):

```text
dist/mcp-vfp9sp2-toolchain-offline/
  app/                          # CANONICAL toolchain runtime root (single copy)
    config.json                 # real configuration (not a fallback)
    src/vfp_toolchain/          # Core Service
    vfp_*.py                    # first-party root modules
    tools/dbfbridge/            # VENDORED pinned snapshot (addbadb928...)
    tools/dbf_anonymizer/       # VENDORED pinned snapshot (ed79154978...)
    runtime/runtime-dependencies.json
    runtime/test-dependencies.json
    language/                   # mandatory knowledge files
    docs/                       # project documentation
    tests/
    THIRD_PARTY_NOTICES.md
  wheels/
    310/  312/  314/            # pinned runtime wheels (exact-set, SHA256-verified)
  test-wheels/
    310/  312/  314/            # pinned test-runner wheels (test plane only)
  manifests/bundle-manifest.json  # all wheel + tree + file SHA256 hashes
  licenses/
    THIRD_PARTY_NOTICES.md
    py310/ py312/ py314/        # extracted wheel METADATA license files
  install-offline.ps1
  scripts/verify_offline_runtime.py
```

There is NO sibling `knowledge/` directory: `app/` is the single canonical
root, and `VFPToolchainService(root=<bundle>/app)` loads the real shipped
`config.json` and mandatory knowledge files. `dist/` is **never committed**
(maintainer artifact; GitHub Actions publishes it as an artifact).

## Supported Python: one source of truth

The default build target list is `supportedPython` in
`runtime/runtime-dependencies.json` (3.10, 3.12, 3.14). The builder parameter
is an explicit maintainer override:

```powershell
# default (manifest supportedPython):
powershell -ExecutionPolicy Bypass -File scripts\build_offline_bundle.ps1
# explicit override (single string, comma-separated):
powershell -ExecutionPolicy Bypass -File scripts\build_offline_bundle.ps1 -PythonVersions "3.12"
```

Every resolved version must match `^\d+\.\d+$`; otherwise the build fails
`OFFLINE_DEPENDENCY_RESOLUTION_ERROR` **before any pip invocation**. The
contract is implemented once (`scripts/offline_build_common.ps1`) and covered
by `tests/test_offline_builder_versions.py`.

## Installing offline (target machine)

```powershell
powershell -ExecutionPolicy Bypass -File install-offline.ps1
powershell -ExecutionPolicy Bypass -File install-offline.ps1 -PythonExe py -PythonArgs "-3.12"
```

The installer:
1. resolves the EXACT CPython tag (`3.10`->`310`, `3.12`->`312`,
   `3.14`->`314`) and fails `OFFLINE_DEPENDENCY_MISSING` when that tag's
   wheelhouse is absent - it **never substitutes** another interpreter
   directory (ABI-specific wheels make that unsafe),
2. verifies the wheelhouse against the lock manifest (every expected wheel
   present, every present wheel listed, all SHA256 match; a bad hash is
   `OFFLINE_DEPENDENCY_HASH_MISMATCH`, a missing wheel is
   `OFFLINE_DEPENDENCY_MISSING`),
3. installs with `pip --no-index --find-links <local wheelhouse>` - there is
   **no PyPI fallback**,
4. optionally installs the test runner from the local `test-wheels/`
   (`-AlsoTestRunner`), still `--no-index`,
5. runs `scripts/verify_offline_runtime.py` against `app/` and fails on any
   problem (`OFFLINE_RUNTIME_INCOMPLETE`).

## Verified dependency set (lock)

`runtime/runtime-dependencies.json` is the machine-readable RUNTIME lock
(schema v1, Windows, Python 3.10/3.12/3.14). Pure-Python wheels are
interpreter-agnostic; `polars_runtime_32` is `cp310-abi3` (one file serves
all three Pythons); `orjson` is the only per-ABI wheel (one per CPython).

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

`runtime/test-dependencies.json` is the separate TEST-RUNNER lock
(pytest 9.1.1 + pluggy/iniconfig/packaging/pygments/colorama). Test deps are
**never** merged into the runtime manifest; they install only into test
environments (`test-wheels/`).

Optional packages (all except dbfread) degrade only the specific operation
that requires them if absent; they never disable Core Service or PURE READ.

## Third-party notices

`runtime/THIRD_PARTY_NOTICES.md` (copied into `licenses/` and `app/`) lists
every third-party component with exact version, license, source and purpose.
License metadata is extracted per wheel into `licenses/py<NN>/`. We preserve
the actual license material and provenance; we do not invent or paraphrase
license text.

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

`offlineRuntime` is a **deployment property, not a new capability class** -
the Capability enum is unchanged.

## Stable diagnostic codes

| code | meaning |
|---|---|
| `OFFLINE_DEPENDENCY_RESOLUTION_ERROR` | an invalid/missing Python version or manifest before pip |
| `OFFLINE_DEPENDENCY_MISSING` | a required wheel/package is absent |
| `OFFLINE_DEPENDENCY_VERSION_MISMATCH` | installed version differs from the lock (mandatory packages gate) |
| `OFFLINE_DEPENDENCY_HASH_MISMATCH` | wheel SHA256 does not match the lock - never installed |
| `OFFLINE_DEPENDENCY_ORIGIN_MISMATCH` | a vendored package resolved from a non-vendored origin (shadowing) |
| `OFFLINE_RUNTIME_INCOMPLETE` | the offline runtime verification as a whole did not pass |

These are distinct from the Phase 1 `DEPENDENCY_VERSION_MISMATCH` (vendored
snapshot pin checks) on purpose: different evidence, different remediation.

## Scope of this phase

- MCP: **not implemented yet**.
- Production anonymization (`vfp_anonymize`, `vfp_recover_data`): **not
  published** - only read-only status/preflight.
- FoxBin2Prg: remains `EXTERNAL_CONFIGURED`, BIN2PRG-only, not part of the
  offline bundle.
