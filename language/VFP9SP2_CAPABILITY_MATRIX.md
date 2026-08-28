# VFP9 SP2 capability matrix — knowledge vs implementation

This matrix separates three different claims:

1. **KNOWLEDGE AVAILABLE** — the repository contains enough normative information to design/analyze the domain.
2. **TOOL IMPLEMENTED** — the current code actually extracts, validates or refactors that domain.
3. **RUNTIME REQUIREMENT** — whether the operation must work without Visual FoxPro or requires the installed VFP9 SP2 backend.

Do not claim full application support when only the knowledge contract exists.

| Domain | Knowledge contract | Current implementation on main | Runtime target | Status |
|---|---|---|---|---|
| Core VFP9 SP2 syntax/versioning | `vfp9sp2_core_spec.json`, runtime inventory contract | partial parser + VFP/FoxBin2Prg integration | pure static read + optional VFP validation | PARTIAL IMPLEMENTATION |
| Offline full VFP9 SP2 Help/catalog | knowledge gate + VFPX Help plan | full normalized/vendored corpus not yet present | PURE_READ | KNOWLEDGE GAP |
| Forms SCX/SCT | `vfp9sp2_forms_spec.json` | BIN2PRG export + regex SC2 indexing; no validated write plane yet | pure raw/table read target; VFP enhanced conversion | PARTIAL IMPLEMENTATION |
| Classes VCX/VCT | forms/core specs | BIN2PRG + class indexing | pure raw/table read target; VFP enhanced conversion | PARTIAL IMPLEMENTATION |
| DBF/FPT schema/data | required knowledge + data spec | strong vendored dbfbridge export path | PURE_READ / PURE_WRITE_COPY | IMPLEMENTED FOR AUDIT |
| DBF reconstruction/quality | dbfbridge integration | vendored dbfbridge supports reconstruction/verification | no VFP for DBF/FPT core | IMPLEMENTED BACKEND, PARTIAL TOOL SURFACE |
| Data anonymization | `docs/ANONYMIZATION_INTEGRATION.md` | DBF_Anonymizer 0.3.0 vendored + adapter + `vfp_anonymization_status` (read-only); controlled mutating tools are next phase | no VFP without structural CDX; VFP required for valid CDX rebuild | DEPENDENCY + ADAPTER IMPLEMENTED / MUTATING TOOLS NEXT PHASE |
| Anonymization recovery | privacy contract | recovery capability present in vendored package; NOT exposed as a tool (restricted by design) | PRIVACY_SENSITIVE | ROADMAP / RESTRICTED |
| CDX/IDX | index/Rushmore spec | structural heuristic parser + limited VFP enrichment | pure heuristic read + VFP authoritative enrichment | PARTIAL / HEURISTIC |
| Rushmore/SYS(3054) | index/Rushmore + performance spec | not yet complete automated runtime profiling | VFP_READ_ENHANCED | KNOWLEDGE ONLY / ROADMAP |
| Performance optimization | `VFP9SP2_PERFORMANCE_OPTIMIZATION.md` | partial audits, no complete evidence/benchmark engine | mixed pure static + VFP runtime | KNOWLEDGE READY / IMPLEMENTATION PARTIAL |
| DBC metadata | data-access DBC spec | only partial conversion/inference; no complete DBC semantic catalog | pure raw read target + VFP enhanced | PARTIAL |
| Local/remote views | data-access DBC spec | no full structured audit | pure source/DBC read + optional VFP | KNOWLEDGE ONLY / ROADMAP |
| CursorAdapter | data-access DBC spec | no dedicated semantic extraction | PURE_READ source + optional VFP validation | KNOWLEDGE ONLY / ROADMAP |
| SQL Pass-Through | data-access DBC spec | text references may be found, no semantic connection lifecycle audit | PURE_READ source | KNOWLEDGE ONLY / ROADMAP |
| Locking/buffering/transactions | required/data spec | mostly text analysis, no dedicated state model | PURE_READ + VFP runtime validation | PARTIAL |
| Project PJX/PJT/main/build | application-build-runtime spec | conversion/detection only; no build graph or build validation | pure read target; VFP required for build | KNOWLEDGE ONLY / ROADMAP |
| READ EVENTS/CLEAR EVENTS lifecycle | application-build-runtime spec | no application lifecycle model | PURE_READ | KNOWLEDGE ONLY / ROADMAP |
| CONFIG.FPW/runtime configuration | application-build-runtime spec | no complete effective configuration resolver | PURE_READ | KNOWLEDGE ONLY / ROADMAP |
| Menu MNX/MNT/MPR | UI/report/menu spec | BIN2PRG supports MNX, no semantic menu graph | pure raw read target + VFP enhanced | PARTIAL |
| Reports FRX/FRT | UI/report/menu spec | BIN2PRG export, no complete report semantic model | pure raw read target + VFP enhanced | PARTIAL |
| Labels LBX/LBT | UI/report/menu spec | detection/conversion path exists; companion handling uses LBT | pure raw read target + VFP enhanced | PARTIAL |
| COM/OLE/ActiveX | UI/report/menu spec | no dependency resolver | PURE_READ source/artifact analysis | KNOWLEDGE ONLY / ROADMAP |
| DLL/FLL native integrations | UI/report/menu spec | no dedicated signature/dependency audit | PURE_READ | KNOWLEDGE ONLY / ROADMAP |
| Deployment/runtime dependencies | application-build-runtime spec | no deployment manifest | PURE_READ | KNOWLEDGE ONLY / ROADMAP |
| Pure-read designer parser | MCP target architecture | not implemented as complete normalized reader | MUST work without VFP | ROADMAP / HIGH PRIORITY |
| Capability discovery | `docs/mcp_capability_model.json` | `vfp_capabilities` implemented in Core Service + CLI + OpenCode (PURE_READ, no VFP launch) | PURE_READ | IMPLEMENTED PURE_READ |
| Transport-neutral Python service layer | `docs/MCP_TARGET_ARCHITECTURE.md` | `src/vfp_toolchain` core service + backends; CLI/OpenCode are thin adapters; `vfp_detect` routed through core | no VFP required for core dispatch | IMPLEMENTED (foundation) |
| Offline Python runtime closure | `docs/OFFLINE_RUNTIME.md`, `runtime/runtime-dependencies.json` | pinned wheelhouse + SHA256 lock + `--no-index` installer + offline verification + clean-venv install test | no VFP, no network at runtime | IMPLEMENTED |
| OpenCode vfp_detect through Core | MCP target architecture | `tools/vfp.ts` `vfp_detect` is a thin adapter over `vfp_driver.py detect` (no duplicated walk) | PURE_READ | IMPLEMENTED PURE_READ |
| dbfbridge adapter | `tools/VENDORED_DEPENDENCIES.json` | `DBFBridgeBackend` wraps the pinned vendored public API | no VFP | IMPLEMENTED |
| MCP server | MCP target architecture | intentionally not implemented yet | Windows target | FUTURE ROADMAP |
| Safe refactor workspace | required/forms specs | not implemented on current main read-only architecture | VFP_WRITE_WORKSPACE | ROADMAP |
| Compile/round-trip validation | required/forms specs | not implemented as write/refactor tool API | VFP_BUILD_VALIDATE | ROADMAP |
| Performance benchmarking | performance contract | not complete on current main | VFP runtime often required | ROADMAP |

## Current architectural conclusion

The repository contains a broad enough **domain knowledge contract** to plan a complete VFP9 SP2 application service, but the current executable toolset on `main` is still primarily a read-only audit/export system.

The target architecture is now explicitly **MCP-ready but not MCP-implemented**. The transport-neutral Core Service foundation (`src/vfp_toolchain`) is implemented: capability discovery, project detection, dependency adapters and the shared result model exist, and the CLI/OpenCode adapters call it. A future MCP server will be another thin adapter over the same service.

The following claims must therefore NOT be made yet:

- "can rebuild every VFP application from audit output",
- "complete audit" without domain completeness flags,
- "fully understands DBC/views/connections",
- "can safely refactor SCX/SCT" until the controlled write plane exists,
- "FULL Rushmore" without SYS(3054) evidence,
- "production-ready optimized form" without compile/round-trip/regression validation,
- "all READ operations work without VFP" until the pure designer readers are implemented,
- "anonymization is integrated" until the controlled anonymize/verify/self-test tools exist (only the vendored dependency, adapter and read-only status are in place),
- "MCP server available" before the transport adapter is actually implemented.

## Capability classes

All future service operations should declare one or more runtime/safety classes:

```text
PURE_READ
PURE_WRITE_COPY
VFP_READ_ENHANCED
VFP_WRITE_WORKSPACE
VFP_BUILD_VALIDATE
PRIVACY_SENSITIVE
```

`PURE_READ` must never require Visual FoxPro installation.

## Required implementation phases

### P0 safety and correctness

- remove global kill of unrelated VFP9 processes,
- enforce SHA256 source immutability in code,
- preserve correct companion handling such as LBX+LBT,
- fix sync completeness semantics,
- mark raw CDX parsing as heuristic,
- centralize Windows path-safety rules.

### P1 transport-neutral core + pure READ

- create typed Python core service/models/errors/capabilities,
- make OpenCode/CLI thin adapters,
- expose `vfp_capabilities`,
- implement direct read-only DBF/FPT and designer-table/memo readers,
- make SCX/VCX/FRX/LBX/MNX/PJX/DBC READ available without VFP,
- retain provenance/confidence for pure parser vs FoxBin2Prg/VFP runtime,
- build conformance tests comparing pure parser with FoxBin2Prg when VFP exists.

### P2 language/semantic parser

- complete runtime language inventory tools,
- lexer/state-machine parser instead of regex-only routines,
- actual PROCEDURE/FUNCTION line ranges,
- work-area/data-flow model,
- project SET/environment model,
- normalized offline full VFP9 SP2 Help-derived catalog.

### P3 privacy/anonymization

- integrate a pinned DBF_Anonymizer snapshot through Python API,
- share one compatible dbfbridge backend version,
- add anonymize/verify/self-test tools,
- protect dictionary/salt/logging,
- support no-VFP DBF/FPT path,
- require VFP9 REINDEX for structural-CDX anonymized output,
- verify source hashes and atomic publication.

### P4 application audit

- PJX/PJT dependency and main-program graph,
- DBC tables/rules/triggers/stored procedures/views/connections,
- DataEnvironment/CursorAdapter semantic extraction,
- menu/report/label semantic extraction,
- COM/OCX/DLL/FLL dependency manifest,
- CONFIG.FPW and deployment environment manifest.

### P5 performance audit

- query/xBase operation inventory,
- runtime index introspection,
- SYS(3054) profiling,
- exact index-expression matching,
- benchmark harness with warm/cold distinction,
- local/network/remote-backend context,
- measured vs predicted optimization statuses.

### P6 controlled refactor/build

- isolated workspace,
- RefactorPlan preconditions/hashes,
- VFP9 code/form patch application,
- `COMPILE FORM` and other compile/build commands,
- final BIN2PRG round-trip,
- structural and functional regression validation,
- promotion only after PASS.

### P7 MCP adapter

Only after the service contracts are stable:

- implement Windows MCP server adapter,
- expose read-only resources and explicit mutation tools,
- enforce allowed read/output/workspace/sensitive roots,
- isolate or serialize VFP COM workers,
- do not duplicate domain logic inside MCP handlers.

## Completeness protocol

Every audit should eventually emit domain-level statuses such as:

```text
LANGUAGE
OFFLINE_HELP
PROJECT_BUILD
APPLICATION_LIFECYCLE
FORMS
CLASSES
MENUS
REPORTS_LABELS
DATAENV
DBF_SCHEMA
DBF_DATA
CDX_INDEXES
DBC_METADATA
VIEWS_CONNECTIONS
CURSOR_ADAPTER
SQL_PASS_THROUGH
LOCKING_BUFFERING
EXTERNAL_DEPENDENCIES
DEPLOYMENT
PRIVACY_ANONYMIZATION
PERFORMANCE
REFACTOR_VALIDATION
MCP_SERVICE_READINESS
```

Allowed states:

```text
COMPLETE
PARTIAL
HEURISTIC
UNKNOWN
NOT_IMPLEMENTED
MEASURED
PREDICTED
NOT_APPLICABLE
```

A top-level `COMPLETE` may only be returned when every domain required by the detected project artifact/dependency graph is complete or explicitly not applicable.
