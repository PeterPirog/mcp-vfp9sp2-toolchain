# Visual FoxPro 9.0 SP2 — offline knowledge, errata and workaround contract

This file is normative for offline operation of `vfp-integration-toolchain`.

The toolchain must be able to audit, reason about, refactor and validate a VFP9 SP2 project **without Internet access at runtime**. URLs in this file are provenance only. The operational knowledge — symptoms, affected builds, detection rules, workarounds and validation requirements — is stored locally in this repository.

Target dialect:

`microsoft.visual-foxpro.9.0.sp2`

## 1. Offline policy

At runtime the toolchain must not require:

- web search,
- Microsoft documentation servers,
- GitHub,
- package registries,
- online KB articles,
- cloud APIs.

If a fact is required to modify production code, one of the following must be available locally:

1. repository knowledge files,
2. runtime introspection from the installed VFP9 SP2,
3. the local VFP9 compiler/runtime,
4. local project artifacts and test fixtures.

Internet references are maintainers' provenance and refresh sources only.

## 2. Required patch baseline

Known VFP9 builds:

```text
09.00.0000.2412  original VFP9 release
09.00.0000.5815  VFP9 Service Pack 2 baseline
09.00.0000.7423  SP2 + Microsoft Hotfix 3 / KB968409
```

The preferred offline analysis/build baseline is **9.0.0.7423** when the installed/licensed environment permits it.

Rules:

- build `< 5815`: do not call the environment VFP9 SP2,
- build `5815`: SP2 is installed, but the post-SP2 hotfix is absent,
- build `7423` or a verified later patched VFP9 SP2 runtime: mark as fully patched baseline,
- never assume IDE and redistributed runtime DLLs are the same build; inventory both when deployment is audited.

The VFPX installer archive identifies 7423 as the latest fully patched VFP9 release and preserves Microsoft's SP2 and KB968409 packages.

## 3. Official post-SP2 report bug — KB968409

### Symptom

A report with data grouping and `Reprint group header on each page` can print group headers/footers in the wrong order when a group footer flows to the next page after VFP9 SP2 is installed.

### Affected baseline

VFP9 SP2 build 5815.

### Resolution

Microsoft Hotfix KB968409 updates at least:

```text
vfp9.exe   9.0.0.7423
vfp9r.dll  9.0.0.7423
vfp9t.dll  9.0.0.7423
```

### Toolchain rule

If grouped reports are detected and runtime build is 5815:

```text
severity = HIGH
status = PATCH_RECOMMENDED
```

Do not attempt to rewrite report grouping logic merely to work around an engine bug until patch level is verified.

## 4. SQL/Rushmore code-page correctness trap

Under `SET ENGINEBEHAVIOR 70` or `80`, when `CPCURRENT()` differs from a table's `CPDBF()`, Rushmore-optimizable SQL/xBase commands can return or act on incorrect character-index matches.

VFP9 behavior with engine mode 90 avoids using incompatible existing character indexes and can build temporary indexes to preserve correctness, at the cost of performance.

### Safe resolution order

1. Prefer `ENGINEBEHAVIOR 90` for VFP9-native behavior unless the application intentionally depends on older semantics.
2. Match `CPCURRENT()` with the relevant DBF code page where appropriate.
3. Never switch to 70/80 only to regain speed without correctness regression tests.
4. If legacy mode is mandatory, mark optimization results as version-dependent and test exact data results.

### Toolchain detection

For every Rushmore claim record:

```text
ENGINEBEHAVIOR
CPCURRENT()
CPDBF(alias)
index collation/expression
SYS(3054) evidence
```

A speedup that changes returned/updated records is a correctness failure.

## 5. VFP9 SQL semantic changes that frequently break legacy code

### DISTINCT + ORDER BY

With VFP9 engine behavior 90, `SELECT DISTINCT ... ORDER BY field` can error if the ORDER BY field is not present in the SELECT field list.

Resolution: include the ordering expression in the projection when semantically acceptable, or rewrite the query in a VFP9-valid form. Do not blindly switch ENGINEBEHAVIOR to hide the incompatibility.

### DISTINCT + HAVING

VFP9 behavior 90 can reject a HAVING field not present in the SELECT list in the affected DISTINCT form.

Resolution: make the query internally consistent or redesign the grouping/projection.

### Aggregate with no matching records

In VFP9 behavior, an aggregate such as `MAX()` without GROUP BY can return a one-row result even when no input row matches, with `_TALLY` behavior differing from earlier VFP versions.

Resolution: regression-test code that interprets `_TALLY`, EOF state or row existence after aggregate SELECTs.

### TOP under ENGINEBEHAVIOR 70/80

With older engine modes, `TOP n` plus ORDER BY ties may return more than `n` rows.

Resolution: use VFP9 behavior 90 when possible and write deterministic logic if exactly N rows is a business requirement.

## 6. Historical bugs fixed by SP2 — do not reintroduce obsolete workarounds

Microsoft's SP2 bug-fix list includes many problems present in earlier VFP9/VFP8/VFP7 code paths. Important examples for an analyzer are listed below.

If the runtime is >= 5815 these entries are **historical-fixed**. Their presence in old source code may explain strange defensive workarounds. Do not remove such workaround code automatically: first prove it is no longer required by the deployed runtime matrix.

### Forms/classes/UI examples fixed in SP2

- instability when clearing a class also used in another container class,
- crash when `RemoveProperty` is used on a bound property,
- `_VFP.ServerName`/`Application.ServerName` empty for long EXE/DLL paths,
- `PictureVal` failing to accept PNG images,
- form release problems involving ComboBox `Valid` and TRY/CATCH paths,
- DataEnvironment object retained in `DataSource`,
- dangling-reference/form-close issues involving `ISBLANK()` and `THIS.PARENT`,
- orphaned private DataSessions leading to buffer/resource problems,
- closing forms with tooltips causing crashes,
- grid crash/internal-consistency scenarios involving memo tips/indexes,
- fatal exception when listbox RowSource tables are closed.

### Data/SPT/index/SQL examples fixed in SP2

- SQL Pass-Through passing NULL values with the wrong type in some cases,
- long `SQLStringConnect()` connection string limitations from older versions,
- NULL Date/DateTime output-parameter conversion errors in SPT,
- index/optimizer problems involving `ISNULL()`,
- `INDEX ON`/`DELETE TAG ALL` problems for views,
- SQL `NOT IN` subquery incorrect-result cases inherited from older engines,
- `ALL/SOME/ANY` comparison problems with `==`,
- SQL internal error cases involving UNION,
- SQL DELETE join behavior issues,
- Browse crash scenarios after SQL Server connections.

### Reporting examples fixed in SP2

- ReportListener `AdjustObjectSize` inaccurate dimensions in page footers,
- group-header/page-break rendering defects,
- report designer memory leak with protected items,
- print-preview cancellation defects,
- report fields missing in long group headers,
- OLE/picture references embedded in an EXE keeping the EXE locked after report execution,
- ReportListener/report-variable edge cases,
- ReportBuilder/ReportOutput problems under specific SET states.

Toolchain action when one of these patterns is detected:

```text
if runtime_build < 5815:
    PATCH_LEVEL_RISK
else:
    LEGACY_WORKAROUND_CANDIDATE
```

Never delete the workaround solely because SP2 claims the engine bug is fixed; the deployed application may still run an older runtime DLL.

## 7. VFPX ReportingApps fixes relevant on modern systems

The VFP9 object-assisted reporting stack includes ReportBuilder/ReportOutput/ReportPreview applications. VFPX maintains their source and has fixed defects after Microsoft's final VFP release.

Known VFPX ReportingApps changes include:

- high-DPI handling fixes (2014 release),
- duplicate items in a ReportBuilder data-group combo box fixed (2022),
- Print When group-expression handling extended from the older practical 50-character limitation to 250 in the maintained app (2022),
- HTML output bug fixed (2024).

These are **ReportingApps application-layer fixes**, not proof that the VFP9 core runtime itself was changed.

Toolchain rule:

- inventory `_REPORTBUILDER`, `_REPORTOUTPUT`, `_REPORTPREVIEW`, `SET REPORTBEHAVIOR`, and distributed APP versions,
- distinguish Microsoft's original ReportingApps from later VFPX-maintained builds,
- if DPI/report-builder behavior is problematic, prefer a validated maintained ReportingApps deployment over ad-hoc FRX rewrites.

## 8. Report preview deployment pitfall

With `SET REPORTBEHAVIOR 90`, VFP uses the object-assisted reporting architecture and `ReportPreview.App` is the default preview container referenced by `_REPORTPREVIEW`.

A distributed application that relies on this preview path must distribute or otherwise resolve the required preview application.

Missing ReportPreview/ReportOutput/ReportBuilder dependencies are deployment defects, not report-definition syntax errors.

## 9. Saved printer environment can cause slow/hanging report design

VFP9 does not save printer environment information with reports by default. Persisting printer-specific environment data inside FRX/LBX can slow opening/designing reports, especially when the referenced printer is remote or unavailable.

Toolchain rule:

- inventory printer environment metadata in FRX/LBX,
- flag hard dependencies on unavailable/network printers,
- do not blindly preserve machine-specific printer state in regenerated reports unless required.

## 10. XMLAdapter/MSXML dependency

VFP9 `XMLAdapter` requires Microsoft XML Core Services (MSXML) 4.0 SP1 or later according to VFP9 Help. VFPX installation guidance also notes MSXML4 for Task Pane/XMLAdapter functionality.

Offline deployment rule:

- if XMLAdapter/Task Pane XML features are used, record MSXML as an external runtime prerequisite,
- absence of this dependency must be reported explicitly; do not rewrite XML code merely because COM creation fails on an unprepared machine.

## 11. VFP ODBC driver compatibility limitation

The preserved Microsoft/VFPX ODBC release notes state that the Visual FoxPro ODBC driver does not support database features added after VFP6 and recommend the VFP OLE DB Provider where possible.

Toolchain rule:

- detect VFP ODBC usage,
- mark DBC feature coverage as limited,
- prefer VFPOLEDB for tooling that needs VFP9 database features,
- do not infer that an ODBC-level schema is a complete DBC model.

## 12. VFP OLE DB provider limitations

The VFP OLE DB Provider does not support multiple result sets.

Toolchain rule:

- do not generate code that assumes SQL Server-style multiple active result sets from VFPOLEDB,
- represent provider execution as one result set per command unless locally verified otherwise,
- inventory provider version/configuration separately from VFP IDE/runtime version.

## 13. ActiveX security/update risk

Microsoft security update MS08-070 affected several legacy ActiveX controls that can be used by VFP applications (for example common controls, chart, flex grid, winsock families). Updated OCX builds were distributed for VFP9 SP2-era environments.

Offline audit rule:

- inventory every `.ocx`, ProgID/CLSID and version referenced by forms/code,
- flag obsolete/unversioned controls as deployment/security risk,
- do not redistribute random OCX binaries copied from developer machines,
- validate licensing/registration and exact architecture on an isolated deployment fixture.

## 14. FoxUser resource-file operational trap

`FoxUser.dbf` is a VFP resource table with `FoxUser.fpt`. VFP can open the resource file shared and stores user/environment state in it.

For production applications that do not need persistent FoxUser state, `RESOURCE=OFF` / `SET RESOURCE OFF` can reduce unnecessary shared resource-file dependencies.

If the application intentionally uses FoxUser, treat DBF+FPT as a pair and do not delete/replace it casually.

## 15. Table corruption — Error 2091

VFP reports a corrupted table when record-count/header/file-size consistency does not match expected DBF structure.

Offline tool behavior:

- stop write/refactor operations on that table,
- copy/hash the damaged artifact before investigation,
- report the structural mismatch,
- never `PACK`, `ZAP`, `REINDEX` or rewrite a production table as an automatic repair,
- perform repair only on a copy using a verified VFP-aware repair procedure/tool and compare recovered data.

## 16. SET TABLEVALIDATE

Default VFP9 table validation level is 3. Lowering validation can allow access in scenarios where integrity checks would otherwise stop processing, but it must not be treated as a repair.

Toolchain rule:

- record effective `SET TABLEVALIDATE`,
- flag non-default reduced validation in audit output,
- never suppress validation automatically to force a damaged table through a refactor/benchmark pipeline.

## 17. Index mutation during SCAN/REPLACE

VFP Help explicitly warns that replacing values participating in the controlling index changes a record's relative index position. This also applies to filtered indexes whose `FOR` expression depends on modified fields.

Toolchain rule:

Before rewriting any loop, determine whether it modifies:

- active key expression fields,
- filtered-index predicate fields,
- relation keys,
- current order dependencies.

A one-pass optimization that changes record visitation order is semantically unsafe.

## 18. Hard system-capacity limits that must be available offline

Critical VFP9 capacities include:

```text
DBF maximum size                  2 GB
FPT maximum size                  2 GB
records per table                 1 billion
fields per record                 255 (254 when null-bit requirement applies as documented)
record character capacity         65,500
compact/CDX key                   240 bytes max
non-compact IDX key               100 bytes max
SELECT field count                255
command line                      8,192 characters
macro-substituted line            8,192 characters
character memory variable/string  16,777,184 characters
report pages at runtime            65,534 (object-assisted preview also constrained by GDI+ resources)
```

Non-MACHINE collation can consume two bytes per character in an index key; nullable indexed fields can add key overhead.

The optimizer must reject index proposals that can exceed actual key-size limits.

## 19. Variable-length index keys are not supported

VFP pads variable-length key results. Composite expression design must therefore be type-aware and width-aware.

Example risk:

```text
"1", "10", "2"
```

is not numeric ordering.

Do not implement `key1 + key2 + nr_dr` without validating:

- field types,
- exact widths,
- nullability,
- code page/collation,
- numeric ordering requirements,
- date ordering requirements,
- maximum key bytes.

## 20. `WHILE` can disable Rushmore optimization

VFP documentation states that potentially optimizable data retrieval proceeds without Rushmore in cases including commands containing a `WHILE` clause.

Toolchain rule:

Do not classify:

```foxpro
SCAN WHILE ...
```

as Rushmore-equivalent to:

```foxpro
SCAN FOR ...
```

The semantics and optimization model differ.

## 21. High-DPI/modern Windows classification

VFP9 predates modern DPI-awareness models. Community-maintained reporting components include fixes for high-DPI rendering, and application manifests are commonly used to control Windows scaling behavior.

Because DPI behavior depends on Windows version, monitor configuration, manifest, VFP reporting path and third-party controls, classify DPI fixes as:

```text
COMMUNITY_CONFIRMED / ENVIRONMENT_DEPENDENT
```

Do not automatically insert a manifest or change coordinates without visual regression tests.

## 22. Error C0000005 / fatal exception policy

A VFP fatal exception such as C0000005 is not a single diagnosable bug code; historical SP2 fixes include multiple unrelated crash paths.

Toolchain response to a C5/fatal exception must capture:

- exact VFP build,
- runtime DLL builds,
- command/method stack where available,
- form/object path,
- active aliases/index orders,
- current report/provider/ActiveX context,
- reproducible fixture,
- whether the scenario matches a known catalog entry.

Never recommend a generic `REINDEX`, DLL replacement or source rewrite solely because the symptom is C0000005.

## 23. Known-issue confidence classes

Every offline issue entry must be one of:

```text
MICROSOFT_CONFIRMED
MICROSOFT_DOCUMENTED_BEHAVIOR
MICROSOFT_SP2_FIXED
VFPX_CONFIRMED
COMMUNITY_CONFIRMED
ENVIRONMENT_DEPENDENT
UNVERIFIED
```

Production automation may act automatically only on Microsoft-documented/runtime-verifiable rules and explicitly safe VFPX deployment metadata.

Community workarounds require local reproduction before automated changes.

## 24. Offline diagnostic decision order

When a defect is observed:

1. verify exact VFP IDE/runtime build,
2. verify companion files and hashes,
3. verify code page and collation,
4. verify ENGINEBEHAVIOR and critical SET state,
5. check `vfp9sp2_known_issues.json`,
6. determine whether issue is fixed by SP2/7423 or remains environment-dependent,
7. reproduce on an isolated copy,
8. only then propose source/index/report changes,
9. compile/round-trip/regression-test the change.

## 25. Local source provenance

Primary maintainers' sources used to construct this offline summary:

- VFPX/VFPInstallers — VFP9 SP2/Hotfix3 install/build guidance
- VFPX/VFP9SP2Hotfix3 — preserved Microsoft SP2 bug-fix list and hotfix packages
- Microsoft Support KB968409 — post-SP2 grouped-report defect and 7423 file versions
- VFPX/VFP9 SP2 Help — SET ENGINEBEHAVIOR, Rushmore, system capacities, index expressions, table validation, reports, XMLAdapter, resource files, OLE DB
- VFPX/ReportingApps — maintained VFP9 report application fixes
- Microsoft MS08-070 security advisory/update information for legacy ActiveX controls

URLs are stored in `vfp9sp2_known_issues.json` as provenance. Runtime operation must not depend on URL availability.

## 26. Completeness warning

No static document can truthfully guarantee that it contains every bug ever reported on every historical forum. This repository therefore uses a stricter definition of offline completeness:

- all Microsoft/VFPX-confirmed high-value VFP9 SP2 behaviors and fixes required by this toolchain are stored locally,
- community issues are included only when sufficiently reproducible/useful and clearly classified,
- unknown defects remain `UNKNOWN` rather than being guessed,
- the local VFP compiler/runtime and regression tests remain the final arbiter.

The agent must never invent an Internet workaround when offline. If an issue is not in the local catalog and cannot be derived from runtime evidence, return `KNOWN_ISSUE_NOT_FOUND` and preserve the failing fixture for later knowledge-base maintenance.
