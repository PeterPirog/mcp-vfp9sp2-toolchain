# Core Service — transport-neutral foundation

Status: **IMPLEMENTED** (Phase 1 foundation). MCP transport: **not implemented yet** (intentional).

The toolchain now has a single transport-neutral Python service layer that both
current adapters (CLI, OpenCode) use, and that a future MCP server will also use
without re-implementing any logic.

```text
        CLI adapter (vfp_driver.py)        OpenCode adapter (tools/vfp.ts)
                    \                          /
                     \                        /
                     v                        v
              vfp_toolchain (Core Service)  <— future MCP adapter (ROADMAP)
                     |
     +---------------+---------------+----------------+----------------+
     |               |               |                |                |
 PURE_PYTHON     DBFBRIDGE     DBF_ANONYMIZER    FOXBIN2PRG        VFP9_RUNTIME
 (no VFP)      (vendored)     (vendored)      (external,          (installed,
                                         configured)           authoritative)
```

## Package layout

```text
src/vfp_toolchain/
  __init__.py          # public surface: VFPToolchainService, OperationResult, Capability
  models.py            # OperationResult (JSON-serializable, legacy-compatible)
  errors.py            # central error-code catalog (extends vfp_protocol)
  config.py            # read-only config.json access, path resolution
  capabilities.py      # Capability enum == docs/mcp_capability_model.json (one truth)
  service.py           # VFPToolchainService (operations, no globals, no side effects)
  backends/
    __init__.py
    pure_python.py     # PURE_READ ops: detect_project, inventory, snapshot, config
    dbfbridge_backend.py
    dbf_anonymizer_backend.py
    foxbin2prg_backend.py
    vfp9_backend.py
```

## Import contract

`import vfp_toolchain` must work on a machine **without** VFP9, FoxBin2Prg,
COM, OpenCode or Bun. Importing creates no files, opens no DBF, spawns no
process, touches no network. Backend modules load their third-party packages
lazily (only when an operation needs them).

## Operations (Phase 1)

| Operation | Capability | Backend | Notes |
|---|---|---|---|
| `vfp_capabilities` | `PURE_READ` | `PURE_PYTHON` | fast discovery; does NOT launch VFP COM |
| `vfp_detect` | `PURE_READ` | `PURE_PYTHON` | single source of truth replaces the old `tools/vfp.ts` recursive walk |
| `vfp_artifact_inventory` | `PURE_READ` | `PURE_PYTHON` | grouped by artifact family |
| `vfp_anonymization_status` | `PURE_READ` | `DBF_ANONYMIZER` | read-only; no anonymization, no dictionary, no writes |

Every operation returns an `OperationResult` — never a printed line, never a
process exit. The CLI adapter (`vfp_driver.py`) serializes it to the legacy
single-JSON-object protocol and sets the exit code; the OpenCode adapter
(`tools/vfp.ts`) passes the JSON through.

## Result model (backward compatible)

`OperationResult` keeps the legacy `vfp_protocol` fields first and adds the
Core fields. Existing consumers keep working unchanged.

```json
{
  "ok": true, "status": "PASS", "errorCode": null, "rc": 0, "version": "0.3.0",
  "stdout": "", "stderr": "", "data": { },
  "operation": "vfp_capabilities", "requires": ["PURE_READ"], "backend": "PURE_PYTHON",
  "sourceModified": false, "warnings": [], "errors": [], "metadata": {}
}
```

Status meanings are unchanged: `PASS` / `PARTIAL` / `FAIL`.

## Capability model — one truth

`docs/mcp_capability_model.json` is the contract.
`vfp_toolchain.capabilities.Capability` mirrors it exactly; a test
(`test_capability_enum_matches_json_model`) fails if they drift. Do not create
a second list of capability classes.

## PURE READ without VFP

The CI workflow `.github/workflows/pure-read.yml` runs the whole suite on a
runner that **deliberately has no Visual FoxPro** and asserts it. `PURE_READ`
operations (capabilities, detect, inventory, anonymization status, dbfbridge
adapter) pass there. VFP-dependent tests are explicitly skipped, never masked
as PASS.

## Dependency pins (offline)

Manifest: `tools/VENDORED_DEPENDENCIES.json`.

| Dependency | Mode | Pin |
|---|---|---|
| dbfbridge | `VENDORED` (`tools/dbfbridge/`) | `addbadb928…` (v0.1.0) |
| DBF_Anonymizer | `VENDORED` (`tools/dbf_anonymizer/`) | `ed79154978…` (v0.3.0) |
| FoxBin2Prg | `EXTERNAL_CONFIGURED` | upstream `fdbozzo/foxbin2prg` (not in repo) |

DBF_Anonymizer 0.3.0 declares exactly the same dbfbridge commit the toolchain
vendors — one shared dbfbridge, never two. The runtime never downloads any of
these; updates are a maintainer operation.

> **OFFLINE_DEPENDENCY_CLOSURE = NEXT PHASE.** The vendored dbfbridge snapshot
> still imports the third-party `dbfread` package (installed via pip), so the
> dependency closure is not yet fully offline. Closing that gap — vendoring
> `dbfread` (or removing the import) plus a SHA256 manifest per snapshot — is
> the next phase, not part of PR8.

**License/provenance.** dbfbridge ships its upstream `LICENSE` in the vendored
copy. The DBF_Anonymizer upstream repo has no LICENSE file at the pinned
commit — MIT is declared in upstream `pyproject.toml` — so the canonical
license statement for that snapshot is `tools/dbf_anonymizer/NOTICE.md`.

## Fail-closed provenance verification

`backends/verify.py` defines two independent checks; a vendored dependency is
`available == True` **only if all checks pass**:

1. **`pinVerified`** — the commit recorded in the dependency's `VERSION.txt`
   must equal the architecturally pinned commit (short-SHA prefixes ≥ 7 chars
   are accepted, git convention; empty values fail closed). A `VERSION.txt`
   existing at all is NOT evidence of compatibility — the recorded value must
   actually agree with the expected pin.
2. **`moduleOriginVerified`** — after import, the package `__file__` must
   resolve to a path under the expected vendored root. This detects a
   globally installed or shadow copy that won over the vendored snapshot.
   The probe reports the conflict; it never mutates `sys.modules`.

For DBF_Anonymizer, `available` additionally requires `version == 0.3.0`,
the full public API, and `dbfbridgeCompatible` (the shared vendored dbfbridge
pins the commit the anonymizer requires). Any mismatch → `available: false`,
never assumed from the presence of a file.

## Result semantics: PASS / PARTIAL / FAIL

- **PASS** — the operation completed; optional backends may be absent, and
  that is reported in `warnings` (e.g. `VFP9_NOT_INSTALLED`,
  `FOXBIN2PRG_NOT_AVAILABLE`) — an optional runtime being absent on a
  PURE_READ host is a warning, never an error.
- **PARTIAL** — a controlled, explained outcome. `OperationResult.partial()`
  REQUIRES an explicit machine-readable domain `errorCode`
  (`DEPENDENCY_PARTIAL`, `DEPENDENCY_VERSION_MISMATCH`, `CONFIG_ERROR`,
  …) and raises `ValueError` if it is missing. A PARTIAL is therefore never
  mistaken for an unexplained `UNEXPECTED_ERROR`.
- **FAIL** — a hard failure of the requested operation. A FAIL without an
  explicit code defaults to `UNEXPECTED_ERROR` — reserved for genuine,
  unexplained failures, never for controlled partials.
- **`vfp_anonymization_status`** reports subsystem unavailability as PARTIAL
  with the specific domain code (pin mismatch → `DEPENDENCY_VERSION_MISMATCH`,
  otherwise `ANONYMIZER_NOT_AVAILABLE`) — the status query itself succeeded.

## Capability semantics

`vfpEnhancedRead` (VFP_READ_ENHANCED) means **VFP9 runtime present** —
runtime inventory, SYS(3054) profiling and snippet validation need only the
VFP9 executable. It does **not** depend on FoxBin2Prg. FoxBin2Prg is
`EXTERNAL_CONFIGURED` and is a prerequisite for BIN2PRG conversion
operations only (reported as `foxbin2prg.usableForConversion`).
`workspaceWrite` / `buildValidate` remain `false` (roadmap, not yet routed
through the Core Service).

## VFP-enhanced backend (VFP9 + FoxBin2Prg)

`VFP9Backend` exposes cheap availability checks only
(`configured`, `executable_exists`, `enhanced_backend_available`) and never
launches VFP for discovery. Exact version/build verification (5815/7423) stays
in the existing `verno`/`env` operations. FoxBin2Prg remains BIN2PRG-only
against source.

## Future MCP boundary

MCP will be another thin adapter over `VFPToolchainService`. It will add
stdio JSON-RPC / resources / tool registration — nothing else. No domain logic
moves into MCP handlers. Until then: **MCP implemented = false**.
