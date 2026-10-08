# Bootstrap

How the repository foundation is established and verified. The normative
bootstrap model is SOT sections 12, 22-23 and requirements `REQ-G00-*`,
`REQ-B00-*`; this page summarizes the implemented path.

## Inputs (time zero)

The minimal supported start is exactly:

```text
PROJECT_HOME\            operator-selected absolute Windows directory
  <SOT file>             the only required file (any operator-chosen name)
```

The bootstrap invocation binds `project_home` and `bootstrap_sot_path`
explicitly; the Source of Truth is never discovered by scanning, newest-file
selection, or naming conventions (REQ-G00-033). Optional bindings
(`operation_scope`, `authoring_mode`, `execution_adapter`, `repository_origin`,
`target_ref`, `temp_root`, `venv_root`, `cache_roots`, `tool_roots`) default
deterministically: scope `LOCAL_QUALIFICATION`, authoring `MANUAL`,
`REPO_ROOT = PROJECT_HOME\mcp-vfp9sp2-toolchain`, `TEMP_ROOT = PROJECT_HOME\TEMP`,
`VENV_ROOT = PROJECT_HOME\.venv`.

## Start-state classification (fail closed)

`vfp_toolchain.bootstrap.classify` inspects `REPO_ROOT` occupancy without
mutating anything:

| Occupancy | Start mode |
|---|---|
| ABSENT / EMPTY | GREENFIELD |
| MATCHING_BOOTSTRAP_RESUME (provenance bound to same SOT hash) | GREENFIELD (resumable) |
| BROWNFIELD_PRODUCT | BROWNFIELD (requires full eligibility proof) |
| anything else | UNKNOWN_NONEMPTY -> AMBIGUOUS (refuses) |

Classification depends only on `REPO_ROOT`; sibling content under
`PROJECT_HOME` never influences it.

## GREENFIELD bootstrap sequence (MANUAL_BOOTSTRAP_V1 phases)

1. bind and canonicalize inputs; hash the SOT before any mutation;
2. derive `REPO_ROOT`; inspect and classify occupancy;
3. materialize the EXACT SOT bytes at `spec/SOURCE_OF_TRUTH.md`;
4. build the bootstrap control-plane candidate (canonical artifacts,
   package foundation, tests, docs, CI scaffolding);
5. generate the portable generic profile and verifier dispatch;
6. seal the candidate Git-tree identity (temporary index; no commit yet);
7. run the deterministic `BOOTSTRAP_PREFLIGHT` bound to that tree identity;
8. create the trusted local bootstrap commit only after preflight PASS;
9. verify committed-tree equality and clean working state;
10. evaluate Bootstrap Gate B0, then hand off to the committed generic
    profile.

## Dependency model

The runtime is dependency-free at B0. Build/test/validation dependencies are
declared in `pyproject.toml` and materialized in the canonical frozen lock
`spec/dependency-lock.json` (resolved exactly once from the approved PyPI
origin under authorization `OPERATOR-GREENFIELD-PYPI-B0-2026-10-08`, before
the candidate tree was sealed). `spec/dependency-lock.wheelhouse.txt` is the
require-hashes manifest for the frozen wheelhouse; builds, tests, and
installs consume the frozen lock and wheelhouse only — after sealing there
is no floating re-resolution (REQ-G00-018/REQ-G00-022). A pending
`PENDING_AWAITING_APPROVED_ORIGIN` lock remains the deterministic no-approval
fallback state generated when no frozen lock exists.

## Idempotence

Re-running the bootstrap against its own output performs no destructive
rewrite; generated deterministic artifacts may regenerate, and the
double-generation logical-identity check (`tools/verify.py determinism`)
proves their logical stability.