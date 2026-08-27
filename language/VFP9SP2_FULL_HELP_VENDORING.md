# Full offline Visual FoxPro 9.0 SP2 Help vendoring contract

## Decision

`mcp-vfp9sp2-toolchain` requires a complete local copy of the Visual FoxPro 9 SP2 Help source for offline analysis and code generation.

The canonical offline source is the VFPX HelpFile project, not live scraping of `vfphelp.com` during runtime.

Upstream:

```text
https://github.com/VFPX/HelpFile
```

Pinned revision for the initial knowledge snapshot:

```text
b911ff18b06f421ece242c1d4dfa9fb140864a4a
```

The VFPX project states that Microsoft transferred the VFP9 SP2 Help source and rights to change it to the VFP community under Creative Commons licensing. The VFPX source tree contains the material used to build the corrected/enhanced `dv_foxhelp.chm` and documents a source checkout of roughly 5000 files.

The rendered site:

```text
https://www.vfphelp.com/help/
```

is a useful online mirror/reference for maintainers, but **must not be a runtime dependency**.

## License and attribution

The VFPX HelpFile README identifies Creative Commons Attribution 3.0 as the licensing basis for the transferred Help source.

When vendored, retain upstream attribution and notices. Do not remove Microsoft/VFPX attribution from copied Help content.

The repository's MIT license applies to this toolchain's own code only; vendored VFP Help content retains its own Creative Commons licensing/attribution requirements.

## Required repository layout

A complete checkout should contain:

```text
vendor/
  vfpx-helpfile/                 # pinned upstream HelpFile checkout

language/
  generated/
    vfp9sp2_help_index.jsonl     # searchable normalized page index
    vfp9sp2_help_manifest.json   # hashes/counts/pinned revision
```

The vendored source must be available before offline operation is declared `KNOWLEDGE_COMPLETE`.

## Required source coverage

The Help source is expected to provide the complete VFP9 SP2 Help topic corpus, including at least:

```text
Language Reference
Commands
Functions
SYS() functions
Operators
Preprocessor directives
System variables
Properties
Methods
Events
Objects / classes / collections
SQL language
DBC/data access
Forms and controls
Reports and labels
Menus
Projects/build/deployment
OLE DB / COM / ActiveX
Error messages
Backward-compatible language elements
Programming guides
Optimization/application-performance topics
What's New / version changes
```

Do not reduce the vendored Help to only language-reference pages. The toolchain needs conceptual and task-oriented material as well as syntax pages.

## Offline search model

The full Help remains the authoritative human-readable corpus. The generated index is a search/navigation layer, not a replacement.

Each indexed topic should preserve at minimum:

```text
source path
title
headings
plain text
keywords if extractable
links if extractable
source revision
content SHA256
```

A later semantic extraction pass may add:

```text
kind = command/function/property/method/event/concept/error/etc.
canonical symbol
syntax blocks
parameters
return values
remarks
examples
see-also relationships
version notes
backward-compatibility flags
performance tags
```

Do not automatically treat heuristically extracted HTML text as a verified syntax AST. Exact syntax remains compiler/runtime validated.

## Build/update workflow

Knowledge maintenance is allowed to use Internet access. Production/runtime analysis is not.

Recommended maintenance workflow:

```text
1. fetch/checkout pinned VFPX HelpFile revision
2. verify revision
3. retain upstream attribution/license notices
4. generate local index
5. validate topic/file counts and hashes
6. commit/pin the vendor snapshot or submodule revision
7. run language coverage reconciliation against ALANGUAGE()/AMEMBERS()
8. mark knowledge release
```

Use `tools/build_vfp9sp2_help_index.py` to build the local search index from the vendored source.

## Update policy

Do not silently track upstream `master`.

Every Help update requires:

```text
old revision
new revision
change review
index rebuild
coverage comparison
known-issue comparison
knowledge release note
```

This keeps offline agent behavior deterministic and reproducible.

## Relationship to `vfphelp.com`

The online Help site is useful for maintainers to verify rendered topics and discover corrections. It should be recorded as provenance in local entries where appropriate.

The offline toolchain must continue to work when `vfphelp.com`, GitHub, DNS and all external network access are unavailable.

## Knowledge gate

The repository must not report:

```text
EXACT_OFFLINE_LANGUAGE_CATALOG READY
```

merely because the vendor tree exists.

Closing that gate additionally requires:

- local Help index generation,
- reconciliation with runtime `ALANGUAGE()` and `AMEMBERS()`,
- normalized symbol/syntax catalog generation,
- compiler validation for generated examples/constructs used by the refactor plane.
