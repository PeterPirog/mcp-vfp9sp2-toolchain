# Capability state (truthful)

This page is generated-adjacent documentation describing the CURRENT build.
It must never claim capability that a release gate has not qualified
(REQ-AUTO-037).

## Current build: 0.0.0.dev0 (bootstrap foundation)

Implemented and executable in this build:

- start-state classification (ABSENT/EMPTY/MATCHING_BOOTSTRAP_RESUME/
  UNKNOWN_NONEMPTY) — `vfp_toolchain.bootstrap.classify`
- bootstrap invocation logical object, canonicalization, logical hashing —
  `vfp_toolchain.bootstrap.invocation`
- canonical JSON hashing profile — `vfp_toolchain.canonical`
- transport-neutral Core Service with truthful capability discovery —
  `vfp_toolchain.core` / `vfp_toolchain.capabilities`
- typed error registry — `vfp_toolchain.errors`
- deterministic control-plane generation from the frozen SOT —
  `tools/generate_control_plane.py`
- contract self-consistency engine, schema validation, layout/package/
  determinism/no-download checks, requirement dispatch —
  `vfp_toolchain.verification` + `tools/verify.py`

NOT_IMPLEMENTED (truthfully refused; no placeholder success):

- MCP server transport and any MCP tool/resource
- DBF/FPT reading (incl. Memo), schema inspection, value search
- VFPX VFP9 SP2 Help search
- dataset registration/lineage (original/anonymized)
- semantic graph, forms/classes analysis, DBC model, reasoning
- CDX/IDX/Rushmore/SYS(3054) performance analysis, VFP runtime execution
- refactoring (FoxBin2Prg round-trip, compile/build validation)
- privacy/anonymization workflows
- relational target model, PostgreSQL schema design
- PostgreSQL shadow migration, parity, transition/cutover
- remote integration/publication automation

## Activation plan

Each capability activates at its canonical milestone (see
`spec/requirements.graph.json` and `docs/architecture.md`); until that
milestone's release gate passes, the capability reports unavailable.