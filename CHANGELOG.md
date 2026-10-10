# Changelog

All notable changes to this project are documented in this file.
The format follows Keep a Changelog principles; versions follow PEP 440.
Release version identity is derived from release-gate evidence, never from
manual claims (REQ-G00-009).

## [0.0.0.dev0] — bootstrap foundation (unreleased development state)

### Added
- Bootstrap repository foundation for the greenfield start mode:
  canonical control-plane layout, portable requirement graph (484
  requirements) generated deterministically from the frozen Rev.35 Source
  of Truth, verification manifest with fail-closed verifier dispatch
  semantics, compatibility/acquisition manifests, canonical frozen
  dependency lock (resolved exactly once from the approved PyPI origin,
  authorization `OPERATOR-GREENFIELD-PYPI-B0-2026-10-08`) plus its
  require-hashes wheelhouse manifest, threat model, offline JSON Schema
  2020-12 schema set, portable execution profiles (generic + pinned
  Converge), release-gate manifests (B0/BR0 readiness plus releases
  0.4.0-1.0.0, none qualified), truthful empty capability state,
  deterministic offline test suite, and Windows CI scaffolding.
- Corrected canonical milestone semantics per
  WP-SOT-REV35-SEMANTIC-AUDIT-001 (earliest-selecting-milestone execution
  basis; the union-over-memberships defect cycle is impossible and is
  covered by a dedicated regression fixture).

### Not provided (truthful)
- No domain capability (DBF/FPT, VFP knowledge, semantic analysis,
  forms/classes, optimization, refactoring, privacy, relational design,
  PostgreSQL migration, MCP serving) is implemented in this build.