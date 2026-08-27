# Implement VFP9 SP2 language subsystem in vfp-integration-toolchain

Repository:
`https://github.com/PeterPirog/vfp-integration-toolchain`

## Goal

Add a version-aware Microsoft Visual FoxPro 9.0 SP2 language subsystem so analysis and code generation do not rely on model memory.

Use the language package files as the architecture contract.

## Rule

The LLM is not the syntax authority.

A language fact must come from the installed VFP9 SP2 runtime/compiler and/or VFP9 SP2 Help metadata.
Changed/generated code must compile before it can be accepted.

## 1. Add language package

Create:

```text
language/
  README.md
  vfp9sp2_core_spec.json
  vfp9sp2_language.schema.json
  extract_vfp9sp2_runtime_inventory.prg
  runtime/
```

## 2. Add `vfp_driver.py language_inventory`

Invoke `VisualFoxPro.Application.9` in a scratch directory and collect:

- VERSION()
- VERSION(1)
- VERSION(5)
- SYS(3099)
- CPCURRENT()
- ALANGUAGE(...,1..4)
- AMEMBERS(..., class, 1) for each base class

Never write into the source project.

## 3. Add normalized runtime catalog

Generate:

```text
.vfp-ai/language/vfp9sp2_runtime_inventory.txt
.vfp-ai/language/vfp9sp2_language_catalog.json
```

Each element must carry:

```text
id
kind
canonicalName
dialect
status
syntax[]
introducedIn
changedIn
backwardCompatibleOnly
semanticTags[]
environmentDependencies[]
sources[]
runtime{}
```

## 4. Add OpenCode tools

```text
vfp_language_status
vfp_language_inventory
vfp_language_lookup
vfp_validate_snippet
```

`vfp_language_lookup SELECT` must return both work-area SELECT and SELECT-SQL semantics when applicable.

## 5. Replace regex-only method parsing

Implement at minimum:

1. lexer,
2. string/comment recognition,
3. logical-line builder for `;`,
4. preprocessor-aware source model,
5. block stack,
6. PROCEDURE/FUNCTION extraction with real line ranges.

Recognize VFP strings (`""`, `''`, `[]`) before comments and continuation parsing.

## 6. Distinguish ambiguous language families

Create different AST/semantic nodes for:

- work-area SELECT vs SELECT-SQL,
- xBase DELETE vs DELETE-SQL,
- legacy INSERT vs INSERT-SQL,
- legacy UPDATE vs UPDATE-SQL,
- SEEK command vs SEEK() vs INDEXSEEK().

## 7. Environment model

Detect project use of:

`SET ENGINEBEHAVIOR`, `SET COMPATIBLE`, `SET OPTIMIZE`, `SET EXACT`, `SET ANSI`, `SET DELETED`, `SET EXCLUSIVE`, `SET REPROCESS`, `SET MULTILOCKS`, `SET COLLATE`, `SET CPCOMPILE`, `SET STRICTDATE`, `SET TABLEVALIDATE`, `SET DATE`, `SET CENTURY`, `SET PROCEDURE`, `SET CLASSLIB`, `SET PATH`.

Classify effective state as:

`KNOWN | CONFLICTING | DYNAMIC | UNKNOWN`.

## 8. Version-aware SQL

Encode VFP9 SQL changes and `SET ENGINEBEHAVIOR 70|80|90`.

Do not reject valid VFP9 syntax because it was invalid in VFP8.
Do not choose backward-compatible language for new code unless required.

## 9. Code-generation guard

Before a RefactorPlan can use newly generated code:

1. look up introduced commands/functions in language catalog,
2. reject `UNVERIFIED`,
3. run foreign-language artifact detection,
4. run `vfp_validate_snippet` through VFP9 compiler,
5. only then allow the patch into the controlled write plane.

## 10. Foreign-language detector

Outside strings/comments flag likely accidental VBA/VB.NET/C#/JS/Python/T-SQL constructs, including examples such as:

`End If`, `Next`, `While ... Wend`, `Dim x As`, `Set obj =`, `//`, `/* */`, `let`, `const`, `var`, `===`, `=>`, unsupported CTE/MERGE/APPLY syntax.

Do not false-positive on comments or string literals.

## 11. Tests

Pure tests:

- comments,
- bracket/single/double-quoted strings,
- continuation lines,
- nested blocks,
- typed FUNCTION,
- PROCEDURE/FUNCTION line ranges,
- macro substitution,
- SELECT ambiguity,
- SQL/xBase DELETE/INSERT/UPDATE ambiguity,
- foreign-language detection outside vs inside strings/comments,
- environment state classification.

VFP9 integration tests, skipped when COM unavailable:

- runtime inventory,
- AMEMBERS,
- compile valid snippet,
- reject invalid snippet,
- typed FUNCTION compile,
- representative VFP9 SELECT-SQL,
- COMPILE FORM fixture.

## 12. Agent policy

Update `agents/vfp-analyst.md` and future `vfp-refactor`:

> Never assert that syntax is valid because it resembles VFP. Query the VFP9 SP2 language catalog. For generated/changed code require compiler validation.

The analyst remains read-only. Writes happen only through the controlled refactor workspace.

## Definition of done

OpenCode must support:

```text
vfp_language_status
vfp_language_lookup "CALCULATE"
vfp_language_lookup "SELECT"
vfp_validate_snippet <candidate code>
```

A generated patch cannot reach the write plane if:

- VFP9 SP2 version is unconfirmed,
- introduced syntax is UNVERIFIED,
- parser reports structural errors,
- compiler validation fails.

Work on a feature branch, push to GitHub and open a PR. Do not merge automatically.
