# Offline Runtime Dependencies — verified analysis

Scope: the **runtime** Python dependency closure of the offline bundle:
`src/vfp_toolchain/` + vendored `tools/dbfbridge/` + vendored `tools/dbf_anonymizer/`.
Analysis method: AST scan of every `.py` file in those trees for third-party
imports, then verification against the installed environment (Python 3.14) and
the PyPI index. `pyproject.toml` was NOT the source of truth — actual import
statements were.

## Direct runtime imports (verified)

| name | purpose | importedBy | requiredFor | kind | runtimeMandatory |
|---|---|---|---|---|---|
| `dbfread` | pure-Python DBF/FPT reader | `dbf_bridge/exporter/reader.py`, `dbf_bridge/exporter/writer.py`, `dbf_bridge/importer/reconstruct.py`, `dbf_bridge/verifier.py` (top-level `from dbfread import DBF, MissingMemoFile`) | **DBF/FPT READ — required for PURE READ** | purePython | **YES** |
| `dbf` | pure-Python DBF writer (reconstruction) | `dbf_bridge/importer/writer.py` (lazy `import dbf` inside `write_dbf()`) | DBF reconstruction only | purePython | optional (lazy) |
| `orjson` | fast JSON (de)serialization | `dbf_bridge/converters.py` (lazy `import orjson`, falls back to stdlib `json`) | JSON/JSONL conversion speedup | nativeBinary | optional (fallback exists) |
| `openpyxl` | XLSX reading | `dbf_bridge/importer/readers.py` (lazy `import openpyxl` inside `_iter_xlsx()`) | XLSX reconstruction only | purePython | optional (lazy) |
| `xlsxwriter` | XLSX writing | `dbf_bridge/converters.py` (lazy `import xlsxwriter` at line 390) | XLSX export only | purePython | optional (lazy) |
| `polars` | tabular conversion | `dbf_bridge/converters.py` (lazy `import polars as pl` at line 677) | large-table CSV/tabular conversion | nativeBinary (runtime binary) | optional (lazy) |

`tools/dbf_anonymizer/` imports **no** third-party packages directly (verified
by AST scan) — only stdlib + `dbfbridge` + `vfp_*` project modules. Its
transitive closure is identical to dbfbridge's.

`src/vfp_toolchain/` imports **no** third-party packages (stdlib + project
modules + lazy vendored backend packages only).

## Transitive closure (pip-verified, Windows)

| name | version | why |
|---|---|---|
| `et_xmlfile` | 2.0.0 | required by openpyxl |
| `polars_runtime_32` | 1.44.1 | native runtime binary required by polars (cp310-abi3 win_amd64) |
| `aenum` | 3.1.17 | required by `dbf` (0.99.11) |

## Locked versions (per-Python verified)

| name | py3.10 | py3.12 | py3.14 | notes |
|---|---|---|---|---|
| `dbfread` | 2.0.7 | 2.0.7 | 2.0.7 | pure Python wheel, one file serves all three |
| `dbf` | 0.99.11 | 0.99.11 | 0.99.11 | pure Python wheel |
| `openpyxl` | 3.1.5 | 3.1.5 | 3.1.5 | pure Python wheel |
| `et_xmlfile` | 2.0.0 | 2.0.0 | 2.0.0 | pure Python wheel |
| `xlsxwriter` | 3.2.9 | 3.2.9 | 3.2.9 | pure Python wheel |
| `orjson` | 3.12.0 | 3.12.0 | 3.12.0 | **platform wheel — one per CPython ABI** |
| `polars` | 1.44.1 | 1.44.1 | 1.44.1 | pure Python meta-package |
| `polars_runtime_32` | 1.44.1 | 1.44.1 | 1.44.1 | **cp310-abi3 wheel — one file covers 3.10/3.12/3.14** |
| `aenum` | 3.1.17 | 3.1.17 | 3.1.17 | pure Python wheel (dbf dependency) |

**Result: a SINGLE shared wheelhouse serves all three supported Pythons**
(pure-Python wheels are interpreter-agnostic; the two native wheels
`orjson` is the only per-ABI file — the builder downloads one wheel per
supported CPython version). No per-Python resolution was necessary beyond
that; `pip download --only-binary=:all: --python-version <X>` confirmed each
version resolves on Windows for 3.10, 3.12 and 3.14.

## License / source

| name | license | source |
|---|---|---|
| dbfread | Apache-2.0 | https://pypi.org/project/dbfread |
| dbf | MIT | https://pypi.org/project/dbf |
| openpyxl | MIT | https://pypi.org/project/openpyxl |
| et_xmlfile | MIT | https://pypi.org/project/et_xmlfile |
| xlsxwriter | BSD-3-Clause | https://pypi.org/project/xlsxwriter |
| orjson | Apache-2.0 | https://pypi.org/project/orjson |
| polars / polars_runtime_32 | MIT | https://pypi.org/project/polars |
| aenum | BSD-2-Clause | https://pypi.org/project/aenum |

## Test-runner dependency closure (separate lock)

Executing the pytest suite is a TEST plane, not a runtime one. It is locked
in a **distinct** manifest `runtime/test-dependencies.json`:

| name | version | license | applies to |
|---|---|---|---|
| pytest | 9.1.1 | MIT | 3.10 / 3.12 / 3.14 |
| pluggy | 1.6.0 | MIT | 3.10 / 3.12 / 3.14 |
| iniconfig | 2.3.0 | BSD-2-Clause | 3.10 / 3.12 / 3.14 |
| packaging | 26.3 | BSD-2-Clause / Apache-2.0 | 3.10 / 3.12 / 3.14 |
| pygments | 2.21.0 | BSD-2-Clause | 3.10 / 3.12 / 3.14 |
| colorama | 0.4.6 | BSD-3-Clause | 3.10 / 3.12 / 3.14 |
| tomli | 2.4.1 | MIT | **3.10 only** (`python_version < "3.11"`) |
| exceptiongroup | 1.3.1 | Apache-2.0 | **3.10 only** (`python_version < "3.11"`) |
| typing_extensions | 4.16.0 | PSF | **3.10 only** (via exceptiongroup) |

The marker-gated rows carry a `marker` field in
`runtime/test-dependencies.json`; the builder resolves them per tag and the
wheelhouse verification enforces the exact per-tag set (tomli et al. are
absent from the 3.12/3.14 test wheelhouses).

These packages are NOT imported by `vfp_toolchain` at runtime and must not
be moved into the runtime manifest. The builder downloads them into
`test-wheels/<py>/`; the installer only touches that wheelhouse with
`-AlsoTestRunner`, still under `--no-index`.

## Strategy

- `dbfbridge` + `DBF_Anonymizer` remain **vendored** (Phase 1 decision, unchanged).
- Everything above goes into a **pinned offline wheelhouse**
  (`wheels/<py>/` and `test-wheels/<py>/` inside the built bundle, never
  committed to Git).
- `runtime/runtime-dependencies.json` (committed) is the machine-readable
  RUNTIME lock: exact versions + SHA256 per wheel;
  `runtime/test-dependencies.json` is the machine-readable TEST-RUNNER lock.
- The default supported Python list comes from
  `runtime/runtime-dependencies.json` → `supportedPython` (one source of
  truth; `-PythonVersions` is an explicit override, validated before pip).
- `scripts/build_offline_bundle.ps1` (maintainer, network allowed) resolves
  and verifies; `scripts/install_offline.ps1` (target machine, network
  FORBIDDEN) uses `pip --no-index --find-links <wheelhouse>` only.
