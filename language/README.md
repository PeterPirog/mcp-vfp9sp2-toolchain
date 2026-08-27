# Microsoft Visual FoxPro 9.0 SP2 — executable language specification

Target: `microsoft.visual-foxpro.9.0.sp2`

This package is designed for `PeterPirog/vfp-integration-toolchain` and OpenCode agents that analyze and generate VFP code.

## Core design

Do not use one frozen keyword list as the syntax authority. Use three layers:

1. documented VFP9 SP2 syntax and semantics,
2. runtime inventory from the installed VFP9 SP2,
3. compiler validation of changed/generated code.

Production code must not be generated from `UNVERIFIED` language facts.

## Mandatory companion specifications

The following files are normative parts of this language subsystem and must be loaded by audit/refactor agents and tools:

- `VFP9SP2_REQUIRED_KNOWLEDGE.md` — mandatory language, work-area, forms, DataEnvironment, SCX/SCT, DBF/CDX/DBC, Rushmore and validation contract.
- `vfp9sp2_forms_spec.json` — machine-readable form/object/SCX-SCT validation model.
- `vfp9sp2_indexes_rushmore_spec.json` — machine-readable index, SEEK, CDX/IDX and Rushmore model.
- `vfp9sp2_core_spec.json` — lexical/core language and environment model.
- `vfp9sp2_language.schema.json` — normalized language-element schema.
- `extract_vfp9sp2_runtime_inventory.prg` — runtime-derived command/function/class/PEM inventory.

A tool or agent that loads only `vfp9sp2_core_spec.json` must report the VFP knowledge base as PARTIAL, because form storage/validation and index/Rushmore semantics are separate mandatory domains.

## Source-of-truth priority

1. Installed Microsoft Visual FoxPro 9 SP2: `VERSION()`, `SYS(3099)`, `CPCURRENT()`, `ALANGUAGE()`, `AMEMBERS()`, `APROCINFO()`, `COMPILE`, `COMPILE FORM`.
2. Microsoft VFP9 SP2 Help / VFPX mirror: https://www.vfphelp.com/
3. Community references only as secondary evidence.

## Confidence statuses

- `VERIFIED_RUNTIME_AND_HELP`
- `VERIFIED_HELP`
- `VERIFIED_RUNTIME`
- `BACKWARD_COMPATIBLE`
- `VERSION_DEPENDENT`
- `PROJECT_ENVIRONMENT_DEPENDENT`
- `HEURISTIC`
- `UNVERIFIED`
- `INVALID_FOR_VFP9SP2`

## Runtime inventory

VFP9 SP2 provides:

```foxpro
ALANGUAGE(ArrayName, nType)
```

where:

- `1` = commands,
- `2` = functions plus parameter metadata,
- `3` = base classes,
- `4` = DBC events.

For object/class PEMs:

```foxpro
AMEMBERS(ArrayName, cClassName, 1)
```

With `nArrayContentsID=1`, column 2 identifies `Property`, `Event`, `Method`, or `Object`.

## Lexical rules the parser must model

- VFP keywords are case-insensitive.
- `*` begins a full-line comment.
- `&&` begins an inline comment.
- `;` continues a logical command onto the next physical line.
- Strings can use `"..."`, `'...'`, or `[ ... ]` delimiters.
- logical literals: `.T.`, `.F.`
- null literal: `.NULL.`
- strict date literal example: `{^2026-08-27}`
- `&` is macro substitution and must not be treated as C/VBA syntax.

A lexer must recognize strings/comments before interpreting `&&`, `;`, `&`, keywords, or operators.

## Required block grammar

```text
IF              -> [ELSE] -> ENDIF
DO CASE         -> CASE / OTHERWISE -> ENDCASE
DO WHILE        -> ENDDO
FOR             -> ENDFOR
FOR EACH        -> ENDFOR
SCAN            -> ENDSCAN
TRY             -> CATCH / FINALLY -> ENDTRY
WITH            -> ENDWITH
TEXT            -> ENDTEXT
DEFINE CLASS    -> ENDDEFINE
PROCEDURE       -> ENDPROC
FUNCTION        -> ENDFUNC
PRINTJOB        -> ENDPRINTJOB
```

Do not infer block structure from indentation.

## PROCEDURE and FUNCTION

Classic function form:

```foxpro
FUNCTION FunctionName
    LPARAMETERS p1, p2
    RETURN eExpression
ENDFUNC
```

VFP9 also supports typed FUNCTION syntax:

```foxpro
FUNCTION FunctionName(p1 AS Type1, p2 AS Type2) AS ReturnType
    RETURN eExpression
ENDFUNC
```

Do not generate VBA `End Function`, `Dim ... As`, or `For ... Next` syntax.

## Work areas are part of program state

VFP code is not purely expression/SQL based. The analyzer must model:

- current work area,
- alias opening/closing,
- current record pointer,
- active index order,
- relation/filter state.

Examples:

```foxpro
SELECT customers
USE customers IN 0 ALIAS customers SHARED
USE IN customers
```

Refactoring that changes work-area state can be semantically wrong while still compiling.

## Data-access families

### Navigational xBase
`USE`, work-area `SELECT`, `GO/GOTO`, `SKIP`, `SEEK`, `LOCATE`, `CONTINUE`, `SCAN`, `SET ORDER`, `SET FILTER`, `SET KEY`, `SET RELATION`.

### Aggregation
`CALCULATE`, `COUNT`, `SUM`, `AVERAGE`, `TOTAL`.

### Record modification
`REPLACE`, `APPEND`, xBase `DELETE`, `RECALL`, `GATHER`, `SCATTER`.

### VFP SQL
`SELECT - SQL`, `INSERT - SQL`, `UPDATE - SQL`, `DELETE - SQL`, `CREATE CURSOR - SQL`, `CREATE TABLE - SQL`, `ALTER TABLE - SQL`.

Never classify every `SELECT` as SQL.

## Ambiguous names that must be distinct AST nodes

- work-area `SELECT` vs `SELECT - SQL`
- xBase `DELETE` vs `DELETE - SQL`
- legacy/xBase `INSERT` vs `INSERT - SQL`
- legacy `UPDATE` vs `UPDATE - SQL`
- `SEEK` command vs `SEEK()` function vs `INDEXSEEK()`

## Rushmore semantics

Annotate data operations with:

- `FOR`, `WHERE`, `JOIN ON` expressions,
- matching CDX/IDX expression,
- `SET OPTIMIZE` state,
- `SYS(3054)` evidence,
- `FULL | PARTIAL | NONE | UNKNOWN`.

Never replace `CALCULATE/COUNT/SUM ... FOR` with manual `SCAN` solely because the rewritten code appears to make one pass.

## SQL version semantics

VFP9 SQL behavior is parameterized by:

```foxpro
SET ENGINEBEHAVIOR 70 | 80 | 90
```

and:

```foxpro
SYS(3099 [, 70 | 80 | 90])
```

Mode `90` is the VFP9 engine mode.

VFP9 changed SQL relative to older releases, including removal/increase of older limits and support for multiple nested subqueries, UNION in INSERT-SQL, correlated UPDATE-SQL, and other SQL behavior changes.

The analyzer must not judge VFP9 syntax using VFP7/VFP8 rules.

`SET COMPATIBLE` is a separate compatibility mechanism and must be modeled independently.

## Verified relational operators

```text
<  >  =  <>  #  !=  <=  >=  ==
```

`==` is exact character comparison and ignores `SET EXACT`.

## Data types

General/runtime types documented by VFP9 SP2 include:

- Blob
- Character
- Currency
- Date
- DateTime
- Logical
- Numeric
- Varbinary
- Variant

Additional field-only types include:

- Character (Binary)
- Double
- Float
- General
- Integer
- Integer (Autoinc)
- Memo
- Memo (Binary)
- Varchar
- Varchar (Binary)

Preserve code-page behavior, lengths, decimals, nullability and autoincrement metadata.

## Preprocessor

Recognize at minimum:

```text
#DEFINE / #UNDEF
#IF / #ELIF / #ELSE / #ENDIF
#IFDEF / #IFNDEF
#INCLUDE
#INSERT
#NAME
Coverage directives
```

Retain inactive preprocessor branches in the source model.

## High-value environment settings

Detect and model:

```text
SET ENGINEBEHAVIOR
SET COMPATIBLE
SET OPTIMIZE
SET EXACT
SET ANSI
SET DELETED
SET EXCLUSIVE
SET REPROCESS
SET MULTILOCKS
SET COLLATE
SET CPCOMPILE
SET STRICTDATE
SET TABLEVALIDATE
SET DATE
SET CENTURY
SET SAFETY
SET PROCEDURE
SET CLASSLIB
SET PATH
```

Effective project state should be `KNOWN`, `CONFLICTING`, `DYNAMIC`, or `UNKNOWN`.

## Compiler validation contract

Generated/refactored code must be validated using the installed VFP9 SP2:

```foxpro
SET LOGERRORS ON
COMPILE ...
```

For forms:

```foxpro
COMPILE FORM <form.scx>
```

Compilation errors mean the generated change is invalid.

## Form validation contract

For changed SCX/SCT:

1. compile using VFP9,
2. reopen with VFP9,
3. BIN2PRG final SCX to SC2,
4. parse final SC2,
5. compare source/final object inventories,
6. compare method inventories and hashes,
7. detect encoding corruption, duplicate code and foreign-language artifacts,
8. run smoke tests,
9. only then return PASS.

## Recommended language subsystem

```text
language/
  README.md
  VFP9SP2_REQUIRED_KNOWLEDGE.md
  vfp9sp2_core_spec.json
  vfp9sp2_forms_spec.json
  vfp9sp2_indexes_rushmore_spec.json
  vfp9sp2_language.schema.json
  extract_vfp9sp2_runtime_inventory.prg
  runtime/
      runtime_inventory.txt
      runtime_catalog.json
```

Recommended tools:

```text
vfp_language_status
vfp_language_inventory
vfp_language_lookup
vfp_validate_snippet
vfp_validate_prg
vfp_validate_form
```

## Important design rule

The LLM is not the syntax authority.

The LLM proposes code. The toolchain checks the complete VFP9 SP2 knowledge contract, runtime catalog and VFP9 compiler before that code can enter the write/refactor plane.
