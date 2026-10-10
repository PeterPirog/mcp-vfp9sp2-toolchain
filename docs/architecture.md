# Architecture

The authoritative architecture is the frozen Source of Truth
(`spec/SOURCE_OF_TRUTH.md`, Rev.35). This document is a navigation aid only
and never overrides it.

## One Core, thin adapters

```text
MCP client / reasoning model        operator terminal
            |                              |
       MCP adapter                    CLI adapter
            |                              |
        +--------------------------------------+
        |      VFPToolchain Core Service       |
        |  core / models / errors / capabilities / policy / jobs
        |  project / datasets / knowledge / language / semantic
        |  forms / analysis / performance / backends / vfp_runtime
        |  refactor / privacy / relational / postgres / mcp
        +--------------------------------------+
             |            |              |          \
          dbfbridge   VFPX Help      FoxBin2Prg   DBF_Anonymizer
          (DBF/FPT)   (VFP9 corpus)  (bin<->text)  (privacy)
                                |
                          PostgreSQL (relational target)
```

- `vfp_toolchain.core.CoreService` is the single domain owner; both console
  entry points (`vfp-toolchain`, `mcp-vfp9sp2`) delegate to it.
- `dbfbridge` owns low-level DBF/FPT Direct Read/Write; `DBF_Anonymizer` owns
  reversible pseudonymization and vault behavior; neither is copied into this
  repository — only their public APIs are consumed.
- FoxBin2Prg owns canonical bidirectional VFP binary/text conversion.
- VFPX HelpFile supplies the pinned VFP9 SP2 documentation corpus.

## Release-gated capability layers

Capability arrives in independently useful releases:

```text
B0      repository foundation (this build)
0.4.0   Data & Help Explorer
0.5.0   Application Analyzer
0.6.0   Optimization Assistant
0.7.0   Safe Refactoring
0.8.0   Privacy & Anonymized Datasets
0.9.0   PostgreSQL Relational Designer
0.10.0  PostgreSQL Shadow Migrator
0.11.0  VFP/PostgreSQL Transition Assistant
1.0.0   complete target architecture
```

Each release closure is derived mechanically from the canonical requirement
graph (`spec/requirements.graph.json`); release-gate manifests live in
`release-gates/`.

## Canonical module map (target)

`vfp_toolchain` grows one module family per phase: `core`, `bootstrap`,
`verification` exist from B0; `project`, `datasets`, `knowledge`, `language`,
`semantic`, `forms`, `analysis`, `performance`, `backends`, `vfp_runtime`,
`refactor`, `privacy`, `relational`, `postgres`, and the `mcp` adapter join
as their milestones activate. Adapters stay thin; domain behavior never
leaks into them.

## Windows trust zones

Analysis never writes into immutable zones; work happens in isolated
workspace/output zones (see SOT section 14). The threat model
(`spec/threat-model.json`) enumerates boundaries and controls.