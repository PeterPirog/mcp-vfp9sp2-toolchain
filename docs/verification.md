# Verification

How requirements are verified and how PASS is earned. The normative model is
SOT section 20 plus `REQ-AUTO-002..005`, `REQ-AUTO-040/041`, `REQ-PORT-004`,
`REQ-PORT-007`; this page summarizes the implemented dispatcher.

## States

Requirement compliance states (REQ-AUTO-040):

```text
UNASSESSED, PLANNED, NOT_IMPLEMENTED, PARTIAL, BLOCKED, PASS, NOT_APPLICABLE
```

Only `PASS` — or a release-gate-permitted `NOT_APPLICABLE` with deterministic
applicability evidence — satisfies prerequisite closure. A `NOT_APPLICABLE`
must cite the applicability rule that excludes the requirement and becomes
non-PASS automatically when that rule stops matching.

## Verifier mapping

`spec/verification.manifest.json` maps all 484 requirements to verifier
descriptors:

- `state: PLANNED` — mapped but not executable; can never return PASS
  (REQ-G00-007 / REQ-AUTO-004).
- `state: EXECUTABLE` — mapped to a concrete repo-local deterministic
  command that exists in the tree; the dispatcher refuses zero-collected-test
  results, unknown IDs, missing fixtures/capabilities, timeouts, crashes,
  malformed results, and unexpected skips (all fail closed).

## The dispatcher

```text
python tools/verify.py self-consistency   # contract self-consistency engine
python tools/verify.py schemas            # schema docs + artifact conformance
python tools/verify.py layout             # canonical layout + file set
python tools/verify.py package            # package foundation checks
python tools/verify.py determinism        # double-generation identity
python tools/verify.py no-download        # runtime network sentinel (static)
python tools/verify.py test-map           # test-module -> requirement map
python tools/verify.py dependency-lock    # frozen canonical dependency lock
                                          #   [--wheelhouse DIR] enables the
                                          #   artifact-hash, wheelhouse-equality
                                          #   and closure-from-wheel-metadata
                                          #   checks (BLOCKED without it)
python tools/verify.py dispatch --requirement REQ-... \
    --start-mode GREENFIELD --authoring-mode HYBRID \
    --operation-scope LOCAL_QUALIFICATION
```

Dispatch evaluates, in order: applicability (NOT_APPLICABLE with rule
evidence), verifier state (PLANNED cannot PASS), then command execution.

## Test suite

`tests/` is a deterministic offline suite runnable with the stdlib runner
(`python -m unittest discover -s tests -t .`) and pytest-compatible. Every
test module declares `REQUIREMENT_IDS` (machine-readable test-to-requirement
mapping, REQ-AUTO-005); `python tools/verify.py test-map` collects it.

## Protected verification surface

Tests, manifests, schemas, release-gate definitions, skip policy, thresholds,
and golden baselines are protected architecture. Removing/weakening a failing
test is not a repair. Changes to the verification surface require the
stronger review path and re-run the complete deterministic suite.

## Contract self-consistency (REQ-B00-004)

`python tools/verify.py self-consistency` re-parses the frozen SOT and
proves: every named ID exists; every range expands deterministically; every
requirement is lifecycle-classified exactly once per the canonical map;
applicability expressions are closed-vocabulary and evaluable; milestone and
requirement graphs are acyclic (independent Tarjan SCC); readiness closures
equal their graph-derived lifecycle/applicability closures; release closures
are cumulative with complete transitive prerequisites; and the meta-contract
counts/IDs/revision match. The regression fixture proves the removed
union-over-memberships rule is rejected.