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
