# MCP VFP9 SP2 Toolchain

Offline-first tooling for analysis, optimization and future controlled refactoring of **Microsoft Visual FoxPro 9.0 Service Pack 2** applications.

Target dialect:

```text
microsoft.visual-foxpro.9.0.sp2
```

Target deployment platform is Windows. The long-term architecture is a **local MCP server** running on a Windows machine that may have Microsoft Visual FoxPro 9 SP2 installed. MCP is **not implemented yet**; current interfaces are CLI/OpenCode adapters.

## Core architectural rule

Visual FoxPro must **not** be required for ordinary read-only inspection.

The target capability split is:

```text
PURE READ                     no VFP required
VFP-enhanced authoritative    VFP9 SP2 required
workspace write/refactor      VFP9 SP2 required
compile/build/REINDEX          VFP9 SP2 required
```

This allows the same future MCP server to provide useful analysis even when VFP is unavailable, while using the installed VFP9 SP2 runtime/compiler as the authoritative backend whenever exact VFP behavior matters.

## VFP9 SP2 role

VFP9 SP2 is the authoritative backend for operations such as:

```text
FoxBin2Prg canonical BIN2PRG conversion
ALANGUAGE()/AMEMBERS() runtime inventory
runtime CDX/DBC introspection
SYS(3054) Rushmore profiling
syntax/compiler validation
COMPILE / COMPILE FORM
BUILD PROJECT / APP / EXE / DLL
REINDEX copied/anonymized tables
controlled form/class/database workspace operations
```

Important known baselines stored in the offline knowledge base:

```text
9.0.0.5815  Visual FoxPro 9 Service Pack 2
9.0.0.7423  SP2 + Microsoft post-SP2 Hotfix baseline
```

The IDE and deployed runtime DLLs must not be assumed to have identical builds.

## PURE READ — must work without VFP

The architecture requires these classes of operation to remain available without installing Visual FoxPro:

- project/artifact detection,
- file manifests and SHA256,
- PRG/H/MPR text reading and search,
- DBF/FPT schema and record export,
- direct read-only inspection of VFP table-based designer artifacts,
- static dependency/symbol analysis,
- code-page/encoding analysis,
- local knowledge and known-issue lookup,
- structural CDX/IDX analysis with explicit heuristic confidence.

Artifact families that the pure reader should understand include:

```text
DBF + optional FPT/CDX/IDX
SCX + SCT
VCX + VCT
FRX + FRT
LBX + LBT
MNX + MNT
PJX + PJT
DBC + DCT + DCX
PRG / H / MPR
```

Pure parsing must not fabricate source from binary fields. Every result should indicate provenance such as:

```text
PURE_PARSER
FOXBIN2PRG
VFP9_RUNTIME
HEURISTIC_CDX
```

When VFP9 is available, enhanced results can verify/supersede pure-parser results without changing the public result schema.

## Core Service (implemented)

The transport-neutral Python Core Service now exists and is used by the CLI
and OpenCode adapters:

```text
OpenCode / CLI (adapters)
        |
        v
src/vfp_toolchain  (Core Service — one code path, no business logic in adapters)
        |
        +-- PurePythonBackend    (PURE_READ: detect, inventory, snapshot, config)
        +-- DBFBridgeBackend    (vendored dbfbridge, pinned)
        +-- DBFAnonymizerBackend (vendored DBF_Anonymizer 0.3.0, status-only in this phase)
        +-- FoxBin2PrgBackend   (EXTERNAL_CONFIGURED, BIN2PRG-only)
        +-- VFP9Backend         (availability checks only; no VFP launch for discovery)
        |
        v
future MCP adapter (ROADMAP — not implemented)
```

Public entry points already available today:

```bash
py vfp_driver.py capabilities                       # PURE_READ, no VFP launch
py vfp_driver.py detect --directory <path>          # PURE_READ
py vfp_driver.py anonymization_status               # read-only privacy subsystem status
```

The OpenCode tools `vfp_capabilities`, `vfp_detect` and
`vfp_anonymization_status` are thin adapters over these operations — detection
logic is no longer duplicated in TypeScript.

See `docs/CORE_SERVICE.md` for the service contract, result model and
dependency pins.

## Offline runtime (implemented)

The Python runtime is a **closed, reproducible dependency set**. On a Windows
machine after installing the offline bundle:

```text
PURE READ      : VFP not required.
Internet       : NOT required at runtime (no PyPI fallback, no network).
VFP9 SP2       : required ONLY for enhanced/runtime/write/build capabilities.
MCP            : not implemented yet.
```

- Lock manifest: `runtime/runtime-dependencies.json` (exact versions + SHA256 per wheel).
- Build (maintainer, network allowed): `scripts/build_offline_bundle.ps1` -> `dist/` (never committed).
- Install (target machine, network FORBIDDEN): `scripts/install_offline.ps1` -> `pip --no-index --find-links <local wheelhouse>`.
- Verify: `scripts/verify_offline_runtime.py` (imports, pins, origin, versions, hashes, capabilities without VFP).
- Tests: `tests/test_offline_install.py` (clean venv, `--no-index`, DBF pure-read fixture, no VFP) and `tests/test_offline_dbf_read.py`.

See `docs/OFFLINE_RUNTIME.md` and `docs/OFFLINE_RUNTIME_DEPENDENCIES.md`.

## Future MCP architecture

MCP is intended to be a thin transport adapter over the same Core Service.

Domain logic must not be duplicated inside future MCP handlers.

See:

- `docs/MCP_TARGET_ARCHITECTURE.md`
- `docs/CORE_SERVICE.md`
- `docs/mcp_capability_model.json`

## Capability classes

Every future operation should declare its requirements:

```text
PURE_READ
PURE_WRITE_COPY
VFP_READ_ENHANCED
VFP_WRITE_WORKSPACE
VFP_BUILD_VALIDATE
PRIVACY_SENSITIVE
```

A future `vfp_capabilities` operation should let clients discover which modes are available on the current host before invoking a tool.

## Data layer — dbfbridge

The repository uses **dbfbridge** as the preferred DBF/FPT data backend:

`https://github.com/PeterPirog/dbfbridge`

The current toolchain already vendors a pinned dbfbridge snapshot under `tools/dbfbridge/` for offline reproducibility.

Its Python API provides data-oriented operations such as:

```text
export_dbf()
reconstruct_dbf()
verify_conversion()
check_conversion_quality()
```

Important capabilities include:

- VFP-independent DBF/FPT access,
- JSONL/JSON/CSV/XLSX export,
- schema metadata,
- memo handling,
- reconstruction,
- checksum/round-trip validation,
- Polish cp1250/cp852/Mazovia handling.

## Data anonymization

The target architecture integrates:

`https://github.com/PeterPirog/DBF_Anonymizer`

through its Python API rather than duplicating anonymization logic.

The upstream public API includes:

```text
anonymize_directory()
make_dbf_recovery()
self_test()
```

Planned toolchain operations:

```text
vfp_anonymize
vfp_anonymize_verify
vfp_anonymize_self_test
vfp_recover_data
```

### When VFP is not required

For DBF/FPT data without structural CDX requirements, anonymization can follow:

```text
DBF/FPT
 -> dbfbridge
 -> DBF_Anonymizer
 -> dbfbridge reconstruction
 -> verification
```

without Visual FoxPro.

### When VFP is required

If anonymized tables use structural CDX, changing indexed values makes the old index contents stale. A valid output therefore requires VFP9 SP2 to rebuild/verify indexes in an isolated copy:

```text
anonymized DBF/FPT
 -> VFP9 REINDEX
 -> runtime tag verification
 -> publish only after PASS
```

The toolchain must never present a copied stale CDX as valid for changed DBF data.

The reversible `dictionary.sqlite3` is a **sensitive secret artifact**. It must not be included in normal audits, logs, model prompts or Git commits. Recovery should be separately disableable in a future server deployment.

See `docs/ANONYMIZATION_INTEGRATION.md`.

## FoxBin2Prg

The VFP-enhanced backend uses FoxBin2Prg:

`https://github.com/fdbozzo/foxbin2prg`

FoxBin2Prg provides canonical text representations of VFP binary designer/project/database artifacts such as:

```text
PJX -> PJ2
SCX -> SC2
VCX -> VC2
FRX -> FR2
LBX -> LB2
MNX -> MN2
DBC -> DC2
DBF -> DB2
```

For **source analysis**, this toolchain uses BIN2PRG only. Source files remain immutable.

FoxBin2Prg requires the VFP environment; therefore it is an enhanced canonical backend, not a dependency for future PURE READ availability.

## Offline VFP9 SP2 knowledge base

Runtime operation is intended to work without Internet access.

The repository stores normative VFP9 SP2 knowledge under `language/`, including:

- language and compatibility rules,
- forms/classes/DataEnvironment,
- DBF/FPT/CDX/IDX/Rushmore,
- DBC/views/CursorAdapter/SPT,
- build/runtime/deployment,
- menus/reports/labels,
- COM/OLE/ActiveX/DLL/FLL,
- known VFP9 SP2 defects and patch levels,
- performance optimization rules,
- capability/completeness gates.

Important files include:

```text
language/README.md
language/VFP9SP2_REQUIRED_KNOWLEDGE.md
language/VFP9SP2_COMPLETE_APPLICATION_KNOWLEDGE.md
language/VFP9SP2_OFFLINE_KNOWLEDGE_AND_ERRATA.md
language/VFP9SP2_PERFORMANCE_OPTIMIZATION.md
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

## Full VFP9 SP2 Help goal

The project should contain a complete offline searchable VFP9 SP2 Help-derived corpus rather than requiring `vfphelp.com` at runtime.

The preferred upstream source is the VFPX HelpFile project, whose README states that Microsoft transferred the VFP9 SP2 Help source/change rights to the VFP community under Creative Commons licensing:

`https://github.com/VFPX/HelpFile`

The architecture should use a **pinned snapshot or normalized generated catalog**, with upstream commit/license/SHA256 provenance. Do not scrape the live web site during requests.

The exact offline Help/catalog gate is not closed yet; see `language/VFP9SP2_KNOWLEDGE_COMPLETENESS_GATE.md`.

## Performance optimization

> Implemented in this branch (see `docs/TOOLCHAIN_IMPROVEMENTS.md` for the full guide):
>
> ```bash
> # Count risky/slow patterns across the whole project (no VFP9 needed)
> opencode vfp_count_patterns --project . --patterns "RLOCK,UNLOCK ALL,SET FILTER,SET OPTIMIZE,SET MULTILOCKS"
>
> # Build the per-procedure performance access map for one form (no VFP9 needed)
> opencode vfp_form_perf --form .vfp-ai/source/forms/karty_pr_pp.sc2 --tables-dir Dane
>
> # Benchmark critical operations BEFORE/AFTER refactoring (VFP9 required)
> opencode vfp_benchmark --project . --table ksiazka_k_d --operation count_for \
>   --expression "LEFT(k_pr_sp_nr,10)='ABC'" --iterations 10
>
> # Find duplicate / similar PROCEDURE blocks in a form (no VFP9 needed)
> opencode vfp_find_duplicates --form .vfp-ai/source/forms/karty_pr_pp.sc2 --min-lines 10
>
> # Run any PRG in VFP9 and capture stdout/stderr/.ERR (VFP9 required)
> opencode vfp_run_prg --prg C:\path\to\my_script.prg --workdir D:\data --timeout 120
> ```

Optimization must be evidence-based rather than stylistic.

The local performance contract requires analysis of, among other things:

```text
Rushmore
SYS(3054)
SET OPTIMIZE
CDX/IDX expressions
functional/composite indexes
FOR vs WHILE
CALCULATE/COUNT/SUM/MIN/MAX
ENGINEBEHAVIOR
code pages/collation
local vs network DBF I/O
locking/buffering/transactions
remote views/SPT/CursorAdapter
form startup/DataEnvironment
Refresh/Paint/Timer hot paths
COM/ActiveX crossings
cold vs warm cache benchmarks
```

Performance findings must distinguish:

```text
MEASURED
RUNTIME_PLAN_CONFIRMED
DOCUMENTED_CANDIDATE
PREDICTED
NOT_TESTED
REJECTED_CORRECTNESS_RISK
```

A predicted speedup must never be presented as measured.

See `language/VFP9SP2_PERFORMANCE_OPTIMIZATION.md`.

## Source safety

The current source-analysis plane is read-only.

Never execute against source/production data during audit:

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

Future write/refactor operations must work only on an explicit workspace copy with source hashes/preconditions.

## Target controlled refactor pipeline

```text
SOURCE immutable
  -> snapshot/hash
  -> pure/enhanced audit
  -> semantic model
  -> RefactorPlan
  -> isolated workspace
  -> VFP9 applies changes
  -> compile/build
  -> reopen
  -> final FoxBin2Prg round-trip
  -> structural/regression comparison
  -> performance validation
  -> PASS -> promote final artifact
```

The existence of this architecture does not mean the current `main` already implements the complete write plane.

## Current state

The executable toolset is a read-only audit/export system with a
transport-neutral Core Service foundation (see above).

High-priority remaining work includes:

1. PURE READ support for all table-based VFP designer artifacts without VFP,
2. full offline Help-derived language catalog,
3. lexer/state-machine semantic parser,
4. runtime language/index/DBC introspection,
5. controlled anonymization tools over the DBF_Anonymizer adapter
   (dependency, adapter and `vfp_anonymization_status` are in place),
6. complete SYS(3054)/benchmark performance subsystem,
7. full DBC/views/CursorAdapter/application dependency audit,
8. controlled VFP9 write/build/refactor pipeline,
9. MCP adapter only after those service contracts stabilize.

See `language/VFP9SP2_CAPABILITY_MATRIX.md` for the authoritative implemented-vs-roadmap status.

## Documentation

- `docs/USAGE.md` — current CLI/OpenCode usage
- `docs/ARTIFACTS.md` — current audit outputs
- `docs/CORE_SERVICE.md` — transport-neutral Core Service contract (implemented)
- `docs/MCP_TARGET_ARCHITECTURE.md` — future MCP-ready service architecture
- `docs/mcp_capability_model.json` — machine-readable runtime capability model
- `docs/ANONYMIZATION_INTEGRATION.md` — privacy/anonymization integration
- `language/README.md` — VFP9 SP2 knowledge architecture
- `language/VFP9SP2_PERFORMANCE_OPTIMIZATION.md` — performance knowledge contract
- `language/VFP9SP2_CAPABILITY_MATRIX.md` — implementation/completeness matrix

## Credits and licensing

Third-party components keep their own licenses and provenance. See `THANKS.md`.

Primary related projects:

- FoxBin2Prg — `https://github.com/fdbozzo/foxbin2prg`
- dbfbridge — `https://github.com/PeterPirog/dbfbridge`
- DBF_Anonymizer — `https://github.com/PeterPirog/DBF_Anonymizer`
- VFPX VFP9 SP2 HelpFile — `https://github.com/VFPX/HelpFile`

This project does not replace Microsoft Visual FoxPro 9.0 SP2. When installed, VFP9 SP2 remains the authoritative runtime/compiler backend for operations that depend on exact VFP execution semantics.
