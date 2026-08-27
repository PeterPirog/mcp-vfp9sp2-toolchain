# Visual FoxPro 9.0 SP2 — complete application knowledge contract

This document extends the core VFP9 SP2 language/form/index contracts to the whole application lifecycle. A tool that can parse VFP syntax but cannot model projects, application startup, DBC metadata, views, reports, menus, external dependencies, runtime configuration and deployment does **not** have enough information to claim complete VFP9 SP2 application support.

Target dialect:

`microsoft.visual-foxpro.9.0.sp2`

Normative companion files:

- `VFP9SP2_REQUIRED_KNOWLEDGE.md`
- `vfp9sp2_core_spec.json`
- `vfp9sp2_forms_spec.json`
- `vfp9sp2_indexes_rushmore_spec.json`
- `vfp9sp2_application_build_runtime_spec.json`
- `vfp9sp2_data_access_dbc_spec.json`
- `vfp9sp2_ui_reports_menus_integration_spec.json`
- `VFP9SP2_CAPABILITY_MATRIX.md`

## 1. Application architecture and project model

A complete audit must understand the `.pjx/.pjt` project pair and not treat a project as merely a directory of files.

The project model must identify:

- main/startup program or main form,
- included vs excluded project items,
- PRG/H sources,
- SCX/SCT forms,
- VCX/VCT class libraries,
- FRX/FRT reports,
- LBX/LBT labels,
- MNX/MNT menus and generated MPR/MPX,
- DBC/DCT/DCX databases,
- free DBF/FPT/CDX tables,
- external DLL/FLL/OCX/type libraries,
- help/resource/config files,
- build outputs APP/EXE/DLL,
- dynamically loaded resources that cannot be proven statically.

The analyzer must build a dependency graph, not merely a file list.

## 2. Build model

The knowledge base must include VFP build semantics for:

- `BUILD PROJECT`,
- `BUILD APP`,
- `BUILD EXE`,
- `BUILD DLL`,
- compilation of PRG/forms/classes/reports/labels/stored procedures,
- generated FXP/MPX artifacts where applicable,
- build errors and `.ERR` files,
- source vs generated/compiled artifacts.

A future write/build plane must build only in an explicit workspace. It must never compile or alter the production/source project implicitly.

## 3. Application startup and event loop

A VFP application can use a main program that initializes environment, opens resources, establishes menus/forms and then enters an event loop.

Mandatory constructs to recognize:

```text
DO
DO FORM
READ EVENTS
CLEAR EVENTS
ON SHUTDOWN
QUIT
RETURN
SET PROCEDURE
SET CLASSLIB
SET PATH
SET DEFAULT
SET RESOURCE
```

The tool must understand that `READ EVENTS`/`CLEAR EVENTS` can define the lifetime of modeless applications. Removing or moving them during refactoring can terminate the application or make it unresponsive.

`ON SHUTDOWN` handlers and cleanup logic are part of application semantics and must be traced.

## 4. CONFIG.FPW and effective environment

A VFP application can obtain behavior from configuration files and startup code. The tool must find and model `CONFIG.FPW` when present and distinguish internal/project configuration from external configuration when relevant.

Important environment state includes at least:

```text
ENGINEBEHAVIOR
COMPATIBLE
OPTIMIZE
EXACT
ANSI
DELETED
EXCLUSIVE
REPROCESS
MULTILOCKS
COLLATE
CPCOMPILE
STRICTDATE
TABLEVALIDATE
DATE
CENTURY
SAFETY
PROCEDURE
CLASSLIB
PATH
DEFAULT
RESOURCE
REPORTBEHAVIOR
TALK
NOTIFY
```

The effective value must be classified as `KNOWN`, `CONFLICTING`, `DYNAMIC` or `UNKNOWN` when multiple code paths alter it.

## 5. DBC as a semantic database artifact

A `.dbc/.dct/.dcx` database is not just another DBF-like file. A complete data model must capture, when present:

- database tables,
- field metadata,
- primary and candidate keys,
- persistent relationships,
- field validation rules,
- table rules,
- default values,
- insert/update/delete triggers,
- stored procedures,
- local views,
- remote views,
- connections,
- DBC events/properties.

A relationship inferred from two table names occurring in the same source file is not equivalent to a DBC relation.

## 6. Views

The analyzer must distinguish local and remote views and capture their actual SQL and update metadata.

For a view, capture where available:

- SQL definition,
- base tables/views,
- connection,
- parameter expressions,
- key fields,
- updateable fields,
- update names,
- send-updates state,
- fetch size/max records,
- prepared/share-connection behavior,
- WHERE type/update conflict behavior,
- buffering implications.

Do not treat a view cursor as a physical DBF merely because it has an alias at runtime.

## 7. CursorAdapter

`CursorAdapter` is a first-class VFP data-access abstraction. A complete application analyzer must inventory CursorAdapter instances/classes and their configured commands and update mapping.

High-value properties include:

```text
Alias
DataSource
DataSourceType
SelectCmd
InsertCmd
UpdateCmd
DeleteCmd
KeyFieldList
UpdatableFieldList
UpdateNameList
Tables
WhereType
BufferModeOverride
FetchAsNeeded
MaxRecords
BatchUpdateCount
UseTransactions
CompareMemo
SendUpdates
```

The tool must distinguish auto-generated update commands from custom commands and capture relevant methods/events such as `CursorFill` and `CursorRefresh`.

## 8. SQL Pass-Through (SPT)

A complete audit must recognize remote data access via:

```text
SQLCONNECT()
SQLSTRINGCONNECT()
SQLDISCONNECT()
SQLPREPARE()
SQLEXEC()
SQLMORERESULTS()
SQLCOMMIT()
SQLROLLBACK()
SQLCANCEL()
SQLGETPROP()
SQLSETPROP()
AERROR()
```

The semantic model should track connection handle lifetime, transaction boundaries, asynchronous/query timeout settings and error handling where statically possible.

Embedded passwords or credentials are security findings. Audit output must redact secrets rather than copying them into reports.

## 9. Buffering and optimistic updates

VFP applications often depend on record/table buffering. The tool must detect and reason about:

```text
CURSORGETPROP()
CURSORSETPROP()
TABLEUPDATE()
TABLEREVERT()
GETFLDSTATE()
GETNEXTMODIFIED()
```

A refactor that changes when `TABLEUPDATE()` happens, the table buffering mode, key fields or conflict checks can change transaction semantics even if UI behavior appears unchanged.

## 10. Locking and multi-user behavior

Mandatory constructs:

```text
RLOCK()
FLOCK()
UNLOCK
SET REPROCESS
SET MULTILOCKS
```

The analyzer must identify expensive operations inside lock regions and must not move logic across lock/unlock boundaries without explicit validation.

## 11. Transactions

Mandatory constructs:

```text
BEGIN TRANSACTION
END TRANSACTION
ROLLBACK
```

Transactions must be modeled separately from SPT/remote-server transactions when both are present.

## 12. Menus

A VFP menu can involve:

- `.mnx/.mnt` designer artifacts,
- generated `.mpr/.mpx`,
- hierarchy/pads/popups,
- menu prompts,
- shortcuts/hotkeys,
- `SKIP FOR` expressions,
- command actions,
- procedure actions,
- setup/cleanup code,
- `SET SYSMENU` integration.

The dependency graph must follow menu actions into `DO`, `DO FORM`, commands and procedures.

## 13. Reports

A VFP report is `.frx/.frt` and can contain its own DataEnvironment, expressions, variables, grouping and runtime code.

Mandatory audit areas:

- report DataEnvironment,
- aliases/data sources,
- bands/groups,
- report variables,
- calculated expressions,
- user-defined functions,
- printer/page settings,
- runtime parameters,
- code stored in report metadata.

VFP9 introduced object-assisted reporting. The tool must detect `SET REPORTBEHAVIOR` and `ReportListener` usage and must not assume all `REPORT FORM` executions use legacy rendering semantics.

## 14. Labels

The binary label designer artifact is:

```text
.lbx + .lbt
```

Do not confuse `.lbt` with FoxBin2Prg's generated text representation `.lb2`.

A label audit is analogous to report audit and must include DataEnvironment and expressions.

## 15. COM, OLE and ActiveX

Recognize at minimum:

```text
CREATEOBJECT()
GETOBJECT()
CREATEOBJECTEX()
OLEPUBLIC
OLEControl/OLEBoundControl
ActiveX controls
```

Capture ProgID/CLSID/type-library/OCX/DLL dependencies where discoverable. Missing COM registration is a deployment risk.

VFP is a 32-bit environment; external component bitness compatibility is relevant to deployment and must be reported when known.

## 16. Native DLL/FLL integration

Recognize:

```text
DECLARE - DLL
SET LIBRARY
CALL
```

Capture library names/paths, called entry points and declared signatures. Native calls are high-risk for automated refactoring because signature or calling-convention mistakes can crash the process rather than produce a normal VFP error.

## 17. Automation servers

For `OLEPUBLIC` classes and projects intended for `BUILD DLL`/automation EXE, the public COM interface is part of the compatibility contract.

Refactoring must preserve:

- public class names,
- public method/property names,
- parameter and return expectations,
- registration/deployment requirements.

## 18. Runtime resources and external files

The tool should trace, where possible:

- `FILE()`, `FULLPATH()`, `LOCFILE()`,
- images/icons/cursors,
- INI/configuration files,
- templates,
- help files,
- network/UNC paths,
- registry access,
- shell/process invocation,
- files loaded via dynamic expressions.

Dynamic paths must be represented as unresolved/dynamic dependencies rather than silently ignored.

## 19. FOXUSER/resource state

`SET RESOURCE` and the FoxUser resource table can influence developer/runtime behavior. The tool should detect explicit resource-file use and avoid treating FoxUser.dbf/FPT as normal business tables without context.

## 20. Performance optimization domains

Performance analysis must cover more than SELECT-SQL. It must inventory:

- `SCAN`, `LOCATE`, `SEEK`, `INDEXSEEK`,
- `CALCULATE`, `COUNT`, `SUM`, `AVERAGE`,
- SQL SELECT/JOIN/GROUP/ORDER/DISTINCT/UNION,
- repeated query/N+1 patterns,
- repeated form/control `Refresh`,
- grid RecordSource/cursor size,
- repeated table opening,
- remote SPT/view/CursorAdapter round trips,
- locking duration,
- index selection and Rushmore,
- memory/cursor materialization where material.

Optimization claims must be classified as `MEASURED` or `PREDICTED`. Predicted speedups are not benchmark results.

## 21. Testing and validation model

A production refactor must have multiple validation layers:

- syntax/compile validation,
- source hash/precondition validation,
- form/class/report structural comparison,
- data-schema/index invariants,
- smoke tests,
- regression scenarios,
- performance BEFORE/AFTER measurements,
- external dependency availability checks.

For changed forms, final `SCX/SCT -> BIN2PRG -> SC2` round-trip is mandatory.

## 22. Security-sensitive information

Audit reports must not copy plaintext credentials, connection secrets, API keys or passwords discovered in source/configuration. Findings should identify location and risk while redacting values.

## 23. Deployment manifest

A complete application audit should eventually produce a deployment manifest covering:

- VFP runtime requirements,
- APP/EXE/DLL output type,
- VFP runtime DLLs where required,
- OCX/COM registrations,
- DLL/FLL dependencies,
- database/data locations,
- configuration/resource files,
- report/menu/image/help resources,
- external server/ODBC dependencies,
- 32-bit constraints.

## 24. Complete-audit rule

The tool may report top-level `COMPLETE` only when every domain required by the detected project is either:

- `COMPLETE`, or
- explicitly `NOT_APPLICABLE`.

If the project uses an artifact/feature whose analyzer is missing, the top-level audit must be `PARTIAL`.

Examples:

- project contains MNX but no menu semantic parser -> PARTIAL,
- project has DBC views but no view metadata extraction -> PARTIAL,
- project uses CursorAdapter but only regex source search exists -> PARTIAL,
- CDX analysis is binary heuristic only -> index domain HEURISTIC,
- optimization lacks SYS(3054)/benchmark -> PREDICTED/NOT_TESTED.

## 25. Final architecture rule

The repository must always distinguish:

**KNOWLEDGE CONTRACT** — what VFP9 SP2 semantics the system knows it must model,

from

**IMPLEMENTED CAPABILITY** — what the current executable tools actually extract/verify/change.

The presence of this document does not mean those capabilities are already implemented. See `VFP9SP2_CAPABILITY_MATRIX.md` for the current gap analysis.
