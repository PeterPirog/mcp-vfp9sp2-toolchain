# Security Policy

## Supported state

This is the bootstrap foundation build (`0.0.0.dev0`). No domain capability
(DBF parsing, VFP integration, PostgreSQL access, MCP serving) is
implemented yet; the attack surface of the shipped package is the
bootstrap/verification tooling itself.

## Reporting a vulnerability

Report security issues privately to the maintainers via GitHub Security
Advisories for `PeterPirog/mcp-vfp9sp2-toolchain`. Do not open public issues
for exploitable findings.

## Security architecture

The authoritative threat model lives at `spec/threat-model.json`
(schema-validated, version-controlled). It covers, among others:

- repository mutation and generated-artifact integrity;
- Windows path/reparse-point attacks and immutable source zones;
- external process execution (VFP, FoxBin2Prg, COM);
- dependency origins and supply-chain integrity;
- DBF binary/Memo data handling and value redaction;
- PostgreSQL boundary and credential redaction;
- MCP transport and prompt-injection/data-as-instruction defenses;
- evidence/provenance freshness and sensitivity classes;
- agent/controller trust boundaries;
- remote integration/publication authorization.

## Hard rules already enforced by this build

- The package performs no runtime network access or dependency download.
- No proprietary Microsoft VFP assets are vendored or redistributed.
- Generated contract artifacts are deterministically reproducible;
  hand-editing them is a verification-surface violation.
- Public test fixtures use redistributable synthetic data only.