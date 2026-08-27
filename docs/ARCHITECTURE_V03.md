# Architecture — v0.3 Safe Refactor Workspace and Validated Form Build Pipeline

> Status: design baseline for the `feature/v03-safe-refactor-pipeline` PR.
> Companion documents: `docs/PERFORMANCE_AUDIT_ROADMAP.md`, `docs/DBC_DEPENDENCIES_ROADMAP.md`.

## 0. Central design rule

**The LLM is NOT the write layer.**

The LLM (agents `@vfp-analyst`, `@vfp-refactor`) only *proposes*: audits,
refactor plans (`refactor_plan.json`), new method code. A deterministic
Python toolchain then: checks preconditions, copies, modifies (through the
installed VFP9 COM host only), compiles, round-trips, compares, and only on a
full PASS promotes a final artifact. Every failure produces a machine-readable
`errorCode` and NO final artifact.

## 1. Current architecture (v0.2, read-only analyze plane)

```
OpenCode session
├── agents/vfp-analyst.md      (STRICT READ-ONLY agent)
├── tools/vfp.ts               (OpenCode tool wrappers, spawn vfp_driver.py)
└── vfp_driver.py              (single Python CLI; one JSON object per command)
    ├── verno          → vfp_verno.vbs       → VFP9 COM → FoxBin2Prg
    ├── convert        → vfp_convert.vbs     → VFP9 COM → oFb.execute() BIN2PRG
    ├── convert_dir    → same, per file (BIN_WRITEABLE exts)
    ├── index          → vfp_indexer.py      → .sc2/.vc2 → .vfp-ai/index.json
    ├── dbf_*          → vfp_dbf_export.py   → dbfbridge/dbfread (no VFP9)
    ├── cdx_*          → vfp_cdx.py          → structural 512-byte block scan
    │                                      → + best-effort VFP9 SYST(325) enrich
    └── audit          → vfp_audit.py        → consolidated audit dir
```

Known defects fixed by v0.3:

1. **Global process kill** — `_kill_tree()` ran `taskkill /F /IM vfp9.exe`,
   killing ALL VFP9 instances on the machine. Removed; replaced by
   PID-scoped `TerminateProcess` (vfp_protocol.run_process) with a timeout
   that returns a diagnostic instead of killing unowned processes.
2. **Sync after failed conversion** — the sync pipeline could index after
   conversion errors and present a "complete" index. Replaced by the explicit
   CONVERT → VERIFY → INDEX model with `status = COMPLETE|PARTIAL|FAILED`.
3. **`include_data` default drift** — `vfp_driver.py` audit passed
   `--include-data` (default off) while `vfp_audit.py` and docs say ON by
   default. Unified: ON by default, opt-out `--no-include-data`.
4. **Indexer method line=0** — methods indexed without line ranges. v0.3 adds
   a state-machine method parser with real line ranges.
5. **Encoding assumed cp1252** — v0.3 reads CPID from the FoxBin2Prg header
   and applies a central encoding policy (`vfp_encoding.py`).
6. **CDX heuristics presented as fact** — v0.3 tags every result with
   `confidence` + `sourceOfTruth` (`VFP9_RUNTIME` vs `PURE_PYTHON_CDX_SCAN`).
7. **`vfp_audit` CLI was missing `--only-tables` / `--no-validate`** that the
   OpenCode tool already passed. Added.

## 2. Target architecture (v0.3)

Two planes, one shared safety core:

```
┌──────────────────────────── READ-ONLY ANALYZE PLANE (unchanged) ──────────────┐
│ vfp_detect, vfp_status, vfp_export_file, vfp_export_project, vfp_export_class,│
│ vfp_sync, vfp_index, vfp_find_*, vfp_trace, vfp_export_table, vfp_list_tables,│
│ vfp_export_dir, vfp_audit, vfp_analyze_cdx, vfp_scan_cdx, vfp_snapshot,       │
│ vfp_environment                                                                │
│   - source is NEVER written (BIN2PRG whitelist in vfp_convert.vbs unchanged)   │
│   - output only to cache (.vfp-ai/) or an explicit --out directory            │
└────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────── CONTROLLED-WRITE REFACTOR PLANE (new) ────────────┐
│ vfp_create_refactor_workspace  (source → workspace copy, SHA-verified)        │
│ vfp_apply_form_patch           (RefactorPlan → method-only patch on the COPY, │
│                                via VFP9 COM; preconditions + SHA verification) │
│ vfp_compile_form               (VFP9 COMPILE FORM; .ERR only in workspace)    │
│ vfp_roundtrip_form             (final SCX → BIN2PRG → workspace/validation/)  │
│ vfp_form_inventory             (structural snapshot of an SC2)                │
│ vfp_compare_forms              (object/method inventory diff, EXPECTED/UNEXP) │
│ vfp_validate_form              (one-command state machine → PASS_VERIFIED/FAIL│
│                                + validation_report.json / .md)                │
└────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────── SHARED SAFETY CORE (single implementation) ───────┐
│ vfp_safety.py     PathSafetyGuard (canonical paths, .., case-insensitive,     │
│                   source≠target, write only under workspace, fail-closed)     │
│                   + SourceHashGuard (SHA256 manifest, mutation detection)     │
│ vfp_protocol.py   emit() {ok,status,errorCode,rc,...}, run_process()          │
│                   (PID-scoped kill only), parse_driver_output()               │
│ vfp_encoding.py   CPID from FoxBin2Prg header → codec policy (cp1250/cp852/…) │
└────────────────────────────────────────────────────────────────────────────────┘
```

### New modules

| File | Responsibility |
|---|---|
| `vfp_protocol.py` | Output protocol (single JSON, `PASS/FAIL/PARTIAL`, `errorCode`), process runner with PID-scoped cleanup, driver-output parser |
| `vfp_safety.py` | `PathSafetyGuard`, `SourceHashGuard`, SHA256 helpers, manifest compare |
| `vfp_encoding.py` | FoxBin2Prg CPID → codec; `decode_sc2`/`read_sc2_text` |
| `vfp_method_parser.py` | State-machine method lexer: PROCEDURE/ENDPROC + FUNCTION/ENDFUNC with line ranges; string/comment/continuation aware |
| `vfp_static_validate.py` | SC2/method static validation (artifacts, duplicates, END* balance, suspicious growth) |
| `vfp_form_inventory.py` | Structural form inventory (object path, baseclass, geometry, stable props) + comparison (EXPECTED/UNEXPECTED) |
| `vfp_refactor.py` | RefactorPlan schema/validation, precondition checks, workspace creation, deterministic PRG generation, VFP9 COM orchestration (apply patch / compile), roundtrip |
| `vfp9_run_prg.vbs` | Minimal VFP9 COM host: run one toolchain-generated PRG, `RC=` output |
| `vfp9_compile_form.vbs` | Minimal VFP9 COM host: `COMPILE FORM` + `.ERR` capture |
| `vfp9_env.vbs` | Environment/language inventory (VERSION, SYS(3099), CPCURRENT, SET values) |
| `vfp_refactor_plan.json` (format) | Machine-readable intermediate: objectPath, method, oldMethodSha256, newCode |

## 3. Safety boundaries (enforced by code, not by prompt)

1. **SOURCE is read-only, always.** Every write-enabled operation routes
   targets through `PathSafetyGuard`: target must be strictly *outside* the
   canonical source directory and *inside* an explicitly declared workspace.
   `source == target` and `target under source` → `SOURCE_PATH_WRITE_FORBIDDEN`.
   Fail closed on any ambiguity (unresolvable paths, symlinks into source).
2. **Source hash guard.** `snapshot` records `path/size/mtime/sha256/fileType/
   companions` into the workspace (`workspace/audit/source_manifest.json` —
   never into the source). BIN2PRG (convert/convert_dir) and the apply-patch /
   compile steps hash source files before AND after; any change →
   `SOURCE_HASH_CHANGED` (FAIL CRITICAL).
3. **No global process kill.** Only the child PID spawned by the toolchain may
   be terminated, and only via `TerminateProcess(PID)`. On timeout with no
   attributable owner the tool returns a timeout diagnostic + manual steps.
   A test scans the whole repo for `taskkill ... /IM vfp9.exe` regressions.
4. **No binary SCX/SCT assembled by hand.** Method replacement happens inside
   VFP9 (`SET PROCEDURE TO <copy>.SCX` → `STORE <code> TO <obj>.<method>` →
   `SAVE TO <copy> TYPE FormClass`), which rewrites SCX *and* SCT together.
   Python only generates a deterministic PRG; the correctness is provided by
   the installed VFP9.
5. **RefactorPlan preconditions.** Every patch carries `oldMethodSha256`.
   Before replace, the current method code is read back and hashed; mismatch →
   `PATCH_PRECONDITION_FAILED`. No "most similar" fuzzy matching.
6. **No production data mutation.** No REINDEX/PACK/ZAP/ALTER/UPDATE anywhere
   in the write plane; the apply/compile PRGs contain no such commands
   (enforced structurally: generated PRGs are produced from fixed templates).
7. **Transactional promotion.** Patches land in `workspace/working/`; only
   after `validate_form` returns `PASS_VERIFIED` may the form be promoted to
   `workspace/final/`. On FAIL the previous `final/` (if any) is untouched.

## 4. Validation pipeline (vfp_validate_form)

State machine; every step is recorded in `validation_report.json` / `.md`:

```
WS_SAFETY → SRC_SHA_OK → COPIES_OK → COMPILE_OK → ROUNDTRIP_OK
→ STATIC_OK → INV_OBJECTS_OK → INV_METHODS_OK → SRC_SHA_POST_OK → PASS_VERIFIED
```

Any step failure → `FAIL` with the failing `errorCode`; no "DONE with errors"
state exists. Report sections: SOURCE HASH STATUS, WORKSPACE STATUS, COMPILE
FORM, ERR FILE, FINAL BIN2PRG, SC2 STATIC VALIDATION, OBJECT INVENTORY,
METHOD INVENTORY, UNEXPECTED OBJECT CHANGES, UNEXPECTED PROPERTY CHANGES,
DUPLICATE CODE, ENCODING, SMOKE TEST, FINAL STATUS.

## 5. Failure / rollback model

| errorCode | Meaning | Action taken |
|---|---|---|
| `SOURCE_PATH_WRITE_FORBIDDEN` | target inside/identical to source | operation refused before any write |
| `SOURCE_HASH_CHANGED` | source file mutated during/after operation | FAIL CRITICAL; no artifact promoted |
| `MISSING_COMPANION` | .sct/.fpt/… absent for a binary | file reported; not converted |
| `PATCH_PRECONDITION_FAILED` | current method code ≠ oldMethodSha256 | patch refused; working copy untouched |
| `VFP9_NOT_AVAILABLE` | COM host not present | clean FAIL with guidance |
| `COMPILE_ERROR` | COMPILE FORM reported errors | FAIL; .ERR preserved in workspace |
| `ROUNDTRIP_FAILED` | final SCX cannot be BIN2PRG-converted | FAIL; no final artifact |
| `FORM_STRUCTURE_CHANGED` | object/property changes outside the plan | FAIL |
| `ENCODING_CORRUPTION` | CPID mapping uncertain / U+FFFD artifacts | FAIL/Warning with exact file |
| `STATIC_VALIDATION_FAILED` | method code artifacts/duplicates/END* imbalance | FAIL |
| `VFP9_TIMEOUT` | operation timed out; owner not attributable | diagnostic + manual steps; no kill |

Rollback = *do not promote*. `working/` is kept for developer diagnostics;
`final/` is never overwritten by a failed pipeline. Re-running a patch after
fixing the plan re-derives preconditions from the pristine `working/` copy or
from the source snapshot — the source itself is re-hashed first.

## 6. Output protocol (all Python CLI subcommands)

Exactly one JSON object on stdout:

```json
{"ok": true, "status": "PASS|FAIL|PARTIAL", "errorCode": null,
 "rc": 0, "version": "0.3.0", "stdout": "", "stderr": "", "data": {…}}
```

Exit code 0 when `ok`, 2 otherwise. `PARTIAL` is legal only where the
semantics allow it (e.g. sync with some conversions failed); agents MUST NOT
treat `PARTIAL` as a complete audit.
