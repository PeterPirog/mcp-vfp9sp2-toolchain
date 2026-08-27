# VFP9 SP2 capability matrix — knowledge vs implementation

This matrix separates two different claims:

1. **KNOWLEDGE AVAILABLE** — the repository contains enough normative information to design/analyze the domain.
2. **TOOL IMPLEMENTED** — the current code actually extracts, validates or refactors that domain.

Do not claim full application support when only the knowledge contract exists.

| Domain | Knowledge contract | Current implementation on main | Status |
|---|---|---|---|
| Core VFP9 SP2 syntax/versioning | `vfp9sp2_core_spec.json`, runtime inventory contract | partial parser + VFP/FoxBin2Prg integration | PARTIAL IMPLEMENTATION |
| Forms SCX/SCT | `vfp9sp2_forms_spec.json` | BIN2PRG export + regex SC2 indexing; no validated write plane yet | PARTIAL IMPLEMENTATION |
| Classes VCX/VCT | forms/core specs | BIN2PRG + class indexing | PARTIAL IMPLEMENTATION |
| DBF/FPT schema/data | required knowledge + data spec | strong dbfbridge export path | IMPLEMENTED FOR AUDIT |
| CDX/IDX | index/Rushmore spec | structural heuristic parser + limited VFP enrichment | PARTIAL / HEURISTIC |
| Rushmore/SYS(3054) | index/Rushmore spec | not yet complete automated runtime profiling | KNOWLEDGE ONLY / ROADMAP |
| DBC metadata | data-access DBC spec | only partial conversion/inference; no complete DBC semantic catalog | PARTIAL |
| Local/remote views | data-access DBC spec | no full structured audit | KNOWLEDGE ONLY / ROADMAP |
| CursorAdapter | data-access DBC spec | no dedicated semantic extraction | KNOWLEDGE ONLY / ROADMAP |
| SQL Pass-Through | data-access DBC spec | text references may be found, no semantic connection lifecycle audit | KNOWLEDGE ONLY / ROADMAP |
| Locking/buffering/transactions | required/data spec | mostly text analysis, no dedicated state model | PARTIAL |
| Project PJX/PJT/main/build | application-build-runtime spec | conversion/detection only; no build graph or build validation | KNOWLEDGE ONLY / ROADMAP |
| READ EVENTS/CLEAR EVENTS lifecycle | application-build-runtime spec | no application lifecycle model | KNOWLEDGE ONLY / ROADMAP |
| CONFIG.FPW/runtime configuration | application-build-runtime spec | no complete effective configuration resolver | KNOWLEDGE ONLY / ROADMAP |
| Menu MNX/MNT/MPR | UI/report/menu spec | BIN2PRG supports MNX, no semantic menu graph | PARTIAL |
| Reports FRX/FRT | UI/report/menu spec | BIN2PRG export, no complete report semantic model | PARTIAL |
| Labels LBX/LBT | UI/report/menu spec | detection/conversion path exists; companion handling must use LBT | PARTIAL |
| COM/OLE/ActiveX | UI/report/menu spec | no dependency resolver | KNOWLEDGE ONLY / ROADMAP |
| DLL/FLL native integrations | UI/report/menu spec | no dedicated signature/dependency audit | KNOWLEDGE ONLY / ROADMAP |
| Deployment/runtime dependencies | application-build-runtime spec | no deployment manifest | KNOWLEDGE ONLY / ROADMAP |
| Safe refactor workspace | required/forms specs | not implemented on current main read-only architecture | ROADMAP |
| Compile/round-trip validation | required/forms specs | not implemented as write/refactor tool API | ROADMAP |
| Performance benchmarking | index/Rushmore contract | not complete on current main | ROADMAP |

## Current architectural conclusion

The repository now contains a broad enough **knowledge contract** to plan a complete VFP9 SP2 application toolchain, but the current executable toolset on `main` is still primarily a read-only audit/export system.

The following claims must therefore NOT be made yet:

- "can rebuild every VFP application from audit output",
- "complete audit" without domain completeness flags,
- "fully understands DBC/views/connections",
- "can safely refactor SCX/SCT" until the controlled write plane exists,
- "FULL Rushmore" without SYS(3054) evidence,
- "production-ready optimized form" without compile/round-trip/regression validation.

## Required implementation phases

### P0 safety and correctness

- remove global kill of unrelated VFP9 processes,
- enforce SHA256 source immutability in code,
- fix LBX companion from `.lb2` to `.lbt`,
- fix sync completeness semantics,
- mark raw CDX parsing as heuristic.

### P1 language/semantic parser

- runtime language inventory tools,
- lexer/state-machine parser instead of regex-only routines,
- actual PROCEDURE/FUNCTION line ranges,
- work-area/data-flow model,
- project SET/environment model.

### P2 application audit

- PJX/PJT dependency and main-program graph,
- DBC tables/rules/triggers/stored procedures/views/connections,
- DataEnvironment/CursorAdapter semantic extraction,
- menu/report/label semantic extraction,
- COM/OCX/DLL/FLL dependency manifest,
- CONFIG.FPW and deployment environment manifest.

### P3 performance audit

- query/xBase operation inventory,
- runtime index introspection,
- SYS(3054) profiling,
- exact index-expression matching,
- benchmark harness with warm/cold distinction,
- measured vs predicted optimization statuses.

### P4 controlled refactor/build

- isolated workspace,
- RefactorPlan preconditions/hashes,
- VFP9 code/form patch application,
- `COMPILE FORM` and other compile/build commands,
- final BIN2PRG round-trip,
- structural and functional regression validation,
- promotion only after PASS.

## Completeness protocol

Every audit should eventually emit domain-level statuses such as:

```text
LANGUAGE
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
PERFORMANCE
REFACTOR_VALIDATION
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
```

A top-level `COMPLETE` may only be returned when every domain required by the detected project artifact/dependency graph is complete or explicitly not applicable.
