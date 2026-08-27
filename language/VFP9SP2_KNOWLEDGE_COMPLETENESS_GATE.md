# VFP9 SP2 knowledge completeness gate

This document is a hard gate for `mcp-vfp9sp2-toolchain`.

Target dialect:

`microsoft.visual-foxpro.9.0.sp2`

## Verdict on current repository knowledge

The repository contains a broad and useful VFP9 SP2 **domain knowledge contract**, including:

- language lexical/block rules,
- Visual FoxPro version/compatibility rules,
- forms/SCX/SCT and visual classes,
- DBF/FPT data,
- CDX/IDX and Rushmore,
- DBC/views/CursorAdapter/SPT,
- application startup/build/runtime,
- menus/reports/labels,
- COM/OLE/ActiveX/DLL/FLL integration,
- offline errata/known issues,
- patch-level and deployment knowledge.

However, the repository does **not yet contain an exhaustive offline exact-language reference** sufficient to claim that every Visual FoxPro 9.0 SP2 command/function/PEM signature can be generated without either runtime/compiler validation or an additional local Help-derived catalog.

Therefore the current knowledge status is:

```text
DOMAIN_KNOWLEDGE               READY
OFFLINE_ERRATA                 READY
RUNTIME_INTROSPECTION_SPEC     READY
EXACT_OFFLINE_LANGUAGE_CATALOG INCOMPLETE
AUTONOMOUS_CODE_GENERATION     BLOCKED_BY_KNOWLEDGE_GATE
```

This distinction is intentional and mandatory.

## Why the existing core spec is not enough

`vfp9sp2_core_spec.json` defines important lexical and semantic rules, but it is not an exhaustive enumeration of:

- every VFP9 SP2 command,
- every command syntax variant and clause ordering,
- every function and exact argument contract,
- every `SYS()` variant,
- every system variable,
- every preprocessor directive variant,
- every base-class property/method/event,
- every DBC event signature,
- every designer-specific PEM,
- every backward-compatible language element,
- every version-dependent syntax/behavior note.

`ALANGUAGE()` and `AMEMBERS()` can confirm names exposed by the installed runtime, but they do not replace full semantic documentation for each signature and side effect.

## Required conditions for KNOWLEDGE_COMPLETE

The repository/toolchain may report `KNOWLEDGE_COMPLETE` only if all gates below pass.

### Gate A — domain contracts

Required locally:

- `VFP9SP2_REQUIRED_KNOWLEDGE.md`
- `VFP9SP2_COMPLETE_APPLICATION_KNOWLEDGE.md`
- `VFP9SP2_OFFLINE_KNOWLEDGE_AND_ERRATA.md`
- forms/index/data/build/UI machine-readable specs
- known issue catalog

Status on current main: `PASS`.

### Gate B — exact language catalog

A normalized local catalog must exist containing, for each relevant language element:

```text
canonical name
kind
syntax variants
required/optional arguments
return type where applicable
argument types/semantics where documented
context restrictions
side effects
work-area/record-pointer effects
version introduced/changed
backward-compatible status
ENGINEBEHAVIOR/COMPATIBLE dependencies
error/limit notes
source/provenance
runtime-present flag
confidence status
```

The catalog must cover at minimum:

```text
commands
functions
operators
preprocessor directives
SYS() functions
system variables
base classes
properties
methods
events
DBC events
SQL language constructs
backward-compatible elements
```

Status on current main: `FAIL / NOT YET GENERATED`.

### Gate C — runtime inventory from the exact installed VFP9 SP2

On the target machine generate and persist:

```text
VERSION()
VERSION(1)
VERSION(5)
SYS(3099)
CPCURRENT()
ALANGUAGE(..., 1..4)
AMEMBERS(...)
```

The runtime inventory is installation-specific and therefore must be generated locally rather than frozen as universal truth.

Status in repository: generator exists.
Status for a target installation: `UNKNOWN` until generated.

### Gate D — local VFP9 SP2 Help-derived reference

For offline operation, the exact syntax catalog must be derived from or cross-checked against a locally available VFP9 SP2 Help corpus.

Preferred maintainers' source is the VFPX `HelpFile` project, which preserves and corrects the VFP9 SP2 Help source under community-maintained licensing.

The runtime agent must not depend on a live URL. A release/install process should package either:

1. a normalized extracted catalog generated from the Help source, or
2. an approved local Help snapshot plus a deterministic local index.

Status on current main: `FAIL / REFERENCE CORPUS NOT VENDORED`.

### Gate E — compiler validation

Even after Gates A-D pass, generated/refactored code must still be compiled with the exact installed VFP9 SP2 runtime/IDE before write-plane promotion.

For forms, `COMPILE FORM` plus reopen and final BIN2PRG round-trip are required.

Compiler success is necessary but not sufficient: semantic/regression validation still applies.

## Offline behavior while the gate is incomplete

Until the exact-language gate is closed, the toolchain may safely:

- audit existing code,
- classify project artifacts,
- analyze known constructs,
- export DBF/FPT,
- analyze forms/classes through BIN2PRG,
- analyze indexes with appropriate confidence,
- use the offline known-issues catalog,
- propose refactoring plans marked as requiring compiler/runtime validation.

It must **not** claim:

```text
"complete offline VFP9 SP2 language reference"
"all syntax is locally known"
"safe autonomous generation without verification"
```

## Acceptance test for the future exact catalog

Before setting `knowledgeStatus=COMPLETE`, automated tests should demonstrate that:

1. every command/function returned by `ALANGUAGE()` has a catalog entry or an explicit documented exception,
2. every base class returned by `ALANGUAGE(...,3)` is represented,
3. every PEM returned by `AMEMBERS()` can be resolved to a normalized local entry or explicit runtime-only entry,
4. all local catalog examples used for generation compile under VFP9 SP2,
5. ambiguity families such as `SELECT`, `DELETE`, `UPDATE`, `INSERT`, `SEEK` remain context-distinct,
6. backward-compatible elements are explicitly classified,
7. unknown elements fail closed as `UNVERIFIED`,
8. the complete catalog is usable without network access.

## Current architectural decision

Do not proceed to unrestricted autonomous VFP code generation until this gate is closed.

Implementation of audit/parser/refactor infrastructure may continue, but generated production code must remain guarded by runtime/compiler validation and the controlled workspace model.
