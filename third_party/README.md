# Third-party provenance

This repository vendors NO third-party source code at the bootstrap
foundation. Third-party components are consumed either as locked
dependencies (declared in `spec/dependency-lock.json` when resolution is
approved) or as operator-provided trusted-host assets, always through
explicit public boundaries.

## Declared architecture baselines (not installed at B0)

| Component | Baseline | Role | Boundary rule |
|---|---|---|---|
| dbfbridge | 1.1.1 | DBF/FPT engine | public 1.x API only; internals never copied |
| DBF_Anonymizer | 1.0.0.dev0 @ 02763d7c34b19335e560ef9597a54aed7790968d | privacy engine | public clean-slate 1.x boundary only; internals never copied |
| FoxBin2Prg | 1.21.05 @ 32715d06b84753401b7262c3cc48bde758ee3c8d | canonical VFP binary/text engine | external tool root; byte-exact snapshots only when explicitly required |
| VFPX HelpFile | 1.08 @ b911ff18b06f421ece242c1d4dfa9fb140864a4a | VFP9 SP2 doc corpus | operator-provided local corpus; redistribution requires proven rights |
| MCP protocol / SDK / conformance | 2026-07-28 / 2.2.0 / 0.2.0-alpha.10 | MCP surface | locked dependency per milestone |
| Psycopg / PostgreSQL / psqlODBC | 3.3.6 / 18.6 / REL-18_00_0002 | relational target | locked dependency / trusted host |
| converge-orchestrator | @ 1be97b75cf3b51f5ad0c2f212288f0a9edb3899b (tree d47b3c74b7b597dec503b4d3dca9db60e5488c93) | autonomous controller | pinned tool root; never product semantics |

Machine-readable provenance lives in `spec/acquisition.manifest.json`
(declaration fields: origin, immutable identity, acquisition mode, license
expectation, destination role, availability milestone).

## Rules

- Upstream license texts, attribution, and provenance are preserved for every
  retained third-party artifact (REQ-P00-023).
- Licensed Microsoft Visual FoxPro executables/runtime files are NEVER
  vendored into public source or release artifacts (REQ-P00-025).
- Byte-exact vendored snapshots (if ever introduced) are marked non-text in
  `.gitattributes` and are hash-pinned in the acquisition manifest.
- No runtime dependency acquisition happens while serving requests
  (REQ-P00-009).