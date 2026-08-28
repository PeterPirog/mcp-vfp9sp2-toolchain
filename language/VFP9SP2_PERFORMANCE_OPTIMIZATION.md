# VFP9 SP2 — Performance optimization knowledge contract

Target dialect: `microsoft.visual-foxpro.9.0.sp2`.

This file is one of the mandatory knowledge files declared in
`config.json` (`knowledge.mandatory`). It defines the **contract** for
performance work in this toolchain: what evidence kinds exist, what the
toolchain implements today, and what remains open. It is a knowledge
document, not a benchmark result — it contains no measured numbers.

## Evidence classification (mandatory)

Every performance finding MUST carry exactly one of these labels.
A predicted speedup must never be presented as measured.

| label | meaning |
|---|---|
| `MEASURED` | produced by an executed benchmark (before/after, same host, same data volume) |
| `RUNTIME_PLAN_CONFIRMED` | VFP9 runtime reported the optimization (e.g. `SYS(3054)` Rushmore status) |
| `DOCUMENTED_CANDIDATE` | stated in vendor documentation, not yet confirmed locally |
| `PREDICTED` | inferred from code shape; no runtime evidence |
| `NOT_TESTED` | identified but never exercised |
| `REJECTED_CORRECTNESS_RISK` | considered but rejected because it would change semantics |

## Performance analysis dimensions (contract)

Optimization work must analyze, where applicable:

```text
Rushmore eligibility (SYS(3054) / SYS(3056))
SET OPTIMIZE on/off interaction
CDX/IDX tag expressions and their Rushmore usability
functional/composite index design
FOR vs WHILE vs SCAN loops
CALCULATE / COUNT / SUM / MIN / MAX short-circuiting
SET ENGINEBEHAVIOR (VFP9 default 3 vs 2)
code page / collation effects on string comparisons
local vs network DBF I/O latency
locking / buffering / transaction scope
remote views / SPT / CursorAdapter materialization
form startup cost and DataEnvironment binding order
Refresh / Paint / Timer hot paths
COM / ActiveX call frequency
cold vs warm cache behavior
```

## What this repository implements today

Implemented and unit-tested in `vfp_driver.py` (see
`tests/test_perf_tools.py`):

| operation | command | VFP9 required | evidence produced |
|---|---|---|---|
| count risky/slow patterns across a project | `vfp_count_patterns` | no | pattern counts (`PREDICTED` input, not a measurement) |
| per-procedure performance access map for one form | `vfp_form_perf` | no | table access map + Rushmore FULL/PARTIAL/NONE static classification |
| find duplicate / similar PROCEDURE blocks | `vfp_find_duplicates` | no | candidate list (refactoring target) |
| benchmark critical operations before/after | `vfp_benchmark` | **yes** | `MEASURED` wall-clock + `RUNTIME_PLAN_CONFIRMED` via `SYS(3054)` when an expression is given |
| run any PRG and capture stdout/stderr/.ERR | `vfp_run_prg` | **yes** | raw execution output |

`vfp_form_perf` classifies an expression as Rushmore FULL / PARTIAL / NONE
using the static function-blocklist rules implemented in `run_form_perf()`
(e.g. functions that block index optimization, `LEFT()` vs prefix-literal
equivalence). That classification is `PREDICTED`-class evidence: it does not
execute the query.

`vfp_benchmark` generates a temporary PRG that times an operation
(`COUNT FOR` / `SEEK` / `SCAN` class operations) and, when an expression is
provided, also records `SYS(3054, 1, <expr>)` for the live cursor. The
results file is the only `MEASURED` evidence this toolchain produces.

## What is NOT implemented (honest scope)

- no automatic cold/warm cache matrix,
- no network-I/O vs local-I/O comparison harness,
- no form-startup/Refresh hot-path profiler,
- no COM-crossing frequency profiler,
- no lock/buffer/transaction behavior test matrix.

These remain `NOT_TESTED` in this repository. They must not be reported as
`MEASURED` or `RUNTIME_PLAN_CONFIRMED` until a corresponding benchmark exists.

## Rules for reporting

1. Distinguish `MEASURED` from `PREDICTED` in every report; the label travels
   with the finding.
2. A `MEASURED` result must name: host, table/row count, operation,
   expression, iteration count, cold/warm state.
3. Rushmore claims must cite `SYS(3054)`/`SYS(3056)` output or the static
   `vfp_form_perf` classification, and say which kind of evidence it is.
4. `SET ENGINEBEHAVIOR`, code page and collation changes are
   `DOCUMENTED_CANDIDATE` until verified on the target runtime.
5. Never optimize from style alone; a finding without an evidence label is
   invalid output.

## Related knowledge

- `language/VFP9SP2_CAPABILITY_MATRIX.md` — capability status per area
- `language/VFP9SP2_KNOWLEDGE_COMPLETENESS_GATE.md` — hard gate semantics
- `language/VFP9SP2_OFFLINE_KNOWLEDGE_AND_ERRATA.md` — offline errata
- `language/vfp9sp2_indexes_rushmore_spec.json` — index/Rushmore spec
- `docs/TOOLCHAIN_IMPROVEMENTS.md` — command usage guide
