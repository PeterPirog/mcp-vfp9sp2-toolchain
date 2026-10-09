# Installation, support, and troubleshooting policy

The normative product policy is the frozen Source of Truth
(`spec/SOURCE_OF_TRUTH.md`, Rev.35). This page summarizes the operator-facing
support contract for the current build; it never overrides the SOT.

## Supported product platform: Windows only

- The production server supports Windows only (REQ-P00-002).
- Packaging, path handling, process execution, COM automation, filesystem
  safety, test matrices, CI acceptance, and release qualification are
  designed for Windows semantics.
- Linux and macOS are not supported product platforms; they are never part
  of the product test matrix, CI acceptance, or release-gate scope
  (REQ-P00-018).
- Incidental import/bootstrap execution of pure logic on a non-Windows
  interpreter is possible but is unsupported product behavior and MUST NOT
  be represented as product support.

## Supported dialect and runtime

- Supported dialect: Microsoft Visual FoxPro 9.0 Service Pack 2 exclusively
  (`microsoft.visual-foxpro.9.0.sp2`, REQ-P00-001). Older FoxPro / Visual
  FoxPro release semantics are not automatically supported; an
  older-compatible element is relevant only when the pinned VFP9 SP2 corpus
  documents it (REQ-P00-004 owns the corpus baseline).
- Supported Python: `>=3.10,<3.15` (REQ-P00-011). Clean-environment
  acceptance executes on Python 3.10, 3.11, 3.12, 3.13 and 3.14
  (`tools/clean_env_smoke.py`); a missing interpreter is a typed blocker
  (`PYTHON_31X_HOST_PREREQUISITE_MISSING`), never a skipped check.
- Runtime dependencies: none in the bootstrap foundation build (standard
  library only).

## Installation (current build)

```text
python -m pip install mcp_vfp9sp2_toolchain-<version>-py3-none-any.whl
```

The install path is the standard Windows Python install flow. Builds,
tests, and installs consume the frozen canonical dependency lock
(`spec/dependency-lock.json` + `spec/dependency-lock.wheelhouse.txt`);
there is no floating re-resolution after candidate-tree sealing
(REQ-G00-018/REQ-G00-022). Full-capability operation additionally requires
operator-provided local VFP9 SP2 assets; none are vendored (REQ-P00-025).

## Troubleshooting

- `vfp-toolchain capabilities` prints the truthful capability state; every
  declared domain capability reports `NOT_IMPLEMENTED` until its milestone
  release gate qualifies it. No placeholder success exists.
- Verifier failures print a machine-readable report and exit non-zero;
  `BLOCKED` results (exit code 2) name the exact missing host capability
  and never silently pass.
- The support-claims verifier (`python tools/verify.py support-claims`)
  fails closed on any promotion-shaped non-Windows support claim in
  version-controlled product surfaces; explicit unsupported statements
  ("Linux is unsupported") are allowed and are never findings.