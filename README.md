# VFP Integration Toolchain for OpenCode

Offline-first integration between OpenCode AI agents and **Microsoft Visual FoxPro 9.0 Service Pack 2** projects.

> **Target platform:** Microsoft Visual FoxPro 9.0 SP2 (`microsoft.visual-foxpro.9.0.sp2`).
>
> The toolchain is designed specifically around VFP9 SP2 language, file formats, SQL engine behavior, forms/classes, DBF/FPT/CDX/IDX data access, DBC metadata, Rushmore, reporting, project/build/runtime semantics and known VFP9 SP2 defects. Older FoxPro/VFP versions may be analyzed as legacy input, but they are not the generation/refactoring target unless compatibility behavior is explicitly modeled.

The current `main` branch is primarily a **strict read-only audit and reverse-engineering plane**. The repository also contains the normative knowledge and architecture required for future controlled refactoring/build support, but those write capabilities must not be confused with what is already implemented.

## VFP9 SP2 requirement

For VFP binary conversion and runtime/compiler validation, a locally installed Microsoft Visual FoxPro 9.0 SP2 environment is required.

The toolchain must identify the exact build rather than merely finding `vfp9.exe`.

Important baselines in the local offline knowledge base are:

```text
9.0.0.5815  Visual FoxPro 9 Service Pack 2
9.0.0.7423  VFP9 SP2 + Microsoft post-SP2 Hotfix baseline
```

A patched SP2 installation must not be rejected simply because its build is later than 5815.

Where deployed runtime DLLs are audited, their versions must also be recorded; the developer IDE and deployed VFP runtime are not assumed to have identical patch levels.

## Offline-first design

The runtime toolchain is intended to work without Internet access.

Operational VFP knowledge lives under `language/` and includes:

- VFP9 SP2 language and semantic rules,
- form/class and SCX/SCT knowledge,
- DBF/FPT/CDX/IDX and Rushmore rules,
- DBC/views/CursorAdapter/SPT knowledge,
- application lifecycle, project/build/runtime semantics,
- menus/reports/labels and external integrations,
- system limits,
- known VFP9/SP2 defects and workarounds,
- patch-level guidance and offline diagnostic policy.

Internet URLs inside the knowledge base are provenance for maintainers, not runtime dependencies.

If an observed defect is not in the local known-issues catalog and cannot be established from the local VFP runtime/project evidence, the agent must return `KNOWN_ISSUE_NOT_FOUND` rather than inventing a workaround.

## Knowledge contract

The complete knowledge layer is defined by the files in `language/`, especially:

```text
language/README.md
language/VFP9SP2_REQUIRED_KNOWLEDGE.md
language/VFP9SP2_COMPLETE_APPLICATION_KNOWLEDGE.md
language/VFP9SP2_OFFLINE_KNOWLEDGE_AND_ERRATA.md
language/VFP9SP2_KNOWLEDGE_COMPLETENESS_GATE.md
language/VFP9SP2_CAPABILITY_MATRIX.md
language/vfp9sp2_known_issues.json
language/vfp9sp2_core_spec.json
language/vfp9sp2_forms_spec.json
language/vfp9sp2_indexes_rushmore_spec.json
language/vfp9sp2_application_build_runtime_spec.json
language/vfp9sp2_data_access_dbc_spec.json
language/vfp9sp2_ui_reports_menus_integration_spec.json
language/vfp9sp2_language.schema.json
language/extract_vfp9sp2_runtime_inventory.prg
```

### Important knowledge-status distinction

The repository already has broad **domain knowledge**, but it does not yet contain a fully exhaustive offline catalog of every VFP9 SP2 command/function/PEM signature and syntax variant.

Current knowledge-gate state:

```text
DOMAIN_KNOWLEDGE               READY
OFFLINE_ERRATA                 READY
RUNTIME_INTROSPECTION_SPEC     READY
EXACT_OFFLINE_LANGUAGE_CATALOG INCOMPLETE
AUTONOMOUS_CODE_GENERATION     BLOCKED_BY_KNOWLEDGE_GATE
```

See `language/VFP9SP2_KNOWLEDGE_COMPLETENESS_GATE.md`.

The installed VFP9 SP2 compiler/runtime remains the final syntax authority for changed/generated code.

## Current architecture

### Analyze plane — implemented/current

The source project is treated as immutable.

Core rules:

```text
No source modification
No PRG2BIN against source
BIN2PRG only for source designer artifacts
Audit/export output goes outside source or to .vfp-ai
Source integrity must be verifiable
```

Current capabilities include, depending on the installed environment:

- detection of VFP project artifacts,
- FoxBin2Prg BIN2PRG export of VFP designer files,
- SC2/VC2 indexing and symbol/reference search,
- DBF/FPT schema and data export,
- CDX/IDX structural analysis with confidence limitations,
- project-level audit artifacts,
- class/form/source reverse engineering.

### Controlled refactor/build plane — architecture/roadmap

The intended write path is:

```text
SOURCE (immutable)
   |
   v
BIN2PRG / audit / semantic model
   |
   v
RefactorPlan with hashes/preconditions
   |
   v
isolated workspace copy
   |
   v
VFP9 SP2 applies changes
   |
   v
COMPILE / COMPILE FORM / BUILD as appropriate
   |
   v
final BIN2PRG round-trip
   |
   v
source/final structural comparison
   |
   v
regression + performance validation
   |
   v
PASS -> final artifact
```

Do not assume these write/refactor operations are already fully implemented merely because the knowledge contract describes them.

## Capability truthfulness

`language/VFP9SP2_CAPABILITY_MATRIX.md` is the authoritative distinction between:

1. knowledge available in the repository, and
2. executable tooling implemented on `main`.

A domain must not be reported `COMPLETE` if it is only partially parsed, heuristic, unknown or roadmap-only.

In particular, current `main` must not claim that audit output alone is guaranteed to reconstruct every arbitrary VFP9 SP2 application. A complete application can depend on DBC semantics, local/remote views, CursorAdapter, external COM/ActiveX/DLL/FLL dependencies, CONFIG.FPW, reports/menus, dynamic paths/macros and deployment state that must also be captured and validated.

## Installation prerequisites

For the complete current audit workflow on Windows:

| Component | Purpose |
|---|---|
| **Microsoft Visual FoxPro 9.0 SP2** | VFP runtime/COM host and authoritative runtime/compiler environment |
| **FoxBin2Prg** | Binary-to-text conversion of VFP designer artifacts |
| **Python 3** | Toolchain orchestration and DBF/audit tooling |
| **OpenCode** | AI/tool integration layer |

DBF/FPT export paths can operate without VFP9 through the bundled/Python data tooling, but that does not make the whole VFP application audit independent of VFP9.

Environment variables:

```text
VFP_TOOLCHAIN_HOME
VFP_FOXBIN2PRG_DIR
VFP9_EXE
```

## Quick start

```bash
git clone https://github.com/PeterPirog/vfp-integration-toolchain.git
cd vfp-integration-toolchain
py -m pip install dbfread orjson xlsxwriter openpyxl dbf
py install.py --foxbin2prg-dir "C:\path\to\foxbin2prg"
```

Then in a VFP9 SP2 project:

```text
vfp_status
vfp_detect --directory <PROJECT_DIR>
vfp_sync --directory <PROJECT_DIR>
vfp_audit --source <PROJECT_DIR> --out <AUDIT_DIR>
```

When using the audit output, inspect the domain completeness statuses rather than assuming every VFP subsystem was fully captured.

## Main OpenCode agent

`@vfp-analyst` is the read-only analysis agent.

It is required to use the local VFP9 SP2 knowledge contract, distinguish runtime facts from heuristics and avoid claiming unsupported completeness.

Typical requests:

```text
@vfp-analyst analyze this VFP9 SP2 project
@vfp-analyst find all references to CUSTOMERS
@vfp-analyst analyze the indexes used by this form
@vfp-analyst identify known VFP9 SP2 engine issues relevant to this code
```

## VFP artifacts

The toolchain recognizes VFP artifact families including:

```text
PRG / H
PJX + PJT
SCX + SCT
VCX + VCT
FRX + FRT
LBX + LBT
MNX + MNT
DBC + DCT + DCX
DBF + optional FPT + CDX/IDX
MPR / MPX
APP / EXE / FXP
DLL / FLL / OCX / TLB
CONFIG.FPW
```

Important: `.lb2` is a FoxBin2Prg text representation; `.lbt` is the binary memo companion for `.lbx`.

## Data and index analysis

The toolchain knowledge model distinguishes native xBase access from VFP SQL, including:

```text
USE / SELECT work area
SCAN / LOCATE / SEEK / INDEXSEEK
CALCULATE / COUNT / SUM / AVERAGE
REPLACE / APPEND / DELETE / RECALL
SELECT-SQL / INSERT-SQL / UPDATE-SQL / DELETE-SQL
views / CursorAdapter / SQL Pass-Through
```

Index/Rushmore analysis must consider:

```text
CDX vs IDX
key expression
filtered-index FOR expression
active order/tag
field types and key byte limits
collation/code page
SET ENGINEBEHAVIOR
SET OPTIMIZE
SYS(3054) evidence
```

The presence of a similar-looking index is not sufficient proof of FULL Rushmore optimization.

## Forms and classes

For source-level analysis, SCX/SCT and VCX/VCT are converted to FoxBin2Prg text representations.

A safe future form refactor must preserve or explicitly authorize changes to:

- object hierarchy,
- class/base-class information,
- layout/properties,
- DataEnvironment/DataSession behavior,
- methods/events,
- data bindings,
- work-area/index state.

A final modified form is not accepted merely because the `.scx/.sct` files exist. The architecture requires compile, VFP reopen, final BIN2PRG round-trip, structural comparison and regression validation.

## Known VFP9 SP2 defects

The offline known-issues subsystem stores patch-level and workaround information locally.

Examples covered by the local knowledge base include:

- VFP9 SP2 vs post-SP2 hotfix build differences,
- grouped-report defect addressed by Microsoft's post-SP2 hotfix,
- ENGINEBEHAVIOR/code-page/Rushmore correctness traps,
- historical form/DataSession/Grid/ListBox issues,
- SQL/SPT/CursorAdapter/index edge cases,
- report/ReportListener/ReportingApps issues,
- table corruption and validation policy,
- system capacity/index-key limits,
- ActiveX/deployment risks.

The catalog deliberately distinguishes Microsoft/VFPX-confirmed behavior from community-only or environment-dependent claims.

## Safety

The current source-analysis plane is read-only.

Never perform these against production/source data during audit:

```text
PRG2BIN
REINDEX
PACK
ZAP
ALTER TABLE
INDEX ON
DELETE TAG
uncontrolled DBF/DBC writes
```

Experiments and future refactoring must operate on explicit copies/workspaces.

## Current important limitations

Before proceeding to unrestricted automated refactoring, the following remain significant implementation/knowledge gates:

- exact offline catalog of every VFP9 SP2 command/function/PEM syntax is not yet complete,
- current SC2/VC2 parser still needs a proper lexer/state-machine semantic parser,
- complete runtime language inventory tooling is not yet exposed as a finished OpenCode subsystem,
- DBC/views/CursorAdapter/SPT semantic extraction is not yet complete,
- CDX binary parsing must not be treated as authoritative without runtime confirmation,
- automated SYS(3054) profiling/benchmarking is not yet complete,
- controlled write/refactor/build plane is not yet complete.

See `language/VFP9SP2_CAPABILITY_MATRIX.md` and `language/VFP9SP2_KNOWLEDGE_COMPLETENESS_GATE.md` before planning the next implementation phase.

## Documentation

- `docs/USAGE.md` — practical CLI/tool usage
- `docs/ARTIFACTS.md` — current audit outputs
- `language/README.md` — VFP9 SP2 knowledge architecture
- `language/VFP9SP2_KNOWLEDGE_COMPLETENESS_GATE.md` — hard knowledge-completeness gate
- `language/VFP9SP2_CAPABILITY_MATRIX.md` — implemented vs roadmap capability matrix
- `language/VFP9SP2_OFFLINE_KNOWLEDGE_AND_ERRATA.md` — offline defects/limits/remediation knowledge

## Credits

The toolchain relies on FoxBin2Prg by Fabio Zadro for VFP binary/text conversion and includes/uses other open-source components as documented in `THANKS.md` and the repository dependency files.

This project does not replace Microsoft Visual FoxPro 9.0 SP2. It uses the locally installed VFP9 SP2 runtime/compiler as the authoritative execution and validation environment.
