# Evidence conventions

This directory holds machine-readable run evidence and its conventions.
Normative inputs: SOT section 13 (evidence hierarchy), `REQ-AUTO-046`
(sensitivity classes/redaction), `REQ-AUTO-049` (freshness binding), and the
`evidence-index`/`provenance-record` schemas in `spec/schemas/`.

## Layout

```text
evidence/
  README.md                     this file (conventions)
  bootstrap/                    bootstrap run evidence (when committed)
  brownfield/                   brownfield baseline (BROWNFIELD starts only;
                                greenfield runs mark this path NOT_APPLICABLE)
```

Run-scoped evidence produced before the repository exists (bootstrap
invocation, preflight reports, candidate trees) is retained OUTSIDE the
repository in the operator TEMP root and, where required by a gate,
transcribed into canonical evidence files here.

## Rules

- Every evidence artifact declares an evidence kind, sensitivity class
  (`PUBLIC` / `SECURE_LOCAL` / `REDACTED`), and redaction policy.
- Evidence is freshness-bound to exact commit/tree, Source of Truth hash,
  requirement-graph hash, verification-manifest hash, dependency-lock
  identity, and effective configuration/policy identity; changed inputs
  invalidate PASS evidence.
- Public evidence never contains original DBF/Memo values, credentials,
  recovery material, sensitive absolute paths, or private application source.
- Logical evidence hashes exclude timestamps, secrets, and machine-specific
  absolute paths (except where a path is required as non-authoritative local
  evidence).
- Greenfield runs MUST mark brownfield-only evidence as NOT_APPLICABLE with
  the start-state proof rather than fabricate a baseline (REQ-G00-013).