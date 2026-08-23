# Changelog

All notable changes to the VFP Integration Toolchain are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-08-23

### Added
- **Automatic BIN2PRG sync in `vfp_audit`** — the audit now runs a sync + index
  first when the `.vfp-ai` cache is missing, so class/form analysis works
  out of the box. `--skip-sync` now actually means "use the existing cache only"
  (previously it was a no-op flag).
- **`vfp_export_dir` tool** — batch-export a whole DBF tree (schema + data,
  memo/FPT) in one command via the vendored dbfbridge. New `dbf_dir` subcommand
  in `vfp_driver.py`.
- **Redundant DBF copy detection** — `vfp_audit` now reports tables that exist
  as multiple files (user backups/temp copies) with a suggested primary copy.
  New `duplicate_tables.json` artifact + "Redundant DBF Copies" report section.
- **`--include-forms` (default ON)** — full form/class/method source + PRG
  scripts exported to `<audit>/forms/`, making the audit self-contained.
- **Versioning** — `--version` on `vfp_driver` and `vfp_audit`; tool version
  stamped into the audit report.
- **MIT `LICENSE`** and a `Licensing` section in `THANKS.md`.
- **`CHANGELOG.md`** (this file).

### Changed
- `polars` is now an **optional** dependency (fast CSV path only; a pure-Python
  fallback is used when absent). Removed from required installs.
- README and agent docs corrected: 15 tools listed, "data layer" rewrite
  feasibility clarified, `tools/dbfbridge/` added to the repo structure.

### Fixed
- Removed dead code (`import sys` in `vfp_indexer.py`), an unused
  duplicate-detection method (now wired into the report), and a duplicated
  `EKS_` archive hint.
- No personal paths or project names (e.g. "Logis") remain in tracked files.

## [0.1.0] - 2026-08-22

### Added
- Vendored `dbfbridge` DBF backend (`tools/dbfbridge/`, frozen snapshot).
- `vfp_audit` — comprehensive project audit (schema, relationships, classes).
- DBF schema + data export to JSONL/CSV/JSON/XLSX (no VFP9 required).
- OpenCode tools (`tools/vfp.ts`) and the `@vfp-analyst` agent.
- `install.py` one-step installer, `FoxBin2Prg-AI.cfg` read-only profile.

[0.2.0]: https://github.com/PeterPirog/vfp-integration-toolchain/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/PeterPirog/vfp-integration-toolchain/
