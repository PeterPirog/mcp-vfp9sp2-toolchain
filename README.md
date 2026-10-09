# mcp-vfp9sp2-toolchain

Windows-local MCP platform for long-term work with Microsoft Visual FoxPro 9.0
SP2 applications: DBF/FPT data access, offline VFP9 SP2 knowledge, whole-
application semantic analysis, controlled refactoring, privacy workflows, and
PostgreSQL modernization — delivered as independently usable, release-gated
capabilities.

**Current build: `0.0.0.dev0` — bootstrap foundation only.**

## Truthful capability state

This build establishes the repository and control-plane foundation
(Bootstrap Gate B0 scope). Every domain capability is truthfully
`NOT_IMPLEMENTED`:

| Capability | State | Activates at |
|---|---|---|
| DBF/FPT/Memo data access | NOT_IMPLEMENTED | release 0.4.0 |
| VFPX VFP9 SP2 offline Help | NOT_IMPLEMENTED | release 0.4.0 |
| Whole-application semantic graph | NOT_IMPLEMENTED | release 0.5.0 |
| Optimization evidence (CDX/Rushmore/SYS(3054)) | NOT_IMPLEMENTED | release 0.6.0 |
| Controlled refactoring (FoxBin2Prg round-trip) | NOT_IMPLEMENTED | release 0.7.0 |
| Privacy/anonymized dataset workflows | NOT_IMPLEMENTED | release 0.8.0 |
| PostgreSQL relational designer | NOT_IMPLEMENTED | release 0.9.0 |
| PostgreSQL shadow migration | NOT_IMPLEMENTED | release 0.10.0 |
| VFP/PostgreSQL transition assistant | NOT_IMPLEMENTED | release 0.11.0 |
| MCP server transport (minimal shell) | NOT_IMPLEMENTED | after Core foundation |
| MCP stabilized surface | NOT_IMPLEMENTED | release 1.0.0 |

No placeholder success responses exist. Running `vfp-toolchain capabilities`
prints the truthful state; `mcp-vfp9sp2` refuses to fake a serving session.

## What this build does provide

- One transport-neutral Core Service boundary (`vfp_toolchain.core`) shared by
  the `vfp-toolchain` CLI and `mcp-vfp9sp2` entry points.
- Deterministic start-state classification (`GREENFIELD`/`BROWNFIELD`/
  `AMBIGUOUS`) scoped to `REPO_ROOT` with fail-closed unknown handling.
- The portable control plane derived from the frozen Source of Truth:
  `spec/requirements.graph.json` (484 requirements), verification manifest,
  compatibility/acquisition manifests, dependency lock, threat model,
  schemas, execution profiles, and release-gate manifests.
- A deterministic verifier dispatcher (`tools/verify.py`) with fail-closed
  semantics: unexecuted verifiers are never PASS.
- Deterministic offline test suite (stdlib runner; pytest-compatible).

## The contract

The frozen Source of Truth lives at `spec/SOURCE_OF_TRUTH.md` (byte-identity
guarded). All portable contract artifacts are generated from it by:

```text
python tools/generate_control_plane.py
```

Verification:

```text
python tools/verify.py self-consistency
python tools/verify.py schemas
python tools/verify.py layout
python tools/verify.py determinism
python tools/verify.py package
python tools/verify.py no-download
python tools/verify.py dialect-identity
python tools/verify.py platform-policy
python tools/verify.py python-support
python tools/verify.py support-claims
python -m unittest discover -s tests -t .
```

## Platform and support

Windows-only product support. The production server supports Windows only;
packaging, path handling, process execution, COM integration, filesystem
safety, test matrices, CI acceptance, and release qualification are designed
for Windows semantics (REQ-P00-002). Linux and macOS are not supported
product platforms and never consume product test-matrix or release-gate
scope (REQ-P00-018). The pure-logic bootstrap layer may incidentally import
on a non-Windows interpreter, but such incidental behavior is unsupported
product behavior.

Supported dialect: Microsoft Visual FoxPro 9.0 Service Pack 2 exclusively
(`microsoft.visual-foxpro.9.0.sp2`, REQ-P00-001). Syntax, object models,
file semantics, compiler behavior, and runtime behavior from older FoxPro or
Visual FoxPro releases are not automatically supported; an older-compatible
language element becomes relevant only when it is documented by the pinned
VFP9 SP2 corpus.

Supported Python: `>=3.10,<3.15` (REQ-P00-011), validated by
clean-environment acceptance on Python 3.10, 3.11, 3.12, 3.13 and 3.14.

Runtime dependencies: none at the bootstrap foundation (standard library
only). See `docs/support.md` for installation, support, and troubleshooting
policy and `docs/` for architecture, bootstrap, verification, and
capability-state documentation.

## License

MIT for first-party source; third-party components keep their own licenses
(see `third_party/README.md`). Licensed Microsoft Visual FoxPro assets are
never redistributed by this project.