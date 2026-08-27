# Microsoft Visual FoxPro 9.0 SP2 — executable knowledge specification

Target dialect:

`microsoft.visual-foxpro.9.0.sp2`

This directory is the normative knowledge layer for `vfp-integration-toolchain` and OpenCode agents that analyze, optimize, refactor or generate Visual FoxPro 9.0 SP2 applications.

## Core architectural rule

The LLM is **not** the syntax or semantics authority.

Use three verification layers:

1. documented VFP9 SP2 syntax/semantics,
2. runtime inventory from the exact installed VFP9 SP2,
3. VFP9 compiler/runtime validation of generated or changed code.

Production changes must never depend on `UNVERIFIED` or merely `HEURISTIC` language facts.

## Mandatory knowledge files

Every complete audit/refactor/build agent must treat all of the following as one contract:

- `VFP9SP2_REQUIRED_KNOWLEDGE.md` — core mandatory language, work-area, forms, DBF/CDX/DBC, Rushmore and validation knowledge.
- `VFP9SP2_COMPLETE_APPLICATION_KNOWLEDGE.md` — complete application lifecycle: PJX/build/startup, CONFIG.FPW, DBC/views, CursorAdapter, SPT, menus, reports, labels, COM/ActiveX/DLL/FLL and deployment.
- `VFP9SP2_CAPABILITY_MATRIX.md` — separates knowledge present in the repo from executable capabilities actually implemented.
- `vfp9sp2_core_spec.json` — machine-readable lexical/core language and environment model.
- `vfp9sp2_forms_spec.json` — form/class/SCX-SCT/DataEnvironment validation model.
- `vfp9sp2_indexes_rushmore_spec.json` — CDX/IDX/SEEK/Rushmore model.
- `vfp9sp2_application_build_runtime_spec.json` — PJX/PJT, build, event-loop, CONFIG.FPW and deployment model.
- `vfp9sp2_data_access_dbc_spec.json` — DBC/views/CursorAdapter/SPT/buffering/locking/transactions model.
- `vfp9sp2_ui_reports_menus_integration_spec.json` — menus, reports, labels, COM/OLE/ActiveX and DLL/FLL integration model.
- `vfp9sp2_language.schema.json` — normalized schema for individual language facts.
- `extract_vfp9sp2_runtime_inventory.prg` — command/function/class/PEM inventory from the exact VFP installation.

A tool or agent that does not load or implement the domains relevant to the detected project must report the knowledge/audit result as `PARTIAL`, not `COMPLETE`.

## Source-of-truth priority

1. Installed Microsoft Visual FoxPro 9 SP2 runtime/compiler:
   - `VERSION()` / `VERSION(1)` / `VERSION(5)`
   - `SYS(3099)`
   - `CPCURRENT()`
   - `ALANGUAGE()`
   - `AMEMBERS()`
   - `APROCINFO()`
   - `COMPILE`, `COMPILE FORM` and other relevant compile/build operations.
2. Microsoft VFP9 SP2 Help / VFPX Help mirror.
3. FoxBin2Prg text representation for safe analysis and round-trip comparison.
4. Community references only as supporting evidence.

## Confidence statuses

Language and semantic facts should use statuses such as:

- `VERIFIED_RUNTIME_AND_HELP`
- `VERIFIED_HELP`
- `VERIFIED_RUNTIME`
- `BACKWARD_COMPATIBLE`
- `VERSION_DEPENDENT`
- `PROJECT_ENVIRONMENT_DEPENDENT`
- `HEURISTIC`
- `UNVERIFIED`
- `INVALID_FOR_VFP9SP2`

## Runtime language inventory

VFP9 SP2 exposes its language inventory through:

```foxpro
ALANGUAGE(ArrayName, 1) && commands
ALANGUAGE(ArrayName, 2) && functions + parameter metadata
ALANGUAGE(ArrayName, 3) && base classes
ALANGUAGE(ArrayName, 4) && DBC events
```

Use `AMEMBERS()` to enumerate class/object properties, methods and events.

Runtime inventory confirms that an element exists. Documentation is still needed for exact syntax and semantics.

## Parser requirements

A reliable parser must not be a set of independent regexes over raw lines. It must understand before command parsing:

- VFP comments `*` and `&&`,
- line continuation `;`,
- single/double/square-bracket strings,
- `.T.`, `.F.`, `.NULL.`, date literals,
- macro substitution `&`,
- preprocessor directives,
- `PROCEDURE/FUNCTION` and block nesting,
- work-area state and ambiguous command families.

Required block families include `IF/ENDIF`, `DO CASE/ENDCASE`, `DO WHILE/ENDDO`, `FOR/ENDFOR`, `SCAN/ENDSCAN`, `TRY/ENDTRY`, `WITH/ENDWITH`, `TEXT/ENDTEXT`, `DEFINE CLASS/ENDDEFINE`, `PROCEDURE/ENDPROC`, and `FUNCTION/ENDFUNC`.

## Semantic distinctions that must never be collapsed

- work-area `SELECT` vs `SELECT - SQL`,
- xBase `DELETE` vs `DELETE - SQL`,
- historical/xBase `INSERT` vs `INSERT - SQL`,
- historical `UPDATE` vs `UPDATE - SQL`,
- `SEEK` command vs `SEEK()` vs `INDEXSEEK()`,
- physical DBF vs view/cursor/temporary cursor,
- source method text vs compiled object code,
- structural CDX tags vs standalone IDX,
- key expression vs filtered-index `FOR` expression,
- DBC relationship metadata vs inferred source-code co-occurrence.

## Version-dependent SQL

Always record the effective SQL engine mode:

```foxpro
SET ENGINEBEHAVIOR 70 | 80 | 90
```

and/or:

```foxpro
SYS(3099)
```

`SET COMPATIBLE` is a separate compatibility mechanism.

Do not judge VFP9 syntax by VFP7/VFP8 limits or semantics.

## Forms and visual classes

Treat VFP designer artifacts atomically:

```text
SCX + SCT
VCX + VCT
FRX + FRT
LBX + LBT
MNX + MNT
PJX + PJT
DBC + DCT + DCX
```

Note: `.lb2` is a FoxBin2Prg text representation, **not** the binary Label Designer memo companion; `.lbt` is the companion of `.lbx`.

Use BIN2PRG/SC2 for source-level analysis. Do not interpret binary object-code bytes as source code.

## Data access and optimization

Analyze both SQL and native xBase access:

- `USE`, `SELECT` work area, `SCAN`, `LOCATE`, `SEEK`, `INDEXSEEK`,
- `CALCULATE`, `COUNT`, `SUM`, `AVERAGE`,
- `REPLACE`, APPEND/DELETE/RECALL,
- SQL SELECT/JOIN/GROUP/HAVING/ORDER/DISTINCT/UNION,
- local/remote views,
- CursorAdapter,
- SQL Pass-Through,
- locking/buffering/transactions.

Rushmore status must use runtime evidence such as `SYS(3054)` whenever claiming FULL/PARTIAL/NONE. An index that merely looks compatible is not proof.

## Complete application domains

A tool that claims complete VFP application support must also understand:

- PJX/PJT project graph and main entry point,
- BUILD PROJECT/APP/EXE/DLL,
- READ EVENTS/CLEAR EVENTS/ON SHUTDOWN lifecycle,
- CONFIG.FPW and effective SET state,
- DBC rules/triggers/stored procedures/views/connections,
- CursorAdapter and SPT,
- menus MNX/MNT/MPR/MPX,
- reports FRX/FRT and VFP9 ReportListener/REPORTBEHAVIOR,
- labels LBX/LBT,
- COM/OLE/ActiveX and automation servers,
- DECLARE DLL/FLL/native dependencies,
- runtime/deployment resources and 32-bit compatibility.

## Compiler/refactor validation

For generated or changed code:

1. verify introduced language elements against the language catalog,
2. parse structure and reject foreign-language artifacts,
3. compile using the exact installed VFP9 SP2,
4. for visual artifacts operate only on an isolated workspace copy,
5. reopen/round-trip through VFP/FoxBin2Prg,
6. compare object/method/data/index invariants,
7. run regression tests,
8. benchmark performance claims,
9. promote only after `PASS`.

The source project remains immutable.

## Completeness rule

Knowledge presence and executable implementation are different things. Use `VFP9SP2_CAPABILITY_MATRIX.md` to report the current implementation state.

A top-level audit may return `COMPLETE` only when every detected/relevant application domain is `COMPLETE` or explicitly `NOT_APPLICABLE`. Otherwise return `PARTIAL`, `HEURISTIC`, `UNKNOWN` or `NOT_IMPLEMENTED` as appropriate.
