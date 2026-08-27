# Visual FoxPro 9.0 SP2 — mandatory knowledge contract for the toolchain

This document defines the minimum language, form, data, index and validation semantics that `vfp-integration-toolchain` must know before it can claim to perform a complete audit or safe refactoring of a Microsoft Visual FoxPro 9.0 SP2 project.

The target dialect is:

`microsoft.visual-foxpro.9.0.sp2`

The toolchain must treat the installed VFP9 compiler/runtime as the final authority for syntax validation. Static metadata and documentation are required for analysis, but generated or changed production code must be compiled by the installed VFP9 SP2 before it is accepted.

## 1. Version and compatibility model

The toolchain must record the exact runtime with `VERSION()` and related information. VFP 9 SP2 is commonly reported as build 5815; a fully patched SP2 installation can report later hotfix builds such as 7423. Do not reject a patched SP2 build only because it is not exactly 5815.

Collect at minimum:

```foxpro
VERSION()
VERSION(1)
VERSION(5)
SYS(3099)
CPCURRENT()
```

The SQL engine compatibility mode must be treated as semantic input:

```foxpro
SET ENGINEBEHAVIOR 70
SET ENGINEBEHAVIOR 80
SET ENGINEBEHAVIOR 90
```

`SYS(3099)` exposes the equivalent mode. Mode 90 is VFP9 behavior. The same SQL text can have different validation or behavior in modes 70, 80 and 90.

`SET COMPATIBLE` is a different compatibility mechanism and must be modeled independently.

## 2. Source-of-truth hierarchy

1. Installed Microsoft Visual FoxPro 9 SP2 runtime/compiler.
2. Microsoft/VFPX VFP9 SP2 Help.
3. Runtime introspection: `ALANGUAGE()`, `AMEMBERS()`, `APROCINFO()` and relevant metadata functions.
4. FoxBin2Prg text representation for analysis and round-trip comparison.
5. Community documentation only as secondary evidence.

Language facts should carry a confidence status such as:

- `VERIFIED_RUNTIME_AND_HELP`
- `VERIFIED_HELP`
- `VERIFIED_RUNTIME`
- `BACKWARD_COMPATIBLE`
- `VERSION_DEPENDENT`
- `PROJECT_ENVIRONMENT_DEPENDENT`
- `HEURISTIC`
- `UNVERIFIED`
- `INVALID_FOR_VFP9SP2`

`UNVERIFIED` and `HEURISTIC` constructs must not be introduced into production code.

## 3. Runtime language inventory

Use:

```foxpro
ALANGUAGE(ArrayName, 1) && commands
ALANGUAGE(ArrayName, 2) && functions + parameter metadata
ALANGUAGE(ArrayName, 3) && base classes
ALANGUAGE(ArrayName, 4) && DBC events
```

Use `AMEMBERS()` for properties, events and methods of classes/objects.

The runtime inventory answers whether an element exists in the installed VFP. Documentation remains necessary for exact syntax, semantics, side effects and version changes.

## 4. Lexical rules the parser must implement

VFP parsing must not be implemented as independent regular expressions over raw lines.

The lexer must understand before command recognition:

- case-insensitive keywords,
- full-line comments beginning with `*`,
- inline comments beginning with `&&`,
- line continuation using `;`,
- double-quoted strings,
- single-quoted strings,
- square-bracket strings `[text]`,
- logical literals `.T.` and `.F.`,
- null literal `.NULL.`,
- date/date-time literals,
- macro substitution using `&`,
- preprocessor directives.

`&&` is a comment delimiter, not a logical operator from another language.

`;` is a continuation mark, not a C/JavaScript statement terminator.

The parser must preserve both physical and logical line numbers.

## 5. Required block grammar

At minimum, the parser must model:

```text
IF                 -> ELSE -> ENDIF
DO CASE            -> CASE / OTHERWISE -> ENDCASE
DO WHILE           -> ENDDO
FOR                 -> ENDFOR
FOR EACH            -> ENDFOR
SCAN                -> ENDSCAN
TRY                 -> CATCH / FINALLY -> ENDTRY
WITH                -> ENDWITH
TEXT                -> ENDTEXT
DEFINE CLASS        -> ENDDEFINE
PROCEDURE           -> ENDPROC
FUNCTION            -> ENDFUNC
PRINTJOB            -> ENDPRINTJOB
```

Do not infer nesting from indentation.

## 6. Procedures, functions, parameters and scope

The analyzer must distinguish:

- `PROCEDURE ... ENDPROC`,
- `FUNCTION ... ENDFUNC`,
- `LPARAMETERS`,
- `PARAMETERS`,
- `LOCAL`,
- `PRIVATE`,
- `PUBLIC`,
- typed function/parameter syntax available in VFP9.

Do not mechanically convert `PRIVATE`/`PUBLIC` variables to `LOCAL`; scope can be part of application behavior.

For every routine store:

- owner class/form/object,
- object path,
- method/function/procedure name,
- physical and logical line range,
- parameters,
- local/private/public symbols,
- source hash,
- calls and data side effects.

## 7. Object-oriented language semantics

The toolchain must know:

- `DEFINE CLASS ... ENDDEFINE`,
- class inheritance,
- `Class`, `ClassLibrary`, `BaseClass`,
- `ADD OBJECT`,
- `THIS`, `THISFORM`, `_SCREEN`, `_VFP`,
- custom properties and methods,
- protected/hidden members,
- `CREATEOBJECT()` and `NEWOBJECT()`,
- visual class libraries `.vcx/.vct`.

A method override and an inherited method are not equivalent. Refactoring must preserve inheritance semantics.

## 8. Work areas and implicit database state

This is mandatory for correct VFP analysis.

The toolchain must model:

- current work area,
- current alias,
- open/closed aliases,
- current record pointer,
- active order/tag,
- filter,
- key range,
- relations,
- buffering,
- locking state when determinable.

Important commands/functions include:

```text
SELECT <workarea-or-alias>
USE
USE IN
ALIAS()
SELECT()
RECNO()
RECCOUNT()
EOF()
BOF()
FOUND()
GO/GOTO
SKIP
LOCATE
CONTINUE
SCAN
SET ORDER
SET INDEX
SET FILTER
SET KEY
SET RELATION
```

Work-area `SELECT` is a different command from `SELECT - SQL` and must use a different AST node.

Code that compiles can still be wrong if a refactoring changes the selected alias or current record.

## 9. SQL and xBase are separate language families

The analyzer must explicitly distinguish:

- work-area `SELECT` vs `SELECT - SQL`,
- xBase `DELETE` vs `DELETE - SQL`,
- historical `INSERT` vs `INSERT - SQL`,
- historical `UPDATE` vs `UPDATE - SQL`,
- `SEEK` command vs `SEEK()` vs `INDEXSEEK()`.

VFP9 SQL includes SELECT, JOINs, subqueries, UNION, GROUP BY, HAVING, ORDER BY, TOP, INSERT-SQL, UPDATE-SQL, DELETE-SQL, CREATE CURSOR-SQL, CREATE TABLE-SQL and ALTER TABLE-SQL.

VFP9 removed or increased several limits present in older versions, so syntax must not be rejected using VFP7/VFP8 assumptions.

Every SQL analysis must record the effective `ENGINEBEHAVIOR` state.

## 10. Data types and code pages

The toolchain must preserve field types, lengths, decimals, nullability, binary flags, code page and autoincrement metadata.

VFP table/runtime types include, depending on context:

- Character,
- Character (Binary),
- Numeric,
- Float,
- Double,
- Integer,
- Integer (Autoinc),
- Currency,
- Logical,
- Date,
- DateTime,
- Memo,
- Memo (Binary),
- General,
- Varchar,
- Varchar (Binary),
- Varbinary,
- Blob,
- Variant.

The table header contains a code-page mark. Source/SC2 text must not be blindly decoded as cp1252. Use the FoxBin2Prg CPID and project/table metadata. Polish projects can require cp1250, cp852 or legacy conversions.

Encoding corruption must be a validation failure, not silently replaced with U+FFFD.

## 11. Multi-file components are atomic artifacts

VFP components commonly consist of a primary file plus companion file(s):

```text
Form             .scx + .sct
Visual class     .vcx + .vct
Report           .frx + .frt
Label            .lbx + .lbt/.lb2 depending on tooling/version representation
Menu             .mnx + .mnt
Table            .dbf + optional .fpt + structural .cdx; optional .idx
Database         .dbc + .dct + .dcx
Project          .pjx + .pjt
```

A form `.scx` without its `.sct` is not a complete form artifact.

A write-enabled tool must copy, hash, validate and promote companion files together.

## 12. SCX/SCT form storage model

VFP stores forms as table-based artifacts. `.scx` is a table and `.sct` is its memo companion. Do not treat SCX/SCT as ordinary text files and do not judge binary memo/object-code bytes as source code.

For semantic analysis prefer:

```text
SCX/SCT -> VFP9/FoxBin2Prg BIN2PRG -> SC2
```

The SC2 representation must preserve enough information to reconstruct or compare:

- form/class definition,
- object hierarchy,
- parent-child paths,
- base classes/class libraries,
- properties and overridden property values,
- methods/events source,
- object names,
- DataEnvironment,
- controls and containers.

Do not edit raw SCX/SCT binary layout from Python/TypeScript when VFP9 can perform the operation safely.

## 13. Form object model that must be audited

At minimum inventory:

- Form/FormSet,
- PageFrame/Page,
- Container,
- Grid/Column/Header,
- TextBox,
- EditBox,
- ComboBox,
- ListBox,
- CheckBox,
- OptionGroup/OptionButton,
- CommandButton/CommandGroup,
- Spinner,
- Label,
- Image,
- Shape/Line,
- Timer,
- OLE Container/OLE Bound controls,
- custom controls/classes,
- DataEnvironment,
- Cursor,
- CursorAdapter,
- Relation.

Do not freeze this list as the final truth: use `ALANGUAGE()` and `AMEMBERS()` to enrich the exact installed runtime inventory.

## 14. Mandatory form properties for before/after comparison

For safe method-only refactoring compare at least:

```text
Name
Class
ClassLibrary
BaseClass
Parent/object path
Top
Left
Width
Height
Caption
FontName
FontSize
FontBold/Italic where relevant
ForeColor
BackColor
Enabled
Visible
ReadOnly
TabIndex
ControlSource
RowSource
RowSourceType
RecordSource
RecordSourceType
Value when design-time relevant
InputMask
Format
Picture/PictureVal where relevant
ToolTipText
Anchor/Dock-related properties when present
```

Use runtime PEM metadata to extend the list by class.

Unexpected changes in object count, hierarchy, base class, control binding or geometry must fail validation unless explicitly authorized by the RefactorPlan.

## 15. Form events and methods

The toolchain must inventory all source-defined methods/events, not only common ones.

High-value form/control events include:

```text
Load
Init
Activate
Deactivate
Refresh
Destroy
Unload
QueryUnload
Resize
Click
DblClick
RightClick
When
Valid
GotFocus
LostFocus
InteractiveChange
ProgrammaticChange
KeyPress
MouseDown/MouseMove/MouseUp
Timer
BeforeOpenTables
AfterCloseTables
```

This list is not exhaustive. Runtime `AMEMBERS()` is the authority for available PEMs.

Do not assume two events can be reordered. Event order and side effects can be part of functionality.

## 16. DataEnvironment semantics

A form, form set or report can have a DataEnvironment. It contains Cursor, CursorAdapter and Relation objects and can automate opening/closing tables/views.

Audit at minimum:

- `AutoOpenTables`,
- `AutoCloseTables`,
- `InitialSelectedAlias`,
- `DataSource`,
- `DataSourceType`,
- Cursor `Alias`, `CursorSource`, `Order`, `Filter`, buffering-related properties,
- Relation parent/child aliases and relational expression,
- code in DataEnvironment methods/events.

Changing a form method without understanding DataEnvironment can change alias availability, selected work area and index order.

## 17. DataSession semantics

The form/session data environment can be isolated from other forms depending on DataSession behavior. The analyzer must not assume all forms share the same work areas.

Where a form uses a private data session, alias state, SET settings and open tables can differ from the calling context.

## 18. Structural index model

A VFP table header can indicate presence of a structural `.cdx`. Structural CDX files are associated with the table and are normally opened automatically with it.

A `.cdx` can contain multiple tags. A standalone `.idx` is a separate index file and is handled differently.

All compound indexes are compact indexes; each CDX tag has an index structure comparable to the compact IDX structure.

The toolchain must never assume that the presence of `<table>.cdx` means a particular useful tag exists.

## 19. INDEX command semantics

The documented VFP9 form includes:

```foxpro
INDEX ON eExpression TO IDXFileName | TAG TagName [BINARY] ;
    [COLLATE cCollateSequence] [OF CDXFileName] [FOR lExpression] ;
    [COMPACT] [ASCENDING | DESCENDING] [UNIQUE | CANDIDATE] [ADDITIVE]
```

Important distinctions:

- regular tag: duplicates allowed,
- `UNIQUE`: only the first record for duplicate keys is kept in that index; it is not a relational uniqueness constraint,
- `CANDIDATE`: duplicate key values are not allowed,
- primary indexes cannot be created with the `INDEX` command; primary-key semantics belong to database/table DDL,
- filtered `FOR` indexes have additional semantics and maintenance implications,
- descending is supported for CDX tags; standalone IDX handling differs,
- collation affects character key representation and sort order.

Never recommend `UNIQUE` when the actual requirement is a candidate/primary uniqueness constraint.

## 20. Index-key design constraints

The analyzer must model key type and key length.

VFP does not support variable-length index keys; varying character values are padded. Composite expression ordering is lexicographic according to the produced key representation.

Do not concatenate fields into a composite key without validating data types and representation.

Examples of hazards:

- character `"10"` sorts before `"2"`,
- numeric fields concatenated incorrectly can change semantics,
- dates should use a sortable representation when converted to character,
- nullable expressions require deliberate handling,
- non-MACHINE collations can consume more key bytes,
- functions in key expressions must be deterministic for correct maintenance.

Before proposing `prefix + field + number`, determine exact field types, lengths, padding and desired ordering.

## 21. Runtime index introspection

Prefer documented VFP runtime functions over binary heuristics when VFP9 is available.

Useful functions include:

```text
TAG()
TAGNO()
TAGCOUNT()
KEY()
SYS(14)
FOR()
SYS(2021)
ORDER()
CANDIDATE()
PRIMARY()
IDXCOLLATE()
CDX()
NDX()
```

`KEY()` and `SYS(14)` return index key expressions.

`FOR()` and `SYS(2021)` return filtered-index expressions.

Binary CDX parsing is a fallback and its results must carry `HEURISTIC` or equivalent confidence unless confirmed by VFP runtime metadata.

## 22. SEEK and index state

Distinguish:

- `SEEK` command,
- `SEEK()` function,
- `INDEXSEEK()` function.

The semantics depend on the index/tag being searched. A refactoring must know the active `SET ORDER` or explicitly specify a tag where supported.

A successful `SEEK` optimization must preserve:

- key expression semantics,
- alias/work area,
- record pointer behavior,
- FOUND()/EOF() expectations,
- ordering assumptions of subsequent `SCAN REST WHILE` or navigation.

`INDEXSEEK()` is useful when checking an indexed key without necessarily moving the record pointer, depending on its arguments; verify exact syntax through the language catalog/runtime before generation.

## 23. Rushmore optimization

Rushmore applies to VFP SQL and many xBase commands using optimizable expressions. The toolchain must analyze all data access, not only SQL.

Candidates include operations involving:

- `WHERE`,
- JOIN `ON`,
- xBase `FOR`,
- `SCAN FOR`,
- `LOCATE FOR`,
- `COUNT ... FOR`,
- `CALCULATE ... FOR`,
- `SUM ... FOR`,
- `REPLACE ... FOR`,
- DELETE/RECALL variants where applicable.

Do not label an operation `FULL` merely because an index looks similar.

Use runtime evidence:

```foxpro
SET OPTIMIZE ON
SYS(3054, 1)   && filter showplan
SYS(3054, 11)  && join showplan
SYS(3054, 2)   && filter + SQL text
SYS(3054, 12)  && join + SQL text
```

Store the result as:

```text
FULL
PARTIAL
NONE
UNKNOWN
```

and record which tags VFP reports as used.

## 24. Exact-expression principle

Rushmore/index matching depends on expression compatibility. The toolchain must compare normalized expression ASTs, not only field names.

Examples that may matter:

```foxpro
UPPER(name)
LEFT(code, 10)
DELETED()
DTOS(datefield)
PADL(...)
```

A tag on `field` is not automatically equivalent to a condition on `LEFT(field,10)`.

Do not recommend a functional tag before verifying its exact expression and benchmarking it on representative data.

## 25. Filtered index caveat

A tag created with `FOR lExpression` is not equivalent to an unfiltered tag. The filter expression must be captured separately from the key expression.

The toolchain must not conflate:

```text
KEY expression
FOR/filter expression
```

Use `KEY()/SYS(14)` for the key expression and `FOR()/SYS(2021)` for the filter expression.

## 26. Index maintenance side effects

Changing a field that participates in the controlling index can move the record's logical index position during `SCAN`/`REPLACE` operations.

A refactoring must detect cases where code modifies:

- the active key field/expression,
- fields used in a filtered-index `FOR` expression,
- relation keys,
- fields used by a controlling order.

Do not alter such loops without behavioral tests.

## 27. Destructive index/table commands

Commands such as:

```text
INDEX ON
REINDEX
DELETE TAG
PACK
ZAP
ALTER TABLE
```

must never run against production/source data during audit.

Index experiments must use copied DBF/FPT/CDX fixtures or an explicit isolated performance workspace.

## 28. DBC and index semantics

A complete data audit must distinguish free tables from tables belonging to a `.dbc`.

The DBC can contain metadata not visible by reading DBF/CDX alone, including relationships, persistent relations, rules, triggers, views/connections and primary/candidate key semantics.

The toolchain must not claim a complete relational model from inferred co-occurrence of table names in source.

## 29. Locking, buffering and multi-user behavior

Safe refactoring must model or at least detect:

```text
RLOCK()
FLOCK()
UNLOCK
SET REPROCESS
SET MULTILOCKS
CURSORSETPROP()
CURSORGETPROP()
TABLEUPDATE()
TABLEREVERT()
BEGIN TRANSACTION
END TRANSACTION
ROLLBACK
```

Do not move expensive logic into or out of a lock region without analyzing concurrency behavior.

Do not replace local unlock behavior with `UNLOCK ALL` casually.

## 30. Preprocessor and dynamic execution

The parser must retain and model:

```text
#DEFINE
#UNDEF
#IF/#ELIF/#ELSE/#ENDIF
#IFDEF/#IFNDEF
#INCLUDE
#INSERT
```

Dynamic features require explicit uncertainty propagation:

```text
&macro
EVALUATE()
EXECSCRIPT()
DO (expression)
SET PROCEDURE TO (expression)
SET CLASSLIB TO (expression)
```

Static analysis must not pretend dynamic references are fully resolved when they are not.

## 31. Form refactoring write model

The LLM must never directly write binary SCX/SCT.

Required flow:

```text
SOURCE SCX/SCT
  -> SHA256 snapshot
  -> BIN2PRG to SC2
  -> semantic audit
  -> RefactorPlan with objectPath/method/old hash/new source
  -> isolated workspace copy
  -> VFP9 applies patch to copy
  -> COMPILE FORM
  -> reopen in VFP9
  -> BIN2PRG final SCX to final SC2
  -> static + structural comparison
  -> smoke/regression tests
  -> PASS/FAIL
```

Source files must retain identical SHA256 before and after.

## 32. Compile and round-trip validation

For changed code enable error logging and compile in an isolated workspace.

For forms use:

```foxpro
COMPILE FORM <form.scx>
```

A valid final form must:

- have both SCX and SCT,
- compile without current `.ERR` errors,
- reopen in VFP9,
- survive final BIN2PRG conversion,
- have no unexpected object/method/property loss,
- contain no encoding corruption,
- contain no accidental Markdown/prompt/foreign-language artifacts,
- preserve required behavior.

## 33. Foreign-language guard

Outside comments/strings, flag likely accidental constructs from VBA, VB.NET, C#, JavaScript, Python and T-SQL that VFP does not support.

Examples:

```text
End If
For ... Next
While ... Wend
Dim x As ...
Set obj = ...
// comment
/* comment */
let / const / var
===
=>
MERGE
APPLY
```

Do not report them when they occur as data inside a string or comment.

## 34. Audit completeness levels

The toolchain should report an explicit completeness status for each area:

```text
LANGUAGE       COMPLETE/PARTIAL/UNKNOWN
FORMS          COMPLETE/PARTIAL/UNKNOWN
CLASSES        COMPLETE/PARTIAL/UNKNOWN
DATAENV        COMPLETE/PARTIAL/UNKNOWN
DBF_SCHEMA     COMPLETE/PARTIAL/UNKNOWN
DBF_DATA       COMPLETE/PARTIAL/UNKNOWN
CDX_INDEXES    COMPLETE/PARTIAL/HEURISTIC/UNKNOWN
DBC_METADATA   COMPLETE/PARTIAL/UNKNOWN
DEPENDENCIES   COMPLETE/PARTIAL/UNKNOWN
PERFORMANCE    MEASURED/PREDICTED/NOT_TESTED
```

Do not use the phrase `complete audit` when critical domains are only heuristic or unparsed.

## 35. Mandatory machine-readable outputs

A complete language-aware audit should be able to produce:

```text
vfp_environment.json
language_catalog.json
project_source_manifest.json
form_inventory.json
method_inventory.json
data_environment.json
database_schema.json
indexes.json
rushmore_analysis.json
dependency_graph.json
validation_report.json
performance_report.json
```

## 36. Mandatory references

Primary references for this knowledge contract:

- VFPX VFP9 SP2 Help project: https://github.com/VFPX/HelpFile
- VFP9 SP2 Help mirror: https://www.vfphelp.com/
- Table file structure: https://vfphelp.com/vfp9/_5wn12pc0x.htm
- Multi-file components: https://www.vfphelp.com/help/_5wn12p3gh.htm
- DataEnvironment: https://vfphelp.com/vfp9/html/19f2a679-bbf3-4343-9ad8-fd20824e8198.htm
- INDEX command: https://www.vfphelp.com/vfp9/html/242d1feb-d43e-4831-9e4b-d0bb0b5fe4ae.htm
- Compound index structure: https://www.vfphelp.com/help/html/c97ab80a-f978-4944-87bd-2f0dceb44227.htm
- KEY(): https://www.vfphelp.com/help/html/f256f6d2-b03f-41cb-af88-4fb4dce1dc9d.htm
- SYS(14): https://www.vfphelp.com/help/_5wn12psmx.htm
- FOR(): https://www.vfphelp.com/help/html/02242895-0cc5-49dc-9197-d5c2db283aa3.htm
- SYS(2021): https://vfphelp.com/vfp9/html/a91f4661-0f12-4f4a-bb53-63725672a299.htm
- SYS(3054): https://www.vfphelp.com/help/html/400a0198-cac5-4abd-8e2d-79564a75742d.htm
- SET ENGINEBEHAVIOR: https://vfphelp.com/vfp9/_5wn12pf3i.htm
- SQL language improvements: https://www.vfphelp.com/help/html/6c75fbec-8d4a-4809-a521-c54802e59ea5.htm

## 37. Final policy

The LLM proposes analysis/refactoring. The toolchain verifies language, version, object model, data state and compiler acceptance.

A change is safe only when both of these are true:

1. the syntax is valid for the installed VFP9 SP2 environment,
2. semantic/regression validation shows that the intended VFP behavior is preserved.
