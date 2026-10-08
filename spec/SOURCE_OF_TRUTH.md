# mcp-vfp9sp2-toolchain — Release-Gated Source of Truth

**Target repository:** `https://github.com/PeterPirog/mcp-vfp9sp2-toolchain`  
**Default autonomous executor:** `https://github.com/PeterPirog/converge-orchestrator`  
**Default autonomous executor baseline:** commit `1be97b75cf3b51f5ad0c2f212288f0a9edb3899b`, tree `d47b3c74b7b597dec503b4d3dca9db60e5488c93`  
**Execution portability:** Converge, Codex, OpenCode, Claude Code, and other coding agents through tool-specific adapters  
**DBF/FPT engine:** `https://github.com/PeterPirog/dbfbridge`  
**Privacy engine:** `https://github.com/PeterPirog/DBF_Anonymizer`  
**Canonical VFP binary/text engine:** `https://github.com/fdbozzo/foxbin2prg`  
**Normative VFP documentation corpus:** `https://github.com/VFPX/HelpFile`  
**Target dialect:** `microsoft.visual-foxpro.9.0.sp2`  
**Target operating system:** Windows only  
**Primary relational target:** PostgreSQL  
**Architecture language:** English  
**Architecture snapshot:** 2026-09-27  
**Revision:** 35 — master-grade freeze candidate; trusted interactive VFP execution, FoxBin2Prg text/code-page fidelity, bounded PostgreSQL connections, dependency-maturity review, and Python 3.15 forward-compatibility evidence  
**Status:** freeze candidate

---

# 0. Contract shape

This document is the tool-neutral normative contract for the product.

Section 2 contains the executable requirements. Each executable record occupies one physical Markdown line, carries one explicit stable ID, states a self-contained obligation, and includes deterministic acceptance evidence.

The format remains compatible with the current Converge Markdown contract compiler, but the meaning of a requirement does not depend on Converge. Alternative coding agents can consume the Markdown directly or use a generated portable requirement/verification manifest.

Expected compiled contract shape:

```text
mandatory records: 484
recommended records: 0
auto-hash records: 0
first id: REQ-G00-001
last id: REQ-P18-030
```

The requirement graph expresses architecture dependencies independently of starting mode. Bootstrap Gate B0 exists only to establish a valid repository foundation; public release gates identify points where a useful Windows MCP package exists even while later modernization work remains unfinished.

Revision 35 adds five narrowly scoped executable records without changing the identity or normative meaning of the 479 Revision-34 records: trusted interactive-session VFP execution (`REQ-P06-014`), FoxBin2Prg text/code-page fidelity (`REQ-P06-015`), bounded PostgreSQL connection management (`REQ-P13-024`), final DBF_Anonymizer dependency-maturity review (`REQ-P18-029`), and Python 3.15 advisory forward-compatibility evidence (`REQ-P18-030`).

---

# 1. Product mission and release strategy

The product is a Windows-local MCP platform for long-term work with Microsoft Visual FoxPro 9.0 SP2 applications.

The target implementation can begin from either a completely empty repository or an existing repository. Both starting modes converge on the same product architecture, requirement IDs, verification semantics, public contracts, and release gates; the starting mode changes only bootstrap and compatibility work.

The product evolves through usable capability layers:

```text
FOUNDATION
  Windows-only Core Service
  path/source safety
  early MCP shell

DATA + KNOWLEDGE
  DBF
  DBF + FPT Memo
  original and anonymized datasets
  VFPX VFP9 SP2 Help

APPLICATION UNDERSTANDING
  PRG/H/MPR
  PJX
  SCX/SCT
  VCX/VCT
  DBC/views/connections
  dependencies and impact

OPTIMIZATION
  CDX/IDX
  Rushmore
  SYS(3054)
  benchmarks

CONTROLLED REFACTORING
  FoxBin2Prg
  workspace changes
  VFP9 SP2 compile/build
  semantic round-trip validation

PRIVACY
  DBF_Anonymizer
  lineage
  anonymized-data verification

RELATIONAL MODERNIZATION
  canonical relational target model
  PostgreSQL schema design
  VFP SQL/xBase translation
  shadow migration
  parity validation
  VFP-to-PostgreSQL transition
  cutover planning
```

The release gates avoid a long interval where repository development produces no deployable user value, while deterministic verifier coverage and cumulative regression gates prevent autonomous progress from erasing previously delivered capabilities.

---

# 2. Executable target-repository contract

## Phase G0 — Start-state classification and deterministic repository bootstrap

`REQ-G00-001` — The implementation workflow MUST classify the target start state as `GREENFIELD`, `BROWNFIELD`, or `AMBIGUOUS` before product changes begin by examining the declared `REPO_ROOT` and its target-repository metadata rather than the surrounding `PROJECT_HOME`, where `GREENFIELD` contains no prior target-product implementation or public contract, `BROWNFIELD` contains prior target-product implementation or public-contract evidence, and `AMBIGUOUS` contains conflicting target-repository signals; acceptance evidence is absent-repository, empty-directory, empty-Git-repository, existing-product, mixed-target-state, and non-empty-project-home classification fixtures.

`REQ-G00-002` — An `AMBIGUOUS` start state MUST fail closed before autonomous coding until an explicit operator decision is supplied through the bootstrap invocation or a later signed/recorded decision: `UNKNOWN_NONEMPTY` MUST NOT be converted to in-place `GREENFIELD`, and it can be accepted as `BROWNFIELD` only after the non-mutating brownfield eligibility rules in `REQ-G00-043` pass; otherwise the operator MUST externally remediate the target state or select a different `PROJECT_HOME` and trigger a fresh classification, with every decision recorded in run provenance; acceptance evidence is ambiguous-state refusal, eligible-brownfield preservation resolution, attempted-in-place-greenfield refusal, ineligible-brownfield refusal, externally-remediated reclassification, and provenance fixtures.

`REQ-G00-003` — A `GREENFIELD` start MUST be supported when the declared `REPO_ROOT` is absent, is a completely empty filesystem directory, or is a Git repository with no product files or product commits, without relying on any pre-existing README, package metadata, tests, source tree, generated manifest, CI workflow, or implementation-specific documentation inside the target repository; acceptance evidence is end-to-end bootstrap fixtures for absent `REPO_ROOT`, empty `REPO_ROOT`, and empty Git target repository while `PROJECT_HOME` contains unrelated tooling files.

`REQ-G00-004` — The greenfield bootstrap MUST create the canonical repository layout defined by `REQ-G00-024`, including Python `src/vfp_toolchain`, distribution name `mcp-vfp9sp2-toolchain`, PEP 517/PEP 621-compatible `pyproject.toml`, Python compatibility `>=3.10,<3.15`, typed-package marker, tests, documentation, portable schemas/manifests, tools, third-party provenance, and Windows CI scaffolding without implementing fake domain success behavior; acceptance evidence is exact repository-layout, package-metadata, import, canonical-contract-discovery, and no-placeholder-success tests.

`REQ-G00-005` — The greenfield bootstrap MUST create at least `README.md`, `LICENSE`, `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`, `.gitignore`, third-party notices/provenance scaffolding, deterministic test configuration, static-analysis configuration, package build configuration, and Windows CI scaffolding, and each created file MUST be usable without hidden chat context; acceptance evidence is bootstrap file-set validation and clean-repository documentation lint.

`REQ-G00-006` — The greenfield bootstrap MUST establish at the canonical paths defined by `REQ-G00-024` the portable requirement graph, verification manifest and schemas, compatibility/acquisition/dependency-lock artifacts, threat model, release-gate schema/location, evidence conventions, execution-profile bindings, and deterministic verifier dispatcher before ordinary feature implementation begins; acceptance evidence is canonical-path/schema validation and an empty-product compliance report in which future product requirements are non-PASS rather than omitted.

`REQ-G00-007` — The greenfield verifier dispatcher MUST be able to represent a mapped but not yet executable verifier as `PLANNED` or `NOT_IMPLEMENTED` without returning PASS, and MUST become executable before the associated requirement can transition to PASS; acceptance evidence is planned-verifier, executable-verifier, false-PASS refusal, and transition fixtures.

`REQ-G00-008` — Greenfield bootstrap quality gates MUST prove that the package builds as wheel and sdist, installs into a clean supported Windows Python environment, imports `vfp_toolchain`, exposes only truthful bootstrap metadata/capability state, and performs no runtime network download; acceptance evidence is clean-build, clean-wheel-install, import, capability-state, and network-sentinel tests.

`REQ-G00-009` — Before the first release-qualification gate, the repository MUST use PEP 440-compatible development versions that cannot be confused with a passed qualified release, and the qualified public version MUST be derived from the release-gate manifest rather than manually claimed by agent prose; later public publication MUST reference that already-qualified version identity rather than invent a new one; acceptance evidence is pre-release version, qualification-gate-to-version, publication-version-identity, and false-release-claim tests.

`REQ-G00-010` — Greenfield bootstrap MUST be idempotent: rerunning it against its own completed output MUST produce no destructive rewrite, no duplicate configuration, and no semantic diff except explicitly regenerated deterministic artifacts; acceptance evidence is two-run clean-diff tests.

`REQ-G00-011` — A greenfield bootstrap MUST NOT require Visual FoxPro, PostgreSQL, psqlODBC, FoxBin2Prg execution, DBF datasets, or private operator applications merely to create and validate the repository foundation, while later capability gates retain their own trusted-host prerequisites; acceptance evidence is bootstrap on a clean Windows host containing only the supported Python/build toolchain.

`REQ-G00-012` — The execution profile MUST handle a target Git repository with no commits or default branch by establishing `main` as the canonical initial branch and creating the bootstrap commit through the integration layer before any workflow that requires a base commit, and ordinary coding-agent credentials MUST remain unable to bypass the configured integration policy; acceptance evidence is no-commit repository bootstrap, canonical-branch, and credential-boundary tests.

`REQ-G00-013` — A `BROWNFIELD` start MUST execute the brownfield-baseline and compatibility-preservation requirements, while a `GREENFIELD` start MUST mark brownfield-only migration evidence as `NOT_APPLICABLE` with the start-state proof rather than fabricate a baseline; acceptance evidence is greenfield/brownfield conditional-compliance fixtures.

`REQ-G00-014` — Cross-start-mode equivalence MUST be a release-lifecycle check rather than a Bootstrap Gate B0 prerequisite, and whenever the same public release has independently qualified `GREENFIELD` and `BROWNFIELD` builds those builds MUST expose equivalent public Core models, MCP tool/resource schemas, error semantics, capability semantics, package entry points, and release-gate behavior unless the Source of Truth explicitly defines a compatibility exception; acceptance evidence is lifecycle classification plus cross-start-mode public-contract differential tests.

`REQ-G00-015` — Bootstrap Gate B0 MUST establish a deterministic greenfield scenario definition parameterized by `authoring_mode` that starts from an empty repository and targets the first qualified release without hand-created generated manifests, undeclared bootstrap artifacts, or undocumented steps; the `AUTONOMOUS` variant MUST run without direct human source-code editing, the `MANUAL` variant can accept human-authored candidate changes with complete provenance, and the `HYBRID` variant can accept both only with the actor attribution required by `REQ-G00-055`, while actual execution of the complete selected-mode scenario belongs to the first release-qualification gate rather than B0; acceptance evidence is hash-bound manual/autonomous/hybrid scenario definitions plus a bootstrap check proving that all scenario inputs are declared.

`REQ-G00-016` — The greenfield repository MUST use the MIT License for first-party source and package metadata, preserving the licensing intent of the target project while keeping third-party licenses separate and intact; acceptance evidence is exact project-license classification, package-metadata license checks, and third-party-license separation tests.

`REQ-G00-017` — The greenfield bootstrap MUST create `.gitattributes` rules that preserve deterministic repository text normalization, keep Windows script line endings explicit, classify VFP binary/data artifact families and byte-exact vendored snapshots as non-text, and prevent Git line-ending conversion from mutating DBF/FPT/CDX/IDX/SCX/SCT/VCX/VCT/FRX/FRT/LBX/LBT/MNX/MNT/PJX/PJT/DBC/DCT/DCX or other declared binary fixtures; acceptance evidence is checkout/commit byte-identity tests on synthetic binary fixtures plus text/script line-ending tests.

`REQ-G00-018` — The greenfield bootstrap MUST establish a deterministic dependency-lock mechanism covering direct and transitive build, test, runtime, and optional-profile Python dependencies with exact resolved versions and integrity hashes or equivalent immutable identities, and the lock MUST be sufficient to construct the release wheelhouse without resolving floating dependency versions; acceptance evidence is lock-schema validation, fresh locked environment creation, tampered-artifact rejection, and no-floating-resolution tests.

`REQ-G00-019` — The greenfield bootstrap MUST establish a machine-readable external-source acquisition manifest for every non-runtime-download upstream required by the Source of Truth, including repository or package origin, immutable commit/version identity, acquisition mode, expected license/provenance inputs, destination role, and post-acquisition content fingerprint; any controller bootstrap source consumed before `REPO_ROOT/spec/acquisition.manifest.json` exists MUST first be authorized directly by the immutable Source of Truth baseline in `REQ-G00-059` or an explicit adapter override covered by `REQ-G00-060`, and the resulting verified controller-acquisition evidence MUST be transcribed into the canonical acquisition manifest once the control plane exists; connected preparation MUST fetch only approved origins while offline preparation MUST consume a preseeded cache with the same identities; acceptance evidence is pre-controller-to-canonical-manifest identity, connected, offline-cache, wrong-origin, wrong-commit, content-mismatch, and undeclared-source fixtures.

`REQ-G00-020` — The canonical public console entry points MUST be `vfp-toolchain` for the operator CLI and `mcp-vfp9sp2` for the MCP server, both MUST delegate to the same transport-neutral Core Service, and a brownfield migration can retain older launch scripts only as compatibility shims that do not become the canonical interface; acceptance evidence is clean-wheel command discovery, shared-Core dispatch, greenfield/brownfield equivalence, and legacy-shim tests.

`REQ-G00-021` — When `GREENFIELD` begins with an absent or non-Git `REPO_ROOT`, the bootstrap integration MUST create the declared repository directory, initialize Git locally with `main` as the canonical initial branch, materialize the complete bootstrap candidate tree, run a deterministic `BOOTSTRAP_PREFLIGHT` bound to that candidate Git-tree identity before any ref is advanced, create the first commit through the trusted integration layer only after preflight PASS, verify that the committed tree is byte-identical to the preflighted tree, and then finalize B0 against the resulting commit before Phase 0 work can begin; acceptance evidence is absent-repository-to-main, empty-directory-to-main, preflight-failure-no-ref-advance, candidate-tree/commit-tree equality, final-B0 commit binding, and rerun-idempotence tests.

`REQ-G00-022` — A greenfield run with no pre-existing approved dependency lock MUST perform dependency resolution exactly once before the bootstrap candidate Git-tree identity is sealed, using direct compatibility/baseline constraints already materialized in the candidate tree and destined to become version-controlled in the first commit, plus a recorded resolver/toolchain identity and approved package-index origins; the complete direct/transitive result with artifact hashes MUST become the canonical tracked bootstrap lock inside that same candidate tree, and after the tree is sealed B0, builds, tests, wheelhouse creation, and releases MUST consume the frozen lock without floating re-resolution; acceptance evidence is one-time-resolution, precommit-candidate-constraint, resolver/origin receipt, candidate-tree lock inclusion, post-seal-resolution refusal, and rerun-from-frozen-lock tests.

`REQ-G00-023` — Before the applicable start-readiness gate can pass, the target repository MUST contain the exact byte-for-byte Source of Truth input at `REPO_ROOT/spec/SOURCE_OF_TRUTH.md`, its SHA-256 MUST equal the Source of Truth identity used to generate every portable contract artifact, line-ending normalization or regeneration MUST NOT alter those bytes, and any later change to that file MUST be treated as explicit Source of Truth contract evolution rather than an ordinary implementation edit; acceptance evidence is external-input-to-repository byte identity for both start modes, SOT-hash equality, line-ending-preservation, tampered-copy refusal, and ordinary-edit refusal tests.

`REQ-G00-024` — The portable control-plane repository layout MUST use paths relative to the declared `REPO_ROOT`: `spec/SOURCE_OF_TRUTH.md`, `spec/requirements.graph.json`, `spec/verification.manifest.json`, `spec/compatibility.manifest.json`, `spec/acquisition.manifest.json`, `spec/dependency-lock.json`, `spec/threat-model.json`, `spec/schemas/`, `execution-profiles/converge.yaml`, `execution-profiles/generic.json`, `release-gates/`, `evidence/`, `third_party/`, `src/vfp_toolchain/`, `tests/`, `docs/`, `tools/`, and `.github/workflows/`; tool-native auxiliary files can coexist but MUST NOT replace, rename, or become the sole authoritative form of the portable contract artifacts; acceptance evidence is exact `REPO_ROOT`-relative layout validation, clean-checkout discovery, alternate-tool auxiliary-file coexistence, and missing/renamed-canonical-path failure tests.

`REQ-G00-025` — The canonical schema directory `spec/schemas/` MUST contain offline-resolvable JSON Schema 2020-12 documents for at least requirement graph, verification manifest, compatibility manifest, acquisition manifest, dependency lock, threat model, bootstrap invocation/evidence, brownfield preflight/start baseline, release-gate manifest, evidence index, capability snapshot, provenance record, and execution-profile binding, with stable schema identities referenced by the corresponding canonical artifacts or run evidence; acceptance evidence is exact required-schema-set validation, artifact/evidence-to-schema resolution, clean-offline validation, missing-schema refusal, and schema-identity mismatch tests.

`REQ-G00-026` — Every execution profile MUST distinguish an operator-selected absolute Windows `PROJECT_HOME` from the target `REPO_ROOT`, MUST NOT hard-code a drive letter or derive either root from the process current directory, and MUST resolve the canonical target repository as the direct child `mcp-vfp9sp2-toolchain` under `PROJECT_HOME`; `PROJECT_HOME` itself MUST be permitted to exist with no content other than the explicitly bound Source of Truth file; acceptance evidence is equivalent runs with project homes on different drive letters, a path containing spaces, Source-of-Truth-only ProjectHome, unrelated process current directories, and wrong-repository-child refusal.

`REQ-G00-027` — `PROJECT_HOME` can contain sibling orchestration tools, Converge installations or clones, external frozen Source of Truth inputs, TEMP directories, Python virtual environments, dependency/source caches, logs, and other repositories without changing the target start-state classification, because `GREENFIELD`/`BROWNFIELD` classification MUST be scoped only to `REPO_ROOT` and its target Git history/contract state; acceptance evidence is non-empty-project-home/absent-repo greenfield, sibling-Git-repository greenfield, existing-target brownfield, and sibling-contract-canary tests.

`REQ-G00-028` — The execution profile MUST bind logical filesystem roles for `project_home`, `repo_root`, `temp_root`, `venv_root`, `cache_roots`, `tool_roots`, `bootstrap_sot_path`, canonical product repository identity, optional local repository origin, and brownfield `target_ref`, MUST canonicalize each bound Windows path before use, and MUST permit TEMP, venv, caches, and orchestration/tool roots to be absent initially and later reside as siblings inside `PROJECT_HOME` while keeping them outside `REPO_ROOT` unless a canonical repository path explicitly requires otherwise; acceptance evidence is Source-of-Truth-only initial topology, lazy sibling-role creation, canonical-repository-identity, target-ref, path-with-spaces, alternate-drive, role-overlap refusal, and effective-profile snapshot tests.

`REQ-G00-029` — Every Git, package-build, test, release, repository-status, contract-generation, and source-tree command that operates on the target project MUST address `REPO_ROOT` explicitly through process working-directory configuration or an equivalent repository-root argument and MUST NOT discover the target repository by walking upward from `PROJECT_HOME`, TEMP, venv, a Converge checkout, or another sibling repository; acceptance evidence is nested/sibling Git repositories, misleading current-directory, explicit-root command tracing, and wrong-repository-mutation sentinels.

`REQ-G00-030` — The bootstrap Source of Truth input can be the only file initially present in `PROJECT_HOME`, can have any operator-chosen filename, and can alternatively reside at another explicitly bound readable path, but its exact declared bytes and source-path provenance MUST be copied into `REPO_ROOT/spec/SOURCE_OF_TRUTH.md` before the applicable readiness gate; for `BROWNFIELD`, that repository mutation MUST occur only after the immutable pre-mutation capture required by `REQ-G00-042`, while after the repository copy is commit- or baseline-bound it becomes the authoritative target-repository contract for the run and no automatic bidirectional synchronization with the external copy is permitted; acceptance evidence is ProjectHome-single-SOT bootstrap, arbitrary-input-filename, greenfield direct-copy, brownfield-capture-before-copy, byte-identical in-repository copy, external-copy-later-change non-effect, and explicit-contract-evolution replacement tests.

`REQ-G00-031` — A clean checkout of `REPO_ROOT` MUST remain sufficient to discover and validate the portable product contract without access to sibling files in `PROJECT_HOME`; execution can use explicitly bound external tooling, caches, proprietary VFP assets, or trusted runtimes, but no build, test, package, release, or compliance PASS can depend on undeclared sibling source/configuration content; acceptance evidence is sibling-removal contract validation, undeclared-sibling-dependency failure, explicit-tool-root success, and clean-checkout package/contract discovery tests.

`REQ-G00-032` — A supported minimal filesystem start MUST consist only of an operator-selected absolute Windows `PROJECT_HOME` directory and one readable frozen Source of Truth file identified explicitly by `bootstrap_sot_path`; `REPO_ROOT`, Git metadata, Converge/tool directories, TEMP, venv, caches, logs, execution profiles, generated manifests, bootstrap scripts, autonomous runtime configuration, and all product source files can be absent at time zero, and their absence MUST NOT prevent start-state classification, `MANUAL_BOOTSTRAP_V1` execution, `AUTONOMOUS_BOOTSTRAP_V1` execution, controller provisioning, or bootstrap preparation; acceptance evidence is ProjectHome-plus-SOT-only manual, autonomous, and hybrid filesystem starts, alternate-drive/path, absent-helper-directory, absent-profile, absent-script, absent-runtime-config, absent-repository, and unreadable-SOT fixtures.

`REQ-G00-033` — The bootstrap MUST never discover the Source of Truth by filename guessing, newest-file selection, directory scanning, or implicit convention: `bootstrap_sot_path` MUST be an explicit readable file binding whose SHA-256 is computed before repository mutation, and if multiple plausible Markdown/specification files exist only the explicitly bound file can become `REPO_ROOT/spec/SOURCE_OF_TRUTH.md`; acceptance evidence is one-file, multiple-candidate, misleading-newer-file, renamed-input, unreadable-path, and hash-before-mutation tests.

`REQ-G00-034` — Before writing inside an existing `REPO_ROOT`, start-state inspection MUST classify its occupancy as `ABSENT`, `EMPTY`, `MATCHING_BOOTSTRAP_RESUME`, `BROWNFIELD_PRODUCT`, or `UNKNOWN_NONEMPTY`: `ABSENT` and `EMPTY` map to `GREENFIELD`; `MATCHING_BOOTSTRAP_RESUME` maps to resumable `GREENFIELD`; `BROWNFIELD_PRODUCT` requires recognizable target-product evidence plus the non-mutating Git/working-tree eligibility proof in `REQ-G00-043` and maps to `BROWNFIELD`; every other non-empty state maps to `UNKNOWN_NONEMPTY` and therefore `AMBIGUOUS`; acceptance evidence is absent, empty, matching-resume, clean-committed-brownfield, dirty-Git, uncommitted-Git, non-Git-product, unknown-content, and deterministic repeated-classification fixtures.

`REQ-G00-035` — `MATCHING_BOOTSTRAP_RESUME` MUST require machine-verifiable bootstrap provenance bound to the same Source of Truth hash, declared `PROJECT_HOME`/`REPO_ROOT`, candidate-tree or committed-tree identity, and bootstrap schema version, while partial files without matching provenance MUST remain `UNKNOWN_NONEMPTY`; acceptance evidence is matching-resume, different-SOT, different-root, corrupted-provenance, stale-schema, and orphaned-partial-tree fixtures.

`REQ-G00-036` — Before start-state classification completes, bootstrap logic MUST treat pre-existing `REPO_ROOT` content as immutable inspection input and MUST NOT delete, rename, truncate, overwrite, initialize Git over unknown content, or move files out of the way; after classification, greenfield creation can write only to absent/empty or verified matching-resume state, while brownfield writes remain subject to brownfield baseline and integration policy; acceptance evidence is unknown-content no-write sentinels, empty-root creation, matching-resume continuation, and brownfield-baseline-before-write tests.

`REQ-G00-037` — Missing sibling workspace roles under `PROJECT_HOME` MUST be created only when needed from the effective execution profile, with deterministic defaults `TEMP_ROOT=PROJECT_HOME\TEMP`, `VENV_ROOT=PROJECT_HOME\.venv`, and `CACHE_ROOT=PROJECT_HOME\cache` when those roles are not overridden, while `TOOL_ROOTS` remain explicitly bound or are provisioned only through the controller/tool acquisition rules in `REQ-G00-059` through `REQ-G00-062`, and none of these sibling paths is required to exist at time zero; acceptance evidence is ProjectHome-only lazy creation, explicit-override, default-path, autonomous-controller-provisioning, alternate-drive, and no-helper-directory-prerequisite tests.

`REQ-G00-038` — Bootstrap host prerequisites MUST distinguish filesystem state from executable prerequisites: target-project directories and tools inside `PROJECT_HOME` can be absent, while the minimal `MANUAL` path requires an available Git implementation and supported Python/build environment and excludes pre-existing project scripts, execution profiles, coding-agent, model-provider, Converge, and autonomous-orchestration prerequisites; when `MANUAL` starts before `execution-profiles/generic.json` exists, the embedded `MANUAL_BOOTSTRAP_V1` contract defined by `REQ-G00-063` through `REQ-G00-065` MUST provide the time-zero procedure; when `AUTONOMOUS` starts before an executable target repository and external controller runtime configuration exist, `AUTONOMOUS_BOOTSTRAP_V1` from `REQ-G00-070` through `REQ-G00-073` MUST establish only the bootstrap/control-plane seed and runtime handoff prerequisites before Converge or another autonomous adapter begins product implementation, while controller acquisition and model routing remain governed by `REQ-G00-059` through `REQ-G00-062` and `REQ-G00-066` through `REQ-G00-069`; inability to satisfy an active prerequisite MUST produce typed prerequisite evidence without changing target start-state classification; acceptance evidence is SOT-only manual bootstrap, SOT-only autonomous bootstrap seed, manual-no-profile/no-script/no-Converge/no-model success, missing-Git/Python refusal, controller-unavailable refusal, model-routing-unavailable refusal, and later-capability prerequisite tests.

`REQ-G00-039` — Before any repository mutation, the bootstrap procedure MUST construct the same tool-neutral bootstrap invocation logical object from explicit operator inputs with required fields `project_home` and `bootstrap_sot_path` and optional fields `operation_scope`, `authoring_mode`, `execution_adapter`, `autonomous_model_routing_ref`, `remote_authorization_ref`, `repository_origin`, `target_ref`, `temp_root`, `venv_root`, `cache_roots`, and `tool_roots`; omitted `operation_scope` MUST resolve according to `REQ-G00-052`, omitted `authoring_mode` and `execution_adapter` MUST resolve according to `REQ-G00-054` and `REQ-G00-058`, an omitted `autonomous_model_routing_ref` can remain unresolved until the autonomous model preflight but MUST NOT cause implicit model selection, the transport used to supply values can be a human-operated CLI/script procedure, UI, API, Converge, or another conforming adapter, and omitted required fields MUST fail before workspace mutation; acceptance evidence is manual-script/CLI, equivalent UI/API/Converge logical-object fixtures, default-local-scope, authoring/controller defaults, explicit-model-routing binding, omitted-routing-no-implicit-selection, explicit-adapter override, required-field refusal, target-ref override, optional-role override, and transport-independence tests.

`REQ-G00-040` — The bootstrap invocation logical object MUST canonicalize Windows path fields before use, record the pre-mutation Source of Truth SHA-256, effective controller/adapter identity, effective operation scope, effective authoring mode, remote-authorization identity when present, and autonomous model-routing reference/hash when resolved, derive `repo_root` according to `REQ-G00-026`, resolve canonical product repository identity and effective `target_ref` according to `REQ-G00-046`, compute a canonical logical-content hash independent of transport serialization, and bind that hash into start-state, `BOOTSTRAP_PREFLIGHT`, `BROWNFIELD_PREFLIGHT`, B0/BR0, authoring/integration, qualification, publication, and run-provenance evidence without committing secrets or machine-specific absolute invocation paths as portable product contract data; acceptance evidence is path-canonicalization, controller/scope/authoring/routing/authorization binding, repository/ref resolution, transport-serialization equivalence, invocation-hash binding, different-input invalidation, secret-redaction, and no-machine-path-in-portable-contract tests.

`REQ-G00-041` — The bootstrap invocation is an ephemeral run-control input rather than a required time-zero file: a supported start with only `PROJECT_HOME` plus the Source of Truth file MUST remain valid when the operator supplies `project_home` and `bootstrap_sot_path` through the selected human-operated or automated controller path, and after TEMP/evidence facilities exist the effective redacted invocation can be retained as run evidence without becoming a prerequisite for clean checkout or release installation; acceptance evidence is manual-no-bootstrap-config-file start, automated-no-bootstrap-config-file start, retained-redacted-run-evidence, sibling-evidence deletion/restart, and clean-checkout independence tests.

`REQ-G00-042` — For a `BROWNFIELD` start, before any mutation inside `REPO_ROOT`, the selected bootstrap procedure or trusted controller MUST create `BROWNFIELD_PREFLIGHT` evidence outside `REPO_ROOT` that binds the bootstrap-invocation hash, Source of Truth hash, canonical product repository identity, local repository origin when present, effective `target_ref`, exact Git HEAD commit/tree identity, clean tracked/untracked working-state proof, declared submodule state, canonical authoritative-content inventory hash, and the non-authoritative ignored-local-state inventory defined by `REQ-G00-050`, plus the machine-readable current public-surface baseline required by `REQ-P00-020`; acceptance evidence is manual-preflight, automated-preflight, clean-repository preflight, wrong-target-ref, changed-HEAD invalidation, tracked/untracked/conflicted refusal, ignored-local-state capture, submodule-state detection, content-inventory tamper detection, and no-target-tree-write tracing.

`REQ-G00-043` — Automatic `BROWNFIELD_PRODUCT` eligibility MUST require a recognizable target-product implementation or contract, a valid Git repository with at least one reachable commit, an effective local branch `target_ref` whose resolved commit equals HEAD, no staged/modified/deleted/non-ignored-untracked/conflicted target content, and ignored local entries that satisfy `REQ-G00-050`; recognizable product content with no Git repository, a Git repository with no commit, detached HEAD, target-ref mismatch, prohibited working-state changes, or unsafe ignored-local-state entries MUST remain `UNKNOWN_NONEMPTY`/`AMBIGUOUS` until the operator externally establishes the eligible state and reruns classification; acceptance evidence is clean-committed-target-ref eligibility, safe-ignored-local-state eligibility, non-Git-product refusal, no-commit refusal, detached-HEAD refusal, wrong-ref refusal, each prohibited-working-state refusal, unsafe-ignored-state refusal, external-remediation reclassification, and no-automatic-user-content-commit tests.

`REQ-G00-044` — After `BROWNFIELD_PREFLIGHT` is sealed, brownfield bootstrap MUST construct an isolated candidate Git tree or temporary worktree rooted at the captured starting commit without mutating the active `REPO_ROOT` worktree or advancing `target_ref`, MUST materialize the canonical Source of Truth/control-plane artifacts and retained baseline evidence into that candidate, MUST preserve the captured starting product tree and public behavior except for explicitly identified bootstrap/control-plane additions, and MUST retain the canonical pre-mutation baseline at candidate path `evidence/brownfield/start-baseline.json`; acceptance evidence is isolated-candidate creation, no-active-worktree mutation, control-plane-only candidate diff, starting-tree preservation, retained-baseline hash equality, and candidate-recreation tests.

`REQ-G00-045` — When a `BROWNFIELD` start lacks an approved canonical `spec/dependency-lock.json`, the bootstrap MUST derive the initial brownfield lock exactly once inside the isolated candidate created by `REQ-G00-044` from the captured repository's pre-existing declared dependency inputs using a recorded resolver/toolchain identity and approved origins, MUST mark the resulting lock role as `BROWNFIELD_BASELINE`, MUST fail BR0 rather than invent undeclared direct dependencies when the existing dependency inputs are insufficient or unsatisfiable, and later adoption of target architecture baselines MUST proceed through explicit dependency-boundary evolution; acceptance evidence is deterministic existing-input resolution, candidate-only lock creation, missing-input refusal, unsatisfiable-input refusal, origin/integrity capture, baseline-role validation, and later-target-baseline migration tests.

`REQ-G00-046` — The canonical public product repository identity MUST be `https://github.com/PeterPirog/mcp-vfp9sp2-toolchain`; the effective greenfield `target_ref` MUST be `refs/heads/main`, the default brownfield `target_ref` MUST be `refs/heads/main` unless the operator explicitly binds another existing local branch, a greenfield repository can remain local with no remote during implementation, and a brownfield local origin can be absent or differ when explicitly recorded as a fork/mirror; repository-origin differences MUST NOT silently change product semantics, and a production release MUST NOT claim publication to the canonical repository unless the trusted release layer verifies that destination identity; acceptance evidence is no-remote greenfield-main, canonical-origin, recorded-fork, brownfield-default-main, explicit-local-branch, wrong-ref, and production-destination identity tests.

`REQ-G00-047` — The isolated brownfield candidate MUST pass a deterministic `BROWNFIELD_BOOTSTRAP_PREFLIGHT` before commit creation, proving Source of Truth/control-plane completeness, retained start-baseline equality, dependency-lock state, candidate-tree integrity, allowed bootstrap-diff paths, package/contract bootstrap checks, absence of changes to captured product files outside explicitly version-controlled bootstrap migration paths, and collision-free compatibility with the captured ignored local state under `REQ-G00-051`; acceptance evidence is valid-candidate, missing-control-plane, baseline-mismatch, lock-mismatch, unauthorized-product-change, ignored-path collision, and candidate-tree-tamper fixtures.

`REQ-G00-048` — After `BROWNFIELD_BOOTSTRAP_PREFLIGHT` passes, the trusted integration layer MUST create exactly one brownfield bootstrap commit whose sole parent is the captured starting HEAD and whose tree equals the approved candidate tree, MUST advance the effective local `target_ref` only by fast-forward from the captured starting HEAD to that bootstrap commit, MUST materialize that exact committed tracked tree in `REPO_ROOT` while preserving the approved ignored local entries byte-for-byte and path-for-path according to `REQ-G00-051`, and MUST leave the target tracked/untracked working state clean; acceptance evidence is parent/tree identity, fast-forward-only ref update, candidate/commit/tracked-worktree equality, ignored-local-state preservation, non-fast-forward refusal, commit-failure-no-ref-advance, and clean-working-state tests.

`REQ-G00-049` — Final `BR0` evidence MUST bind both the immutable pre-mutation starting commit/tree and the brownfield bootstrap commit/tree, effective `target_ref`, Source of Truth hash, bootstrap-invocation hash, retained baseline hash, and brownfield dependency-lock hash, and Phase 0 product work MUST NOT begin until `REPO_ROOT` is clean at the exact bootstrap commit; acceptance evidence is dual-commit BR0 binding, dirty-after-bootstrap refusal, wrong-ref refusal, changed-bootstrap-commit invalidation, and clean-ready brownfield tests.

`REQ-G00-050` — Brownfield working-state classification MUST separate authoritative Git content from ignored local state: the authoritative content identity is the captured commit tree plus declared submodule commit identities; staged/modified/deleted/conflicted and non-ignored untracked entries remain disqualifying; ignored entries can remain only when their ignore status is computed deterministically with global user ignore configuration disabled, repository `.gitignore` rules honored, repository-local `.git/info/exclude` identity captured, and a canonical ignored-state inventory records relative path, entry type, and reparse/symlink classification without storing file bytes or treating ignored contents as product evidence; acceptance evidence is global-ignore-disabled, repository-gitignore, info-exclude-hash, safe-ignored-file, non-ignored-untracked refusal, ignored-reparse classification, and ignored-content-non-authority tests.

`REQ-G00-051` — Before the brownfield bootstrap commit is materialized into active `REPO_ROOT`, the integration layer MUST compare every path introduced or changed by the approved bootstrap candidate against the captured ignored-state inventory and MUST refuse exact-path, ancestor/descendant, case-normalized, short-name, or resolved reparse/symlink collisions; successful materialization MUST NOT run destructive clean/reset operations against ignored content, MUST preserve the captured ignored path set and bytes, and MUST verify after checkout that the tracked tree equals the bootstrap commit while the ignored local state remains unchanged; acceptance evidence is exact collision, ancestor collision, descendant collision, case collision, short-name collision, reparse collision, ignored-byte preservation, destructive-clean refusal, and post-materialization dual-state verification tests.

`REQ-G00-052` — Every run MUST have an explicit effective operation scope from `LOCAL_QUALIFICATION`, `REMOTE_INTEGRATION`, or `PUBLICATION`; omission MUST resolve to `LOCAL_QUALIFICATION`, which can build, test, integrate locally, create local commits, and qualify every release through `1.0.0` without remote repository mutation, while `REMOTE_INTEGRATION` activates authorized remote branch/PR/CI integration and `PUBLICATION` additionally activates tag/package/release publication obligations; acceptance evidence is default-local, explicit-remote-integration, explicit-publication, invalid-scope, and local-through-1.0 qualification fixtures.

`REQ-G00-053` — Any operation that mutates a remote repository, branch policy, pull request, remote ref, tag, package registry, release record, or other publication destination MUST require an explicit operator authorization bound to the bootstrap-invocation hash, canonical destination identity, operation scope, allowed action classes, and authorization validity window; absence or mismatch of that authorization MUST fail closed without remote mutation, ordinary coding-agent credentials MUST NOT supply or elevate it, and local build/qualification MUST remain available; acceptance evidence is no-authorization-local-success, unauthorized-push/tag/release refusal, wrong-destination refusal, expired-authorization refusal, bounded-action authorization, and trusted-layer authorized-operation tests.

`REQ-G00-054` — Every implementation run MUST have an effective authoring mode from `MANUAL`, `AUTONOMOUS`, or `HYBRID`; omission MUST resolve to `MANUAL` so the Source of Truth can be executed without a coding agent, `MANUAL` permits human or external-editor authored candidate changes, `AUTONOMOUS` permits coding-agent authored candidate changes without undeclared human source edits inside the task, and `HYBRID` permits both with explicit actor attribution; authoring mode MUST NOT change product requirements, public semantics, deterministic verifier meaning, release-gate quality thresholds, or operation-scope authorization; acceptance evidence is default-manual, explicit-autonomous, explicit-hybrid, invalid-mode, same-requirement-closure, and same-release-gate-threshold tests.

`REQ-G00-055` — Every candidate change MUST carry authoring provenance that identifies `MANUAL`, `AUTONOMOUS`, `HYBRID`, or deterministic generated-output origin, binds the base and candidate commit/tree identities, records actor class without requiring sensitive personal data, and records mode transitions; an `AUTONOMOUS` task that receives direct human source-code modification before candidate sealing MUST fail its autonomous provenance and can continue only after explicit restart/reclassification as `HYBRID`, while `MANUAL` and `HYBRID` candidates remain subject to the same deterministic verification and review gates; acceptance evidence is manual-candidate, autonomous-candidate, generated-output, hybrid-attribution, undeclared-human-edit autonomous refusal, explicit-hybrid-reclassification, and privacy-safe actor-provenance tests.

`REQ-G00-056` — The portable contract MUST remain executable in all three authoring modes without embedding Converge, a model provider, an IDE, a coding agent, an autonomous execution engine, or a human-only procedure into product semantics: manual authoring MUST NOT require agent work packets, a coding agent, model availability, model-based review, or autonomous orchestration; autonomous authoring MUST receive deterministic requirement context and bounded permissions through a conforming autonomous controller; hybrid authoring MUST preserve actor boundaries; independent review MUST remain satisfiable by one of the reviewer classes defined by `REQ-G00-057`; controller selection MUST follow `REQ-G00-058`; and equivalent accepted candidate trees under the same start/operation/release context MUST produce the same compliance and qualified product semantics regardless of authoring, reviewer, or controller mode; acceptance evidence is manual-no-agent-no-model-no-orchestrator path, autonomous-Converge path, alternative-autonomous-controller path, hybrid path, equivalent-tree compliance equality, reviewer/controller substitution, and tool-neutrality tests.

`REQ-G00-057` — Independent review MUST support reviewer class `HUMAN`, `MODEL`, `DETERMINISTIC_TOOL`, or `COMPOSITE`, with reviewer independence determined by candidate authorship/modification history and evidence identity rather than by class: a reviewer execution MUST NOT have authored or modified the candidate under review, a manual run MUST be able to satisfy required review without any model provider by using an independent human or deterministic review tool, an autonomous run can use an independent model/tool/human reviewer without permitting the authoring agent to self-approve, and a hybrid run MUST exclude every candidate-modifying actor from independent-review identity unless a separate non-authoring reviewer execution is used; acceptance evidence is manual-human-review, manual-deterministic-tool-review, autonomous-independent-model-review, autonomous-self-review refusal, hybrid-author-exclusion, composite-review, and no-model-manual-release tests.

`REQ-G00-058` — Execution-controller selection MUST be deterministic and orthogonal to product semantics: `MANUAL` MUST default to the portable `generic` profile after that profile exists and MUST use the embedded `MANUAL_BOOTSTRAP_V1` contract before it exists; `AUTONOMOUS` MUST use `AUTONOMOUS_BOOTSTRAP_V1` until the target repository, bootstrap readiness gate, external runtime configuration, pinned controller, and model-routing preflight are ready, then default to the `converge` profile whose controller baseline is pinned by `REQ-G00-059` and whose active model roles are governed by `REQ-G00-066` through `REQ-G00-069`; `HYBRID` MUST default to the portable `generic` profile after bootstrap and can bind Converge or another conforming agent bridge explicitly; any explicit `execution_adapter` override MUST declare supported authoring modes and pass portable adapter conformance before use, and changing controller/adapter or model routing MUST NOT weaken requirement closure, verifier semantics, evidence schemas, or release gates; acceptance evidence is manual-time-zero embedded-bootstrap, autonomous-time-zero embedded-bootstrap, manual-generic post-bootstrap, autonomous-pinned-Converge handoff, hybrid-generic post-bootstrap, explicit-autonomous-adapter, incompatible-adapter refusal, model-routing-equivalence, and cross-controller compliance-equality tests.

`REQ-G00-059` — The default autonomous-controller bootstrap baseline MUST identify `https://github.com/PeterPirog/converge-orchestrator` as the approved Converge origin, Git commit `1be97b75cf3b51f5ad0c2f212288f0a9edb3899b` as the immutable controller revision, and Git tree `d47b3c74b7b597dec503b4d3dca9db60e5488c93` as the expected source-tree identity; branch names, moving tags, repository default-branch state, or an unpinned `latest` checkout MUST NOT substitute for these identities, and a future baseline change MUST be an explicit Source of Truth contract evolution with adapter-conformance evidence before becoming the default; acceptance evidence is exact-origin/commit/tree validation, moving-main refusal, wrong-tree refusal, wrong-origin refusal, and explicit-baseline-evolution fixtures.

`REQ-G00-060` — Before the selected autonomous or hybrid controller is allowed to perform product implementation, a minimal pre-controller launcher MUST resolve and verify the effective adapter identity, provision or validate the controller under `REQ-G00-059` through `REQ-G00-061`, and when the target is not yet controller-runnable MUST execute only the bootstrap/control-plane work authorized by `AUTONOMOUS_BOOTSTRAP_V1`; this launcher can create or advance the target repository only to the exact B0/BR0 bootstrap seed permitted by the start-mode rules, can generate external controller runtime configuration and handoff evidence, and MUST NOT implement product features, make discretionary product-architecture decisions, weaken verification, or begin model-authored source mutation; acceptance evidence is matching-bound-tool, connected/offline controller provision, greenfield bootstrap-seed creation, brownfield readiness preparation, runtime-config generation, mismatched-controller refusal, launcher-product-feature-mutation refusal, and no-discretionary-architecture-decision fixtures.

`REQ-G00-061` — Connected controller provisioning MUST fetch only the approved repository/package origin and exact immutable revision into a dedicated canonicalized `tool_root`, verify the expected commit/tree or equivalent adapter content fingerprint before execution, and MUST NOT fall back to a moving branch/tag; offline controller provisioning MUST use a preseeded cache entry carrying the same immutable identity and MUST NOT silently access the network, while absence of both an approved connected path and matching offline cache MUST fail with `CONTROLLER_UNAVAILABLE`; acceptance evidence is exact-connected checkout, offline-cache replay, network-blocked offline mode, moving-ref refusal, tampered-cache refusal, and unavailable-controller tests.

`REQ-G00-062` — Controller handoff MUST preserve and revalidate the exact Source of Truth SHA-256, bootstrap-invocation logical hash, `PROJECT_HOME`, `REPO_ROOT`, start-state classification, authoring mode, operation scope, selected adapter identity/version, verified controller content identity, applicable B0/BR0 readiness identity, external controller-runtime-config logical hash, external Source-of-Truth write-protection evidence identity when model-authored execution is active, and effective model-routing snapshot identity; the receiving controller MUST refuse product mutation if any bound value, protection state, or clean target repository identity differs from the handoff, and once the canonical control plane exists the run MUST retain redacted controller-bootstrap/runtime-config/protection evidence and reproduce the controller acquisition and routing identities in the effective execution-profile snapshot; acceptance evidence is successful post-B0/BR0 handoff, changed-SOT refusal, writable-SOT refusal, changed-root refusal, changed-readiness refusal, changed-runtime-config refusal, changed-mode/scope refusal, changed-controller/routing refusal, canonical-evidence equality, and no-secret-retention tests.

`REQ-G00-063` — The frozen Source of Truth MUST contain the embedded machine-readable logical procedure `MANUAL_BOOTSTRAP_V1`, and when `authoring_mode=MANUAL` or a human-operated `HYBRID` bootstrap begins with no materialized generic profile or bootstrap script that embedded procedure MUST be the sole time-zero execution-control contract in addition to the ordinary normative requirements; it MUST require only the Source of Truth bytes, explicit bootstrap inputs, Windows filesystem operations, Git, hashing, and the supported Python standard-library environment, and MUST NOT depend on Converge, a coding agent, a model provider, a pre-existing repository script, or undocumented external instructions; acceptance evidence is SOT-only manual execution, missing-generic-profile, missing-bootstrap-script, no-model/no-agent/no-Converge, and undocumented-external-instruction refusal tests.

`REQ-G00-064` — The `MANUAL_BOOTSTRAP_V1` logical procedure MUST deterministically order these phases without allowing product-feature implementation before the bootstrap candidate exists: canonicalize and bind inputs; hash the Source of Truth; derive `REPO_ROOT`; inspect and classify target occupancy before mutation; establish the applicable GREENFIELD or BROWNFIELD bootstrap workspace under the existing start-state safety rules; materialize the exact Source of Truth bytes at the canonical repository path when mutation becomes permitted; create or update only bootstrap/control-plane candidate artifacts needed for B0/BR0; generate the portable generic execution profile and verifier-dispatch foundation; seal and verify the candidate tree; execute the applicable bootstrap preflight; create or advance the trusted local bootstrap commit according to the start mode; verify committed-tree equality and working-state safety; then evaluate B0 or BR0; acceptance evidence is phase-order tracing, pre-classification mutation refusal, premature-product-feature refusal, exact-SOT materialization, candidate-seal, preflight-before-commit, commit/tree equality, and B0/BR0 transition tests.

`REQ-G00-065` — After B0 or BR0 succeeds, normal `MANUAL` execution MUST transition from the embedded time-zero procedure to the committed `execution-profiles/generic.json` plus canonical requirement graph, verification manifest, schemas, and repository tooling, and the embedded procedure MUST remain a reconstruction/reference contract rather than a hidden second implementation path; a clean repository produced by either manual or autonomous bootstrap MUST expose equivalent generic-profile semantics and MUST allow later manual continuation without Converge; acceptance evidence is embedded-to-generic handoff, manual-bootstrap repository continuation, autonomous-bootstrap-to-manual continuation, generic-profile semantic equality, embedded/post-bootstrap divergence refusal, and no-Converge post-bootstrap manual execution tests.

`REQ-G00-066` — The frozen Source of Truth MUST define the logical autonomous model-role contract `AUTONOMOUS_MODEL_ROLE_CONTRACT_V1` with role classes `SCOUT`, `PLANNER`, `BUILDER`, `CORRECTNESS_REVIEWER`, `ARCHITECTURE_REVIEWER`, and `SECURITY_REVIEWER`, while exact provider/model identifiers remain execution-profile data rather than product semantics; every active autonomous controller MUST map each active logical role to exactly one primary model route plus an optional finite ordered fallback list, preserve Builder-as-writer and reviewer independence boundaries, and expose declared context/output budgets and provider/tool execution capabilities for preflight; acceptance evidence is complete-role-map, missing-role, duplicate-primary, finite-fallback, builder-boundary, reviewer-independence, and alternative-controller role-equivalence tests.

`REQ-G00-067` — Before the first model call of an `AUTONOMOUS` run or model-assisted `HYBRID` run, the controller MUST materialize an immutable effective model-routing snapshot from an explicit operator binding or selected adapter configuration, recording exact provider/model identifiers, provider or gateway identity, declared context/output token limits, role mapping, ordered fallbacks, retry policy, request-option hash, and secret-variable names without secret values; model discovery can be used only to validate explicitly ordered candidates and MUST NOT rank or silently choose an unspecified 'best available' model, moving aliases such as `latest` can be retained only when the gateway exposes no immutable model revision but the exact alias plus observed catalog identity is frozen in the run snapshot, and any unresolved role MUST remain non-runnable; acceptance evidence is explicit-routing snapshot, adapter-config routing, discovery-validation-only, unspecified-model refusal, ordered-fallback preservation, moving-alias snapshot, secret-redaction, and routing-hash fixtures.

`REQ-G00-068` — An `AUTONOMOUS_MODEL_PREFLIGHT` MUST pass before any model-authored product mutation: it MUST verify that every active logical role resolves through the selected provider/gateway, the effective route exposes sufficient declared context/output budget for the controller's non-truncatable authoritative inputs and configured reserves, the Builder route can execute the controller's required tool loop, reviewer routes satisfy independence constraints, all explicit fallbacks are resolvable in their declared order, and referenced credentials are available without being persisted; an absent gateway/catalog/credential or incomplete/insufficient role route MUST fail with typed `MODEL_ROUTING_UNAVAILABLE` or `MODEL_CAPABILITY_UNAVAILABLE` evidence without changing `GREENFIELD`, `BROWNFIELD`, or `AMBIGUOUS` classification and without blocking a valid `MANUAL` path; acceptance evidence is all-roles-ready, missing-gateway, missing-model, insufficient-context, missing-credential, builder-tool-loop failure, reviewer-independence failure, fallback-resolution failure, and manual-path-unaffected tests.

`REQ-G00-069` — The effective autonomous model-routing snapshot MUST remain immutable for the model-derived portion of a run: provider retry and fallback can occur only according to the snapshot's finite ordered policy, a model/provider/context/fallback/request-option change outside that policy MUST create a new routing snapshot and invalidate dependent authoring/planning/review evidence before further autonomous progress, deterministic verifier evidence bound solely to unchanged code/artifact inputs MUST NOT be downgraded merely because a model route changed, and release/qualification provenance MUST identify the routing snapshot used for model-derived work without treating a specific model vendor as product semantics; acceptance evidence is declared-retry, declared-fallback, undeclared-substitution refusal, mid-run-routing-change invalidation, unchanged-deterministic-evidence preservation, and vendor-neutral qualification-provenance tests.

`REQ-G00-070` — The frozen Source of Truth MUST contain the embedded logical procedure `AUTONOMOUS_BOOTSTRAP_V1` for `AUTONOMOUS` time-zero execution before repository-local profiles or an external controller runtime configuration exist; the procedure MUST consume only the frozen Source of Truth, explicit bootstrap inputs, Windows filesystem/Git/Python bootstrap capabilities, selected immutable controller identity, and an explicit or adapter-supplied model-routing binding, and it MUST separate deterministic bootstrap/control-plane preparation from later model-authored product implementation; acceptance evidence is SOT-only autonomous time-zero invocation, absent-target-repository, absent-runtime-config, absent-controller-before-provision, explicit-routing-binding, and premature-model-authored-product-mutation refusal tests.

`REQ-G00-071` — For a `GREENFIELD` autonomous start, `AUTONOMOUS_BOOTSTRAP_V1` MUST deterministically create or initialize `REPO_ROOT` on canonical `main`, materialize the exact frozen Source of Truth and the same portable bootstrap/control-plane candidate semantics required by the manual path, seal and verify the candidate, execute `BOOTSTRAP_PREFLIGHT`, create the trusted bootstrap seed commit, verify committed-tree equality and clean working state, and pass B0 before controller product work begins; for `BROWNFIELD`, it MUST preserve the pre-mutation capture ordering in `REQ-G00-042`, materialize only authorized control-plane/bootstrap additions, retain the baseline evidence, and pass BR0 before controller product work begins; acceptance evidence is greenfield absent-repo-to-B0 seed, greenfield empty-Git-to-B0 seed, brownfield preflight-before-mutation, brownfield BR0 seed, manual/autonomous bootstrap-control-plane equivalence, product-feature-free seed diff, and readiness-before-controller-work tests.

`REQ-G00-072` — After the autonomous bootstrap seed is ready and before controller launch, `AUTONOMOUS_BOOTSTRAP_V1` MUST generate a redacted external runtime configuration outside `REPO_ROOT` whose logical content is deterministically derived from the bootstrap invocation, frozen Source of Truth, selected adapter, operation scope, target repository identity, readiness identity, effective model-routing snapshot, and Source-of-Truth write-protection policy; for the pinned Converge adapter the configuration MUST bind `project.repo_path` to canonical `REPO_ROOT`, `project.requirements_path` to the external frozen Source of Truth, `project.require_spec_read_only` to `true`, controller state/worktree directories outside `REPO_ROOT`, `github.repo` as disabled for `LOCAL_QUALIFICATION` and as the canonical authorized remote only for remote scopes, `github.base_branch` to the effective target branch, model profiles/agent roles to the frozen routing snapshot, and quality/verifier commands to the canonical bootstrap control plane, while secret values remain environment-only; acceptance evidence is local-qualification config, remote-scope config, external-requirements-path, require-spec-read-only true, external-state/worktree paths, exact-repo/base binding, routing-to-agent mapping, quality/verifier binding, secret-redaction, and config-hash reproducibility tests.

`REQ-G00-073` — The autonomous controller MUST start only after the bootstrap seed repository is clean and B0/BR0-qualified, the external runtime configuration is schema-valid and hash-bound, controller acquisition identity is verified, the external frozen Source of Truth satisfies `REQ-G00-074`, and `AUTONOMOUS_MODEL_PREFLIGHT` passes; the pre-controller launcher MUST run the adapter's deterministic configuration/environment preflight when available, classify failures as `CONTROLLER_CONFIG_UNAVAILABLE`, `CONTROLLER_ENVIRONMENT_UNAVAILABLE`, `SPEC_WRITE_PROTECTION_UNAVAILABLE`, `MODEL_ROUTING_UNAVAILABLE`, or `MODEL_CAPABILITY_UNAVAILABLE` without silently switching authoring mode, and hand off only the immutable seed/config/protection/routing identities defined by `REQ-G00-062`; acceptance evidence is successful Converge-ready handoff, missing-runtime-config, invalid-repo-path, non-Git-target refusal, dirty-seed refusal, writable-external-SOT refusal, failed-controller-doctor/environment preflight, failed-model-preflight, no-silent-manual-fallback, and exact-handoff tests.

`REQ-G00-074` — Before any model-authored `AUTONOMOUS` execution or model-assisted `HYBRID` execution receives the frozen external Source of Truth, the bootstrap/trusted controller layer MUST establish and verify an operating-system write-protection boundary that denies the model-authored execution identity permission to modify, replace, rename, delete, or permission-relax the bound Source-of-Truth file while preserving readability and the exact pre-protection SHA-256; on Windows the protection can be satisfied by an NTFS ACL or an equivalently enforceable OS boundary rather than the weak DOS ReadOnly attribute alone, the protection MUST remain effective for the full model-authored execution interval, and removal or weakening of the boundary MUST invalidate dependent autonomous evidence before further model-authored work; this requirement MUST NOT make OS-level write protection a prerequisite for a valid model-free `MANUAL` path; acceptance evidence is Windows-ACL protected read, write/replace/rename/delete refusal from model execution identity, unchanged-SOT hash, protection-relax refusal, mid-run-protection-loss invalidation, alternative-equivalent-OS-boundary, and manual-path-unaffected tests.

## Bootstrap Gate B0 — Repository foundation

`REQ-B00-001` — Bootstrap Gate `B0` MUST pass before Phase 0 product work on a greenfield repository and MUST prove declared `PROJECT_HOME`/`REPO_ROOT` topology, canonical repository layout, package build/install, portable contract artifacts, verifier-dispatch capability, Windows CI scaffolding, truthful empty capability state, no runtime dependency download, and integration-layer readiness; for an initially commitless greenfield repository the bootstrap process MUST first emit `BOOTSTRAP_PREFLIGHT` evidence bound to the candidate Git-tree identity and final B0 evidence MUST then bind the exact first-commit identity whose tree equals that preflighted tree; acceptance evidence is machine-readable preflight/final gate reports bound to Source of Truth SHA, effective execution-profile/root-topology hash, candidate/committed tree identity, repository commit identity when available, and package artifact hashes.

`REQ-B00-002` — Bootstrap Gate `B0` MUST derive its exact greenfield closure solely from the canonical requirement graph by selecting every requirement whose lifecycle is `BOOTSTRAP` and whose structured applicability expression evaluates true for `start_mode=GREENFIELD`, plus all transitive prerequisites, and MUST NOT maintain a second manually enumerated bootstrap requirement list; actual execution of the first-public-release scenario defined by `REQ-G00-015` remains a release-lifecycle action rather than a B0 action; acceptance evidence is graph-derived closure equality, newly added bootstrap-requirement auto-inclusion, greenfield applicability filtering, transitive-prerequisite inclusion, and no-manual-list-drift tests.

`REQ-B00-003` — Brownfield Readiness Gate `BR0` MUST derive its exact closure solely from the canonical requirement graph by selecting every requirement whose lifecycle is `BOOTSTRAP` and whose structured applicability expression evaluates true for `start_mode=BROWNFIELD`, plus all transitive prerequisites, and MUST prove in order: declared `PROJECT_HOME`/`REPO_ROOT` topology and canonical repository identity/ref, immutable pre-mutation `BROWNFIELD_PREFLIGHT`, isolated candidate construction, retained brownfield baseline, canonical in-repository Source of Truth/control-plane candidate, canonical brownfield dependency lock, `BROWNFIELD_BOOTSTRAP_PREFLIGHT`, trusted bootstrap commit/fast-forward materialization, clean final working tree, compatibility-preservation obligations, and transitional-dependency obligations, without requiring greenfield-only source-tree creation; acceptance evidence is a machine-readable BR0 report, graph-derived closure equality, preflight-before-candidate ordering, candidate-before-commit ordering, bootstrap-commit binding, clean-final-tree validation, retained-baseline equality, canonical-control-plane presence, dependency-lock state, mandatory inclusion of `REQ-P00-020`, `REQ-P00-021`, and `REQ-P00-022`, and greenfield-only exclusion tests.

`REQ-B00-004` — Bootstrap Gate `B0` and Brownfield Readiness Gate `BR0` MUST run a deterministic contract-self-consistency verifier that proves every named requirement ID exists, every range expands deterministically, every prerequisite is satisfiable, every lifecycle class is valid, every structured applicability expression is schema-valid and evaluable, no dependency cycle exists, no earlier gate depends on a later release milestone, each readiness closure exactly equals the graph-derived lifecycle/applicability closure for its start mode, and every release-qualification closure includes all transitive prerequisites; acceptance evidence is deliberate missing-ID, malformed-range, lifecycle, applicability, cycle, future-release-dependency, stale-manual-closure, readiness-closure-mismatch, and omitted-transitive-prerequisite fixtures.

## Phase 0 — Domain lock, Windows-only platform and external baselines

`REQ-P00-001` — The product MUST target Microsoft Visual FoxPro 9.0 Service Pack 2 exclusively, use the dialect identifier `microsoft.visual-foxpro.9.0.sp2`, and treat syntax, object models, file semantics, compiler behavior, and runtime behavior from older FoxPro or Visual FoxPro releases as unsupported unless the same element is explicitly documented by the pinned VFP9 SP2 corpus; acceptance evidence is a dialect gate, negative fixtures for older-version assumptions, and runtime/version reporting.

`REQ-P00-002` — The production server MUST support Windows only and all packaging, path handling, process control, COM automation, filesystem safety, test matrices, and operator documentation MUST be designed for Windows semantics rather than cross-platform compatibility; acceptance evidence is Windows-only package metadata/documentation and CI without Linux/macOS product claims.

`REQ-P00-003` — The full-capability production profile MUST assume a locally installed Microsoft Visual FoxPro 9 SP2 environment, while pure inspection MUST remain available when VFP is unavailable for diagnostics, offline triage, and CI; acceptance evidence is separate capability snapshots for no-VFP and VFP9 SP2 hosts with no schema drift.

`REQ-P00-004` — The authoritative documentation corpus MUST be the VFPX `VFPX/HelpFile` VFP 9 SP2 Help File version 1.08 pinned to commit `b911ff18b06f421ece242c1d4dfa9fb140864a4a`, and no separate FoxPro 2.x or Visual FoxPro 3–8 manual corpus MUST participate in language, form, object, data, or refactoring decisions; acceptance evidence is a provenance manifest and a corpus-origin test rejecting non-VFP9SP2 knowledge roots.

`REQ-P00-005` — Help topics inside the pinned VFP9 SP2 corpus that describe backward-compatible language elements MUST remain tagged as VFP9-SP2-documented compatibility knowledge and MUST not be promoted to preferred refactoring output unless the analyzed source itself depends on that element; acceptance evidence is topic classification tests and a refactoring fixture that preserves legacy syntax only when required by source behavior.

`REQ-P00-006` — The FoxBin2Prg integration baseline MUST be upstream `fdbozzo/foxbin2prg` version 1.21.05 pinned to commit `32715d06b84753401b7262c3cc48bde758ee3c8d`, and any future pin change MUST require explicit dependency-boundary/conformance evidence before replacing this architecture baseline; the baseline declaration itself MUST NOT require FoxBin2Prg execution before the first release whose canonical milestone includes the FoxBin adapter; acceptance evidence is origin/version/commit/acquisition-manifest validation plus a future-baseline-change negative control, while executable bidirectional conversion evidence is owned by Phase 6.

`REQ-P00-007` — The DBF/FPT engine MUST use the public `dbfbridge` 1.x API with compatibility `dbfbridge>=1.1.1,<2`, MUST use version `1.1.1` as the initial architecture baseline for this Source of Truth revision, and fresh DBF/FPT creation paths MUST use `dbfbridge[write]` rather than a private copied DBF parser/writer; a later tested baseline change MUST pass dependency-boundary conformance before adoption while the compatibility range remains a separate policy; acceptance evidence is module-origin, baseline-version, Direct Read/Direct Write consumer, and approved-baseline-change tests.

`REQ-P00-008` — The privacy engine MUST integrate the public clean-slate `dbf_anonymizer` 1.x boundary using compatibility `dbf-anonymizer>=1.0.0.dev0,<2`, MUST use version `1.0.0.dev0` at architecture baseline commit `02763d7c34b19335e560ef9597a54aed7790968d` for this Source of Truth revision, and MUST not copy pseudonymization, recovery-vault, transformation, verification, or bundle internals into this repository; adoption of a later stable or development baseline MUST be an explicit dependency-boundary change with conformance evidence rather than an automatic consequence of upstream publication; acceptance evidence is origin/version/commit checks, import-boundary tests, public-consumer contract tests, and approved-baseline-change tests.

`REQ-P00-009` — The runtime MUST perform no package installation, Git clone, web scraping, or dependency download while serving MCP requests, and a complete deployment MUST be installable from a pinned Windows wheelhouse plus locally pinned FoxBin2Prg, VFPX HelpFile corpus, and configured VFP9 SP2 assets; acceptance evidence is an outbound-network-blocked installation and end-to-end run.

`REQ-P00-010` — The server MUST analyze both original and anonymized VFP datasets as first-class inputs and MUST preserve an explicit dataset role and lineage so results never silently mix original values with pseudonymized values; acceptance evidence is parallel original/anonymized session fixtures and lineage assertions.

`REQ-P00-011` — The supported Python runtime MUST be `>=3.10,<3.15`, matching the current public compatibility intersection of dbfbridge and DBF_Anonymizer and remaining compatible with the official MCP v2 SDK; acceptance evidence is package metadata plus clean-environment tests on Python 3.10, 3.11, 3.12, 3.13, and 3.14.

`REQ-P00-012` — Published releases MUST record exact tested identities for VFP9 SP2, FoxBin2Prg, VFPX HelpFile, dbfbridge, DBF_Anonymizer, MCP protocol revision, MCP SDK, MCP conformance referee/requirement set, Psycopg, PostgreSQL, and psqlODBC components that participate in that release profile, while compatible version ranges remain separate from tested baselines; acceptance evidence is a machine-readable compatibility manifest generated in release CI.

`REQ-P00-013` — Every executable Source of Truth requirement MUST be written in English, occupy one physical Markdown line, carry one explicit stable requirement ID, state a concrete product or delivery obligation without relying on hidden conversation context, and include deterministic acceptance evidence on that line; acceptance evidence is a portable contract-lint test plus an English-only requirement lexical guard.

`REQ-P00-014` — After this revision is frozen for an autonomous run, existing requirement IDs and their normative meanings MUST remain stable across later Source of Truth revisions, and any intentional retirement, replacement, or weakening MUST be represented by an explicit version-controlled contract-evolution record identifying the old ID, disposition, replacement ID where applicable, rationale, and first affected release; acceptance evidence is a previous-versus-current contract diff test that fails on silent removal, ID reuse, or semantic replacement.

`REQ-P00-015` — Every qualified release MUST record the exact immutable Source of Truth SHA-256, compiled or enumerated requirement-ID set hash, execution-profile snapshot hash, clean target Git commit/tree, verification-manifest hash, dependency-lock hash, qualified-release-record identity, and qualification-evidence root so a later audit can reconstruct the release contract independently of chat history or the implementation tool used; later public publication MUST bind the immutable provenance bundle to the same qualified identities rather than replace them; acceptance evidence is local qualification provenance validation, published qualification-binding, and offline reconstruction of the qualified release contract.

`REQ-P00-016` — The target repository MUST maintain a machine-readable compatibility manifest that separates supported version ranges from exact tested release baselines for Python, VFP9 SP2, FoxBin2Prg, VFPX HelpFile, dbfbridge, DBF_Anonymizer, MCP protocol revision, MCP SDK, MCP conformance referee/requirement set, Psycopg, PostgreSQL, and psqlODBC; acceptance evidence is schema validation plus protocol/conformance/dependency-origin/version discovery tests.

`REQ-P00-017` — Windows runtime capability discovery MUST record process architecture, Python architecture, VFP executable path/build, COM registration identity where used, ODBC driver architecture/version where used, filesystem capabilities relevant to junction/reparse handling, and available local dependency origins without assuming that presence implies compatibility; acceptance evidence is 32-bit/64-bit process and driver fixtures, missing-registration fixtures, and trusted-host discovery snapshots.

`REQ-P00-018` — Product runtime compatibility, product CI acceptance, release qualification, installation documentation, troubleshooting, and support claims MUST target Windows only, and non-Windows behavior if incidentally possible MUST remain unsupported and MUST NOT consume product test-matrix or release-gate scope; acceptance evidence is Windows-only CI/release manifests, package metadata, documentation checks, and absence of non-Windows product-support claims.

`REQ-PORT-001` — The Source of Truth MUST remain implementation-tool-neutral: product requirements, acceptance criteria, architecture boundaries, release gates, and safety constraints MUST be understandable and executable without requiring knowledge of Converge, Codex, OpenCode, Claude Code, or any other specific coding agent; acceptance evidence is a terminology lint plus independent review using a tool-neutral requirement parser.

`REQ-PORT-002` — Every mandatory requirement MUST be self-contained enough for an independent coding tool to identify the affected capability, required behavior, prohibited behavior where relevant, and deterministic acceptance evidence without consulting prior chat messages, hidden memory, private prompts, or unstated operator conventions; acceptance evidence is a requirement-completeness review over the full contract.

`REQ-PORT-003` — Tool-specific execution bindings such as verifier command syntax, agent names, model routing, sandbox implementation, worktree strategy, CI provider details, or orchestrator configuration keys MUST live in external execution-profile files or generated manifests rather than being required to understand the product semantics in this Source of Truth; acceptance evidence is a source scan proving that mandatory product semantics do not depend on tool-specific configuration keys.

`REQ-PORT-004` — The repository MUST expose a machine-readable portable verification manifest whose logical fields include requirement ID, verifier identity, command or test selector, evidence class, required capabilities, release-gate membership, and expected PASS/FAIL semantics, and execution adapters MUST translate that manifest into tool-specific configuration without changing its logical meaning; acceptance evidence is schema validation plus equivalent adapter output for at least the default Converge profile and one generic direct-test profile.

`REQ-PORT-005` — The Source of Truth MUST use stable domain terminology defined by the document itself for project, dataset, artifact, evidence, capability, release gate, refactor workspace, relational target model, migration, and validation concepts, and tool-specific synonyms MUST NOT alter those meanings; acceptance evidence is glossary-reference validation and schema vocabulary tests.

`REQ-PORT-006` — An implementation tool MUST be permitted to choose internal algorithms, task decomposition, file organization within declared architecture boundaries, and coding strategy unless a mandatory requirement constrains them, while observable contracts, safety properties, evidence semantics, release gates, and compatibility behavior MUST remain invariant; acceptance evidence is two implementation-plan fixtures that use different task decomposition but satisfy the same requirement set.

`REQ-PORT-007` — A requirement MUST NOT be considered satisfied solely because an agent, model, reviewer, or orchestrator states that it is complete; satisfaction MUST derive from deterministic verifier evidence and required review or release-gate artifacts defined by the portable verification contract; acceptance evidence is a false-positive completion scenario rejected despite a model-generated PASS statement.

`REQ-PORT-008` — The repository MUST provide both a portable `generic` execution profile and a Converge execution profile after bootstrap, with effective post-bootstrap default selection derived from `authoring_mode` by `REQ-G00-058`; before repository-local profiles exist, manual/human-operated hybrid bootstrap MUST use `MANUAL_BOOTSTRAP_V1` and autonomous bootstrap MUST use `AUTONOMOUS_BOOTSTRAP_V1`; the materialized generic profile MUST support complete `MANUAL` and `HYBRID` execution without requiring Converge, the Converge profile MUST support `AUTONOMOUS` and optionally `HYBRID` execution, reproduce the immutable default controller baseline from `REQ-G00-059`, express model roles compatible with `AUTONOMOUS_MODEL_ROLE_CONTRACT_V1`, and be reproducibly projectable into the external controller runtime configuration required by `REQ-G00-072`; alternative adapters MUST preserve requirement IDs, verifier semantics, evidence classes, lifecycle/applicability evaluation, release-gate closure, autonomous bootstrap readiness, and model-role semantics; acceptance evidence is SOT-only-manual-bootstrap, SOT-only-autonomous-bootstrap, generic-manual post-bootstrap, pinned-Converge-autonomous external-config projection, Converge-hybrid, alternative-adapter conformance, and cross-profile closure/evidence equality tests.

`REQ-P00-019` — The Source of Truth MUST have normative precedence over existing repository README files, architecture notes, capability matrices, generated manifests, prompts, agent instructions, implementation code, and historical tests whenever they conflict, while pinned upstream VFP9 SP2, FoxBin2Prg, dbfbridge, DBF_Anonymizer, MCP, Psycopg, PostgreSQL, and psqlODBC sources remain authoritative only for the external semantics assigned to them by this contract; acceptance evidence is conflict fixtures proving that stale repository text cannot override a Source of Truth requirement and that external-source evidence cannot silently redefine product policy.

`REQ-P00-020` — When the start state is `BROWNFIELD`, the first implementation run MUST derive its machine-readable brownfield baseline from the immutable `BROWNFIELD_PREFLIGHT` captured before target-repository mutation, bind that baseline to the exact starting Git HEAD/tree and clean working-tree/content inventory, inventory existing public Python APIs, CLI commands, coding-agent tools, configuration formats, result/error schemas, tests, vendored dependencies, documentation claims, and known implemented capabilities, and retain the validated baseline at `evidence/brownfield/start-baseline.json` without rewriting its captured facts; acceptance evidence is preflight-to-retained-baseline hash equality, changed-starting-commit mismatch, changed-content-inventory mismatch, public-surface inventory, and greenfield `NOT_APPLICABLE` proof.

`REQ-P00-021` — When the start state is `BROWNFIELD`, autonomous or agent-assisted development MUST evolve the existing repository in place rather than perform an unreviewed clean-slate rewrite, and removal or replacement of an already working public behavior MUST have an explicit Source of Truth mapping, compatibility/deprecation decision, migration test, and preserved evidence before the old implementation disappears; acceptance evidence is a deliberate working-interface removal fixture that is rejected without a mapped replacement plus a greenfield non-applicability fixture.

`REQ-P00-022` — When the start state is `BROWNFIELD`, legacy vendored or locally copied dependency integrations that differ from the pinned target public APIs MUST be treated as transitional state, MUST be isolated behind adapters during migration, and MUST be removed only after public-API parity and offline-deployment tests prove that the replacement preserves or intentionally supersedes the prior supported behavior; acceptance evidence is legacy-adapter parity, origin, removal-gate, and greenfield non-applicability tests.

`REQ-P00-023` — Third-party source, binaries, generated corpora, and redistributed package artifacts MUST preserve upstream license texts, attribution, source/commit provenance, local-modification records, and redistribution notices applicable to FoxBin2Prg, VFPX HelpFile, dbfbridge, DBF_Anonymizer, MCP SDK, Psycopg, PostgreSQL client components, and any later dependency; acceptance evidence is release-asset license inventory validation and a missing-license negative fixture.

`REQ-P00-024` — Every qualified release MUST be built and tested from an immutable dependency lock or equivalent fully resolved dependency set that records exact direct/transitive versions and artifact integrity identities separately from broader compatibility ranges, and an unrecorded dependency resolution change MUST invalidate qualification evidence; later publication MUST use the same qualified lock identity; acceptance evidence is locked-build, changed-transitive-dependency, lock/source mismatch, and publication-lock-identity tests.

`REQ-P00-025` — Microsoft Visual FoxPro executables, runtime files, licensed development components, and other proprietary Microsoft assets MUST NOT be vendored into public source or release artifacts unless explicit redistribution rights and provenance are recorded for that exact asset, and normal full-capability operation MUST discover or use operator-provided local VFP9 SP2 assets instead; acceptance evidence is release-asset scanning, configured-local-runtime, and unauthorized-vendoring negative fixtures.

`REQ-P00-026` — Each qualified release profile MUST declare the exact Windows editions/builds and process architectures used for qualification, distinguish `TESTED`, `COMPATIBLE_UNVERIFIED`, and `UNSUPPORTED` host claims, and MUST NOT generalize a successful test on one Windows build or architecture to all Windows versions; later publication MUST expose the same support matrix identity; acceptance evidence is qualification support-matrix validation, publication-matrix identity, and false-generalization tests.

`REQ-P00-027` — The compatibility manifest MUST declare the initial PostgreSQL modernization baselines for this Source of Truth revision as Psycopg `3.3.6`, PostgreSQL server `18.6` within production-major compatibility `18.x`, and 32-bit Windows psqlODBC `REL-18_00_0002` for the VFP transition profile, while later baseline changes require dependency-boundary/trusted-host conformance before adoption; this declaration MUST NOT require installing or connecting to PostgreSQL, Psycopg, or psqlODBC before the canonical milestone that first claims the corresponding capability; acceptance evidence is manifest/schema baseline identity, wrong-baseline refusal, and approved-baseline-evolution tests, with live-server/client/ODBC evidence owned by Phases 13, 15, and 16.

`REQ-PORT-009` — The repository MUST expose a machine-readable requirement graph derived from the Source of Truth that records each requirement ID, phase, explicit prerequisite IDs or prerequisite phase, release-gate membership, and status vocabulary without changing the requirement text; acceptance evidence is graph-schema validation, exact-ID-set equality with the Markdown contract, and deterministic regeneration.

`REQ-PORT-010` — The requirement graph MUST be acyclic, release-gate prerequisite closure MUST be computable without inferring intent from Markdown section order, and an implementation tool MUST NOT mark a requirement PASS while any explicit mandatory prerequisite remains non-PASS unless the requirement is declared independent by the graph; acceptance evidence is cycle, missing-prerequisite, out-of-order, and independent-requirement fixtures.

`REQ-PORT-011` — The portable requirement graph and portable verification manifest MUST remain logically tool-neutral derived artifacts and MUST be hash-bound to the exact Source of Truth version so Converge, Codex, OpenCode, or another runner cannot execute a stale dependency or verifier map against a newer contract; acceptance evidence is cross-hash mismatch and stale-manifest refusal tests.

`REQ-PORT-012` — Execution adapters MUST support a repository with no prior commit by providing or invoking a deterministic bootstrap integration step that establishes the repository foundation required by the tool, and an adapter that cannot handle this state MUST report `BOOTSTRAP_REQUIRED` before ordinary implementation rather than silently assuming a pre-existing base commit; acceptance evidence is no-commit Converge-profile, generic-profile, and unsupported-adapter fixtures.

`REQ-PORT-013` — The default Converge execution profile MUST include a greenfield bootstrap path that reaches a valid base commit and portable verifier-dispatch foundation before normal requirement convergence, while alternative coding tools can implement the same portable bootstrap semantics through different mechanics; acceptance evidence is Converge greenfield bootstrap conformance and generic-adapter equivalence tests.

`REQ-PORT-014` — The portable requirement graph MUST assign every mandatory requirement exactly one primary lifecycle class from `BOOTSTRAP`, `IMPLEMENTATION`, `MERGE_GUARD`, `RELEASE_GUARD`, `DEPLOYMENT_GUARD`, or `FINAL_ACCEPTANCE` according to the canonical lifecycle mapping in this Source of Truth, plus one structured applicability expression according to `REQ-PORT-025` and prerequisite IDs or logical milestones, and every selector used to derive those assignments MUST satisfy `REQ-PORT-024`; acceptance evidence is lifecycle completeness, single-primary-class, selector validation, canonical-map equality, applicability equality, and no-heading/no-prose-inference tests.

`REQ-PORT-015` — The generated requirement graph MUST implement the canonical applicability, lifecycle, milestone, readiness, and release-closure maps defined in the Source of Truth, including graph-derived `GREENFIELD_READY=B0`, `BROWNFIELD_READY=BR0`, split `P01_CORE` and `P01_MCP_MIN` milestones, cross-cutting governance activation, and cumulative release closures, with exact set equality after selector expansion; acceptance evidence is deterministic graph regeneration plus exact applicability/readiness/milestone/release-closure snapshots.

`REQ-PORT-016` — A requirement in `RELEASE_GUARD`, `DEPLOYMENT_GUARD`, or `FINAL_ACCEPTANCE` lifecycle MUST NOT block unrelated earlier implementation solely because its future lifecycle event or structured applicability predicate is not active, while it MUST become blocking when its declared lifecycle event and applicability expression evaluate active; acceptance evidence is future-release-nonblocking, activated-release-blocking, deployment-only, private-profile, artifact-profile, and final-acceptance activation fixtures.

`REQ-PORT-017` — Every hash-bound JSON contract artifact, including requirement graphs, verification manifests, compatibility manifests, release-gate manifests, evidence indexes, capability snapshots, and provenance records, MUST define a canonical logical serialization using RFC 8785 JSON Canonicalization Scheme or a documented byte-equivalent canonical JSON profile, while human-oriented YAML or Markdown renderings MUST derive from the same logical model and MUST NOT be the authoritative hash input; acceptance evidence is cross-tool canonical-byte, key-order, whitespace, Unicode, number-encoding, and YAML-render-equivalence tests.

`REQ-PORT-018` — Every generated portable contract artifact MUST carry its schema version, Source of Truth SHA-256, generator identity/version, canonical logical-content hash, and generation timestamp as non-authoritative metadata where timestamp inclusion would otherwise disturb the logical hash, and consumers MUST reject schema/SOT/content-hash mismatches rather than silently reinterpret stale artifacts; acceptance evidence is deterministic regeneration, stale-SOT, wrong-schema, tampered-content, and timestamp-independence tests.

`REQ-PORT-019` — The contract-self-consistency verifier MUST validate the canonical execution contract against the generated requirement graph and release-gate manifests on every Source of Truth revision so descriptive milestone/release declarations, executable requirement dependencies, and generated closures cannot drift independently; acceptance evidence is a deliberately edited milestone, release closure, and lifecycle mapping that each fail validation.

`REQ-PORT-020` — The contract-self-consistency verifier MUST derive and validate the document meta-contract from the executable requirement set, including mandatory/recommended/auto-hash counts, first and last executable IDs, revision identifier, every named requirement/range, every lifecycle-map entry, every milestone, every release-closure declaration, and every gate reference, and any stale or contradictory meta declaration MUST fail before implementation work begins; acceptance evidence is stale-count, stale-first-ID, stale-last-ID, stale-revision, missing-range, lifecycle-drift, milestone-drift, and release-closure-drift fixtures.

`REQ-PORT-021` — Lifecycle assignment MUST follow the canonical lifecycle mapping declared in the Source of Truth rather than being inferred from natural-language wording, Markdown heading position, model judgment, or implementation-tool heuristics, and the generated requirement graph MUST contain exactly the same lifecycle class and activation rule for every requirement ID; acceptance evidence is full-ID lifecycle coverage, cross-tool graph equality, and deliberately altered-class/activation fixtures.

`REQ-PORT-022` — Portable contract schemas for requirement graphs, verification manifests, compatibility manifests, release-gate manifests, evidence indexes, capability snapshots, provenance records, and execution-profile bindings MUST use JSON Schema 2020-12, MUST declare stable offline-resolvable schema identities, MUST use only local or bundled `$ref` targets during validation, and MUST reject network dereferencing; acceptance evidence is dialect validation, stable-schema-identity, bundled-reference, missing-reference, and external-reference-blocking tests.

`REQ-PORT-023` — Every requirement-graph node MUST carry a structured applicability expression from a versioned closed vocabulary covering start mode, lifecycle event, release profile, operation scope, authoring mode, host capability profile, detected project/artifact capability, and private-deployment qualification, with `ALWAYS` as the default, and applicability expressions MUST support deterministic membership in `LOCAL_QUALIFICATION|REMOTE_INTEGRATION|PUBLICATION` and `MANUAL|AUTONOMOUS|HYBRID`; gate closure MUST evaluate these expressions mechanically rather than infer applicability from prose; acceptance evidence is default-ALWAYS, greenfield/brownfield, release-profile, operation-scope membership, authoring-mode membership, host-capability, artifact-capability, private-profile, unknown-predicate, and cross-tool applicability-equality tests.

`REQ-PORT-024` — Canonical requirement selectors MUST use only three machine-parseable forms: one exact requirement ID, one inclusive numeric range whose two endpoints share the same requirement-family prefix, or one family wildcard of the form `REQ-FAMILY-*` matching only explicit three-digit IDs in that family; cross-family numeric ranges, open-ended numeric ranges, prose selectors such as `every remaining`, and inference from Markdown order MUST be rejected; acceptance evidence is exact-ID, same-family-range, wildcard, cross-family-range-refusal, open-range-refusal, prose-selector-refusal, and deterministic-expansion tests.

`REQ-PORT-025` — Structured applicability assignment MUST follow the canonical applicability mapping declared in this Source of Truth, every mandatory requirement MUST resolve to exactly one applicability expression after ordered overrides and the default `ALWAYS`, and implementation tools MUST NOT infer start-mode, release-profile, operation-scope, authoring-mode, deployment-profile, or comparison applicability from requirement prose; acceptance evidence is full-ID applicability coverage, no-overlap/no-unresolved predicates, greenfield/brownfield closure equality, release-family activation, local/remote/publication activation, manual/autonomous/hybrid activation, cross-start comparison activation, and cross-tool applicability-map equality tests.

`REQ-PORT-026` — Canonical milestone completion MUST be computed from machine-readable include/exclude selectors plus allowed lifecycle classes and structured applicability: a milestone passes only when every selected requirement whose lifecycle is allowed for that milestone and whose applicability is active is `PASS` or gate-permitted justified `NOT_APPLICABLE`, while MERGE_GUARD and RELEASE_GUARD obligations remain in `activated_governance`; acceptance evidence is P01 split-scope, newly added P01-core auto-inclusion, lifecycle filtering, inactive-applicability filtering, future-phase exclusion, and release-closure equality tests.

`REQ-PORT-027` — The portable execution-profile schema MUST represent `project_home`, `repo_root`, `temp_root`, `venv_root`, `cache_roots`, `tool_roots`, `bootstrap_sot_path`, canonical product repository identity, optional local repository-origin binding, effective `target_ref`, effective `operation_scope`, effective `authoring_mode`, effective `execution_adapter`, controller acquisition mode/identity, bootstrap phase/readiness identity, optional autonomous model-routing reference and resolved routing-snapshot identity, external controller-runtime-config role/hash, optional `remote_authorization_ref`, and per-role creation/preexistence policy as typed logical roles, MUST enforce `repo_root == project_home\mcp-vfp9sp2-toolchain` after Windows canonicalization, MUST enforce greenfield `target_ref=refs/heads/main`, MUST default brownfield `target_ref` to `refs/heads/main` while permitting an explicit existing-local-branch override, MUST default operation scope to `LOCAL_QUALIFICATION`, MUST represent both embedded time-zero bootstrap procedures before repository-local profiles exist, and MUST produce equivalent post-bootstrap logical bindings from generic, Converge, and conforming alternative profiles; acceptance evidence is SOT-only manual/autonomous pre-profile resolution, schema validation, canonical-repository identity, greenfield-main, brownfield-default-main, readiness identity, external-runtime-config hash, autonomous-pinned-Converge routing resolution, hybrid transition, controller acquisition, explicit-adapter override, cross-profile binding equality, alternate-drive, wrong-child, and missing-required-binding fixtures.

`REQ-PORT-028` — The canonical schema set MUST include offline JSON Schema 2020-12 definitions for bootstrap invocation/evidence, manual-bootstrap evidence, autonomous-bootstrap evidence, controller-bootstrap evidence, external controller-runtime configuration evidence, autonomous Source-of-Truth protection evidence, autonomous model-role/routing evidence, and execution-profile bindings, with closed field vocabulary covering `project_home`, `bootstrap_sot_path`, operation scope, authoring mode, embedded bootstrap phase/readiness, execution adapter, controller acquisition identity, autonomous routing reference/snapshot identity, external runtime-config identity, Source-of-Truth protection identity when applicable, repository/target-ref identity, tool/workspace overrides, typed path/array/string fields, and no embedded secrets, with schema semantics matching `REQ-G00-039` through `REQ-G00-041`, `REQ-G00-046`, and `REQ-G00-052` through `REQ-G00-074`; acceptance evidence is SOT-only manual-bootstrap evidence, SOT-only autonomous-bootstrap evidence, autonomous-pinned-Converge controller/config/protection/model bootstrap, embedded-to-profile transition, hybrid transition, explicit-adapter override, authorization-reference, default-main, unknown-field, secret-field, wrong-type, and normalized-evidence schema fixtures.

`REQ-PORT-029` — The canonical schema set MUST include an offline JSON Schema 2020-12 definition for `BROWNFIELD_PREFLIGHT`, `BROWNFIELD_BOOTSTRAP_PREFLIGHT`, and `evidence/brownfield/start-baseline.json` covering bootstrap-invocation/SOT identities, canonical/local repository identities, effective target ref, starting and bootstrap Git commit/tree states, authoritative-content identity, tracked/untracked cleanliness proof, repository-local ignore-rule identity, ignored-local-state inventory/hash, submodule identities, current public-surface inventory/hash, candidate/bootstrap tree identities, capture schema version, and canonical logical-content hashes, while timestamps and local absolute paths remain non-authoritative metadata outside the logical hash; acceptance evidence is clean-baseline validation, wrong-ref, prohibited-working-state refusal, safe-ignored-state validation, changed-ignore-rules, ignored-state collision, candidate/bootstrap mismatch, tampered-public-surface hash, changed-HEAD/tree, timestamp-independence, and local-path-redaction fixtures.

`REQ-PORT-030` — The requirement graph and gate evaluator MUST expose operation-scope and authoring-mode applicability as first-class machine-readable inputs, MUST evaluate `PUBLICATION` as satisfying predicates that list `PUBLICATION` and remote-integration predicates whose allowed set explicitly contains it, MUST evaluate `LOCAL_QUALIFICATION` without activating remote-integration/publication-only requirements, MUST evaluate `MANUAL` without activating autonomous-authoring-only requirements, and MUST include effective operation scope, authoring mode, and authorization identity in closure/evidence hashes; acceptance evidence is local-qualification closure, remote-integration closure, publication closure, manual closure, autonomous closure, hybrid closure, membership semantics, scope/mode-change invalidation, and cross-adapter closure-equality tests.

`REQ-PORT-031` — The canonical evidence schema set MUST define a remote-integration policy snapshot and integration receipt with closed machine-readable fields for canonical destination identity, effective target ref, observed remote-head commit, integration mode `NATIVE_PROTECTED|TRUSTED_UNPROTECTED|POLICY_UNKNOWN`, authoritative protection/ruleset evidence when available, Source of Truth gate/review/remote-CI identities, remote-authorization identity, authoring provenance identity, candidate/base commit and tree identities, final integration commit/tree identity, relation `IDENTITY_FAST_FORWARD|TREE_EQUIVALENT_DERIVED|TREE_CHANGED_DERIVED`, ref-update or platform-merge method, post-integration verifier root, and final remote-head identity, with timestamps and transport-specific response metadata excluded from logical identity; acceptance evidence is protected merge/squash/rebase receipts, unprotected snapshot, policy-unknown snapshot, changed-head invalidation, changed-policy invalidation, tree-equivalence, tree-change, and schema-closure tests.

`REQ-PORT-032` — The canonical evidence schema set MUST define authoring provenance with closed fields for effective authoring mode, actor class `HUMAN|CODING_AGENT|GENERATED|TRUSTED_INTEGRATION`, non-sensitive actor identity or opaque run identity, base/candidate commit and tree identities, changed-path digest, mode-transition history, generator identity when applicable, and evidence references, MUST keep independent-review identities separate from candidate-author identities so reviewer-independence checks remain possible without requiring disclosure of personal identity, and equivalent accepted candidate trees MUST remain comparable across authoring modes; acceptance evidence is manual, autonomous, hybrid, generated, trusted-integration, mode-transition, author/reviewer-separation, missing-attribution, and privacy-redaction schema fixtures.

`REQ-PORT-033` — The canonical evidence schema set MUST define independent-review evidence with reviewer class `HUMAN|MODEL|DETERMINISTIC_TOOL|COMPOSITE`, non-sensitive reviewer or execution identity, reviewed commit/tree identity, requirement/context hashes, candidate-author/modifier identities used for independence checks, review dimensions, findings, verifier-state references, outcome, optional class-specific profile metadata, and model-routing snapshot/role identity when reviewer class uses a model, and the schema MUST NOT require a model-provider field for `HUMAN` or `DETERMINISTIC_TOOL`; acceptance evidence is human-review schema, deterministic-tool schema, model-review-with-route schema, composite schema, author/reviewer collision, stale-reviewed-tree, verifier-failure-override refusal, missing-identity, and no-model-manual-review fixtures.

`REQ-PORT-034` — Every execution-adapter profile MUST declare stable adapter identity/version, immutable acquisition origin/revision/content identity or an explicit operator-bound installed-controller identity, supported authoring modes, supported operation scopes, controller class `HUMAN_OPERATED|AUTONOMOUS_ORCHESTRATOR|HYBRID_CONTROLLER`, contract-input format, requirement-graph/applicability implementation, verifier dispatch semantics, evidence output mappings, permission boundary, release-gate behavior, and for model-using controllers a mapping from `AUTONOMOUS_MODEL_ROLE_CONTRACT_V1` roles to adapter role/profile names without embedding exact model vendors into portable product semantics; adapter conformance MUST prove semantic equivalence against the portable generic/reference contracts for identical candidate trees rather than require identical internal implementation; acceptance evidence is generic-reference, pinned-Converge-adapter, alternative-autonomous-adapter, human-operated-adapter, acquisition-identity mismatch, missing-role-map, unsupported-authoring-mode, weakened-verifier, changed-applicability, changed-evidence, and cross-adapter semantic-equivalence tests.

`REQ-PORT-035` — The canonical controller-bootstrap evidence schema MUST define adapter identity/version, acquisition mode `BOUND_TOOL_ROOT|CONNECTED_PINNED|OFFLINE_CACHE`, approved origin, immutable revision, expected and observed tree/content fingerprints, canonicalized tool root, launcher identity/version, Source of Truth hash, bootstrap-invocation hash, handoff target, verification result, and redacted diagnostics, and the logical evidence hash MUST exclude timestamps, credentials, tokens, and machine-specific absolute paths except where a path is required as non-authoritative local evidence; acceptance evidence is bound-tool, connected-pinned, offline-cache, wrong-origin/revision/tree, tampered-content, secret-redaction, timestamp-independence, and handoff-hash fixtures.

`REQ-PORT-036` — The canonical manual-bootstrap evidence schema MUST represent `MANUAL_BOOTSTRAP_V1` phase, Source of Truth hash, bootstrap-invocation hash, start-mode/classification evidence, pre-mutation repository identity when present, candidate-tree identity, bootstrap-preflight identity, resulting bootstrap commit/tree, B0/BR0 result, and embedded-to-generic handoff identity, while timestamps, operator identity details, and machine-specific absolute paths remain non-authoritative metadata; acceptance evidence is greenfield-manual, brownfield-manual, phase-order, candidate/preflight/commit chain, handoff, tamper, timestamp-independence, and privacy-redaction fixtures.

`REQ-PORT-037` — The canonical autonomous model-routing schema MUST define role contract version, routing-snapshot identity, route source identity, provider/gateway identity, exact primary provider/model per active role, declared context/output limits, ordered fallback routes, retry policy, request-option hash, observed catalog identity, secret-variable names without values, controller/adapter identity, preflight result, and evidence dependencies, and it MUST permit provider-specific metadata only in a namespaced extension object that cannot alter portable role or verifier semantics; acceptance evidence is complete-routing, missing-role, duplicate-primary, ordered-fallback, moving-alias catalog freeze, context-limit, secret-redaction, provider-extension, routing-hash, and cross-adapter role-schema fixtures.

`REQ-PORT-038` — The canonical autonomous-bootstrap/runtime-config evidence schema MUST define `AUTONOMOUS_BOOTSTRAP_V1` phase, Source of Truth hash, bootstrap-invocation hash, start-state and B0/BR0 readiness identities, bootstrap seed commit/tree, selected adapter/controller identity, external runtime-config logical hash and storage role outside `REPO_ROOT`, Source-of-Truth write-protection policy/evidence identity, model-routing snapshot identity, target repo/base-branch binding, remote-scope binding, state/worktree roles, quality/verifier binding identity, controller environment-preflight result, handoff result, and redacted diagnostics, with timestamps, secret values, and machine-specific absolute paths excluded from portable logical identity except as non-authoritative local evidence; acceptance evidence is greenfield-autonomous, brownfield-autonomous, local/remote config, protected-SOT seed/config/routing chain, invalid-runtime-config, writable-SOT, environment-preflight failure, handoff tamper, secret-redaction, and timestamp-independence fixtures.

`REQ-PORT-039` — The canonical autonomous Source-of-Truth protection evidence schema MUST define protected-file content hash, protection mechanism class, non-sensitive protected-object identity, execution identity class, verified denied operations `WRITE|REPLACE|RENAME|DELETE|PERMISSION_RELAX`, verified allowed read operation, protection-establishment result, protection-revalidation result, and invalidation reason, while raw ACL security identifiers, credentials, usernames, and machine-specific absolute paths remain redacted or non-authoritative local metadata; acceptance evidence is NTFS-ACL success, equivalent-boundary success, weak-ReadOnly-only refusal, denied-operation matrix, read-success, changed-hash, lost-protection, identity-redaction, and logical-hash stability fixtures.


## Phase 1 — Core Service, sessions, jobs and minimal MCP shell

`REQ-P01-001` — The repository MUST keep one transport-neutral Python Core Service as the single domain implementation, and CLI, MCP, tests, maintenance utilities, and any coding-agent or orchestration integration MUST delegate to that service rather than duplicate VFP, DBF, form, relationship, query, privacy, refactoring, or PostgreSQL logic; acceptance evidence is architecture-boundary tests and equivalent adapter snapshots.

`REQ-P01-002` — The Core Service MUST expose versioned typed JSON-serializable models for operation results, errors, capabilities, project sessions, dataset sessions, artifacts, source spans, provenance, confidence, completeness, findings, jobs, graph nodes/edges, form models, table profiles, relations, query plans/results, index facts, performance evidence, refactor plans/results, knowledge topics, and privacy results; acceptance evidence is public-import tests, JSON Schema snapshots, and round-trip serialization.

`REQ-P01-003` — Every public operation MUST return a bounded common envelope containing schema version, status, operation, project and dataset identities where applicable, capability classes, backend/provenance, source-modified state, warnings, typed errors, artifacts, data, and evidence references; acceptance evidence is envelope contract tests across every operation family.

`REQ-P01-004` — The service MUST use a centralized stable machine-readable error registry and MUST preserve typed downstream error codes from dbfbridge and DBF_Anonymizer where available without classifying failures from prose text; acceptance evidence is registry uniqueness tests and typed error fixtures covering dependency, VFP, FoxBin2Prg, data, form, refactor, path, cancellation, PostgreSQL, privacy, and resource-limit error categories.

`REQ-P01-005` — Capability discovery MUST be side-effect-free and MUST not open user project tables, create files, launch VFP, launch FoxBin2Prg, instantiate COM, inspect recovery vault contents, or contact the network; acceptance evidence is filesystem, subprocess, COM, vault, and network sentinels.

`REQ-P01-006` — The capability catalog MUST retain `PURE_READ`, `PURE_WRITE_COPY`, `VFP_READ_ENHANCED`, `VFP_WRITE_WORKSPACE`, `VFP_BUILD_VALIDATE`, `PRIVACY_SENSITIVE`, and `SOURCE_PROMOTION`, and every operation MUST advertise all applicable capability classes; acceptance evidence is registry-to-operation drift tests.

`REQ-P01-007` — Each opened VFP application MUST receive an opaque `project_id` bound to a canonical Windows source root, immutable source snapshot identity, artifact topology, configuration fingerprint, VFP dialect, and lifecycle state; acceptance evidence is simultaneous two-project tests proving no process-global current-project leakage.

`REQ-P01-008` — Each registered data root MUST receive an opaque `dataset_id` bound to `ORIGINAL`, `ANONYMIZED`, or `WORKSPACE` role, canonical root, source fingerprint, table inventory, schema fingerprint, and optional lineage parent; acceptance evidence is multi-dataset isolation and explicit-role tests.

`REQ-P01-009` — Long operations MUST use a Core job manager with progress, cooperative cancellation, timestamps, bounded evidence, result retrieval by stable `job_id`, and cleanup semantics independent of the initiating MCP request lifetime; acceptance evidence is cancellation, reconnect, completed-job retrieval, and cleanup tests.

`REQ-P01-010` — Project, dataset, artifact, table, record, field, form object, method, relation, finding, knowledge topic, and refactor identities MUST be stable within an immutable source snapshot and MUST change deterministically when their identity-defining source changes; acceptance evidence is stable-ID and one-change invalidation tests.

`REQ-P01-011` — The repository MUST implement a minimal official-Python-SDK MCP v2 server shell immediately after the Core Service foundation and expose truthful capability, project/dataset registration, job-status, job-cancellation, and discovery operations without duplicating domain logic; acceptance evidence is an official MCP client smoke test on Windows.

`REQ-P01-012` — The minimal MCP server MUST omit or explicitly report unavailable advanced tools until their backing Core capability passes its release gate, and placeholder success responses MUST not be used to simulate unfinished analysis, refactoring, privacy, or PostgreSQL features; acceptance evidence is a capability-to-registry consistency test.

`REQ-P01-013` — After the first qualified MCP release, incompatible changes to release-qualified tool names, resource templates, input schemas, output schemas, error codes, or semantic meanings MUST use explicit contract versioning or a documented migration path rather than silent replacement, independent of whether the affected qualified releases have been publicly published; acceptance evidence is compatibility snapshot tests across adjacent qualified releases and published-subset identity tests.

`REQ-P01-014` — Any persistent project/session metadata, job ledger, semantic index, query workspace metadata, refactor record, privacy record, or PostgreSQL migration state MUST carry an explicit schema version and origin identity, and non-cache durable state upgrades MUST use deterministic atomic migrations with backup or rollback evidence before the new schema is published; acceptance evidence is upgrade, interrupted-upgrade, rollback, and unsupported-newer-schema tests.

`REQ-P01-015` — Every reusable cache entry MUST be keyed by the source snapshot identity plus all interpretation inputs that can change its meaning, including relevant parser/model schema versions, knowledge-corpus identity, dependency/tool identities, configuration/policy identity, and operation parameters, and a cache entry with a mismatched key MUST never contribute evidence to a result; acceptance evidence is stale-source, changed-parser, changed-corpus, changed-policy, and changed-dependency invalidation tests.

`REQ-P01-016` — Caches MUST be disposable and rebuildable from authoritative inputs, while durable jobs and migration/refactor state MUST distinguish resumable state from derivable cache state so cache deletion, corruption, or format upgrade cannot destroy authoritative project data or falsely complete an operation; acceptance evidence is cache deletion/rebuild, corruption, restart, and resume tests.

`REQ-P01-017` — A resumed long-running job MUST verify the same project/dataset snapshot, effective policy, dependency identities, and output/staging identity that existed at checkpoint time before continuing, and any incompatible change MUST produce a typed stale-checkpoint refusal rather than reuse partial evidence; acceptance evidence is changed-source, changed-policy, changed-tool, changed-output, and valid-resume fixtures.

`REQ-P01-018` — The product MUST expose a versioned machine-readable configuration schema covering host paths, project/dataset registration defaults, backend identities, execution/time/resource limits, MCP transport policy, PostgreSQL target references, logging/redaction policy, and feature flags, with strict rejection of unknown or misspelled keys unless an explicit extension namespace is defined; acceptance evidence is schema, unknown-key, typo, extension-namespace, and default-resolution tests.

`REQ-P01-019` — Every configurable field MUST declare which configuration sources can set it, and effective configuration resolution MUST be deterministic, auditable, and hashable after secret redaction so defaults, configuration files, environment-backed secret references, command-line options, and execution-profile overrides cannot silently compete for the same security-sensitive value; acceptance evidence is source-precedence, prohibited-override, effective-config-hash, and redaction tests.

`REQ-P01-020` — Configuration schema upgrades MUST preserve supported prior configurations through deterministic migration or emit a typed unsupported-version refusal with actionable diagnostics, and migration MUST never broaden path permissions, enable mutation, enable network transport, expose secrets, or activate PostgreSQL writes solely because a default changed between versions; acceptance evidence is prior-version migration, security-default preservation, unsupported-newer-version, and downgrade-readability tests.

`REQ-P01-021` — Every durable filesystem write for configuration migrations, project/session metadata, compliance state, requirement/verification manifests, job checkpoints, refactor records, migration records, and other authoritative local JSON/text artifacts MUST use a verified crash-safe publication strategy: same-volume write/flush/close/integrity-check plus atomic replace when the configured root proves that semantic, or a versioned journal/two-phase recovery protocol when atomic replace cannot be relied upon, so interruption leaves a recoverable prior or new valid state rather than a partially authoritative file; acceptance evidence is local-atomic, non-atomic-root, power-loss/fault-injection-at-each-step, journal-recovery, and restart tests.

## Phase 2 — Windows path security, source safety and execution isolation

`REQ-P02-001` — The host configuration MUST define canonical Windows `allowed_read_roots`, `allowed_data_roots`, `allowed_output_roots`, `allowed_workspace_roots`, and `sensitive_vault_roots`, and every path access MUST reject traversal, symlink/junction/reparse-point escape, case/alias confusion, forbidden UNC targets, and cross-zone overlap; acceptance evidence is adversarial Windows path fixtures.

`REQ-P02-002` — Original project and original dataset roots MUST remain immutable for analysis, query, profiling, Help lookup, and privacy planning, and every operation that touches source files MUST verify pre/post hashes or equivalent snapshot invariants; acceptance evidence is success/failure/cancellation write sentinels.

`REQ-P02-003` — Workspace, anonymized-output, build-output, scratch, cache, and recovery-vault paths MUST be explicitly distinct from immutable source roots after canonical resolution; acceptance evidence is overlap-matrix tests.

`REQ-P02-004` — Source promotion MUST be disabled by default at host policy level and enabling it MUST not weaken workspace-first refactoring, exact hash preconditions, companion-file closure, rollback evidence, or atomic replacement behavior; acceptance evidence is default-deny and enabled-policy tests.

`REQ-P02-005` — Subprocess execution MUST use configured allowlisted executable identities with argument arrays, working-directory controls, timeouts, bounded captured output, and no user-controlled shell command concatenation; acceptance evidence is command-injection and executable-origin tests.

`REQ-P02-006` — Logs, exceptions, progress events, default audit artifacts, telemetry-free diagnostics, and capability results MUST redact DBF/Memo values, credentials, connection secrets, recovery material, and sensitive paths except where a value-bearing query explicitly returns selected data to the caller; acceptance evidence is canary leakage scans.

`REQ-P02-007` — The service MUST enforce configurable limits for files, file size, memo bytes, rows scanned/returned, regex execution, profile cardinality tracking, graph nodes/edges, query joins/intermediate rows, result bytes, help excerpts, subprocess output, job duration, concurrent pure jobs, and concurrent VFP workers, failing with typed resource-limit errors; acceptance evidence is boundary tests.

`REQ-P02-008` — Concurrent jobs MUST isolate project state, dataset state, temporary relational workspaces, caches, FoxBin2Prg scratch copies, refactor workspaces, privacy state, and VFP workers, while conflicting writes to the same output/workspace/vault/promotion target MUST fail closed under explicit locks; acceptance evidence is concurrency stress tests.

`REQ-P02-009` — Normal MCP request handling MUST perform no outbound telemetry or live documentation lookup, and all documentation, dependency provenance, and language rules used for an answer MUST come from locally pinned assets or project files; acceptance evidence is network sentinels.

`REQ-P02-010` — Windows path authorization MUST normalize and reject unsafe or ambiguous NTFS/Win32 path forms including device namespaces, reserved device names, alternate data streams, trailing-dot/space aliases, 8.3 short-name alias escapes, unexpected hard-link identity changes where detectable, reparse points, junctions, symlinks, case-insensitive aliases, and disallowed UNC targets before authorization decisions; acceptance evidence is an adversarial Windows filesystem fixture matrix.

`REQ-P02-011` — All VFP source text, comments, DBF Character/Memo/General content, filenames, DBC metadata, form properties, report/menu text, external-component metadata, and other project-controlled content MUST be treated as untrusted data rather than agent instructions, execution directives, policy text, or tool-call authorization; acceptance evidence is prompt-injection and instruction-like-content fixtures proving identical structured handling as ordinary data.

`REQ-P02-012` — Structured MCP, CLI, log, JSON, Markdown, and diagnostic rendering MUST preserve data fidelity while safely encoding control characters, terminal escape sequences, delimiter-breaking text, embedded markup, and instruction-like strings so project content cannot alter protocol structure, terminal behavior, audit structure, or verifier parsing; acceptance evidence is control-character, ANSI escape, Markdown/JSON delimiter, and Unicode edge-case fixtures.

`REQ-P02-013` — Analysis and indexing operations MUST NOT execute application source, macros, ActiveX/COM callbacks, external binaries, VFP event code, SQL supplied by project data, or generated scripts merely because such content is discovered, and every execution-capable validation path MUST require an explicit trusted execution profile and isolated workspace; acceptance evidence is malicious-looking source/data fixtures plus default-no-execution and trusted-profile tests.

`REQ-P02-014` — Subprocesses and VFP/FoxBin2Prg helpers MUST receive a minimal allowlisted environment rather than inheriting arbitrary parent-process secrets, and credentials, model/API keys, PostgreSQL secrets, recovery secrets, and unrelated environment variables MUST be absent unless the invoked capability explicitly declares and redacts the needed reference; acceptance evidence is environment-secret canaries and capability-specific allowlist tests.

`REQ-P02-015` — Sensitive vaults, temporary copies containing original values, PostgreSQL credential material, and reversible anonymization state MUST apply and verify a versioned Windows ACL policy that grants access only to the executing product identity plus explicitly allowlisted administrative/service principals, rejects unexpected broad inherited access before use, performs deterministic lifecycle cleanup with typed cleanup-failure reporting, and MUST NOT claim cryptographic secure deletion where the underlying filesystem/storage cannot prove it; acceptance evidence is effective-ACL, inherited-broad-access refusal, allowlisted-admin, cleanup, locked-file cleanup-failure, and no-false-secure-delete tests.

`REQ-P02-016` — Allowed Windows roots and project artifacts MUST support Unicode and extended-length paths within the capabilities of Python and the selected backend, and a VFP9, FoxBin2Prg, ODBC, or other external-tool path limitation MUST be surfaced as a typed capability/compatibility finding rather than causing silent truncation, aliasing, or fallback to a different file; acceptance evidence is Polish/non-ASCII names, extended-length paths, legacy-tool-limit, and wrong-file-alias fixtures.

`REQ-P02-017` — The repository MUST maintain a versioned machine-readable threat model covering protected assets, trust boundaries, attacker-controlled inputs, local privilege assumptions, MCP transports, filesystem/path attacks, prompt-injection/data-content attacks, subprocess/COM/VFP execution, dependency/supply-chain attacks, privacy/recovery material, PostgreSQL targets, release credentials, and evidence publication, and every security-critical requirement/test MUST reference one or more threat/control identifiers; acceptance evidence is threat-model schema validation, control-to-test coverage, newly exposed surface without threat update, and orphaned-threat-control fixtures.

`REQ-P02-018` — Configured UNC or SMB roots that are explicitly allowed MUST be identified as network-backed storage, MUST use the same path-authorization and snapshot-consistency rules as local roots plus typed handling for disconnects, reconnects, sharing/oplock conflicts, partial copies, changed server/file identity, and unavailable atomic-rename guarantees, and the product MUST NOT claim local-filesystem atomicity or consistency semantics that the verified share cannot provide; acceptance evidence is synthetic/local-share or controlled SMB fixtures for stable read, disconnect, mutation during snapshot, sharing conflict, identity change, and unsupported-atomicity cases.

`REQ-P02-019` — Repository and source discovery MUST treat `PROJECT_HOME` as an execution container rather than a source root: target-repository scans MUST stay inside canonical `REPO_ROOT`, dataset/project scans MUST stay inside explicitly registered allowed roots, and sibling Converge/tool checkouts, TEMP, venv, caches, logs, external Source of Truth copies, or unrelated repositories MUST NOT enter source graphs, package contents, release artifacts, evidence payloads, or dependency inventories merely because they are located under `PROJECT_HOME`; acceptance evidence is sibling-canary discovery, packaging, evidence, and dependency-inventory isolation tests.

`REQ-P02-020` — Creation or reuse of `repo_root`, `temp_root`, `venv_root`, `cache_roots`, and provisioned `tool_roots` MUST validate canonical parent/child relationships and existing reparse-point/junction/symlink targets before mutation, MUST refuse any role whose resolved target escapes its declared allowed boundary or aliases another protected role unexpectedly, and MUST never recursively delete a pre-existing nonempty directory merely to satisfy a workspace default; acceptance evidence is safe-missing-directory creation, junction escape, symlink/reparse alias, role-alias collision, nonempty-default-path preservation, and alternate-volume fixtures.

## Phase 2A — Autonomous delivery, regression prevention and publication governance

`REQ-AUTO-001` — Every implementation run in any authoring mode MUST use the Source of Truth as an immutable reviewed input, pin its SHA-256, effective execution-profile/configuration snapshot, operation scope, and authoring mode for the run, and fail closed if the contract or effective run configuration changes during execution; acceptance evidence is manual/autonomous/hybrid preflight plus mid-run contract/configuration mutation tests.

`REQ-AUTO-002` — The portable verification specification MUST cover 100 percent of mandatory requirement IDs before implementation can claim verified progress, while an executable deterministic verifier MUST exist before a requirement can transition to PASS and before any release gate that depends on it can pass, independent of authoring mode; acceptance evidence is full specification-coverage, manual/autonomous/hybrid planned-verifier, executable-verifier, missing-executable-verifier, and release-gate refusal tests.

`REQ-AUTO-003` — The repository MUST maintain a machine-readable verification manifest that maps every mandatory requirement ID to verifier specification, verifier state `PLANNED|EXECUTABLE`, test selectors or verifier commands when executable, evidence class, required fixture capabilities, and release gates that depend on it, and the manifest MUST contain neither missing mandatory IDs nor unknown IDs; acceptance evidence is exact-set comparison with the Source of Truth plus state/schema validation.

`REQ-AUTO-004` — A deterministic verifier runner MUST return non-PASS for a `PLANNED` verifier and MUST fail closed for an unknown requirement ID, zero collected tests from an `EXECUTABLE` verifier, a missing fixture, a missing required external capability, timeout, crashed test process, malformed result, or unexpected skip/xfail instead of converting any of those states to PASS; acceptance evidence is one negative-control fixture for every listed failure mode.

`REQ-AUTO-005` — Every deterministic test that serves as executable requirement evidence MUST carry one or more explicit requirement IDs through pytest markers, generated manifests, or an equivalently machine-readable mechanism, and CI MUST fail if a requirement marked `EXECUTABLE` loses all executable evidence after a code or test change; acceptance evidence is test-collection metadata and executable-state consistency validation.

`REQ-AUTO-006` — Every candidate change in `MANUAL`, `AUTONOMOUS`, or `HYBRID` authoring mode MUST run repository-wide deterministic quality gates in addition to the verifier for the targeted requirement, and release candidates MUST run the complete regression profile rather than only tests selected by changed files; acceptance evidence is manual/autonomous/hybrid gate inspection plus a deliberate unrelated-regression fixture that blocks integration.

`REQ-AUTO-007` — Previously passing mandatory requirement verifiers MUST remain monotonic across candidate changes in every authoring mode so a candidate that makes any earlier mandatory verifier non-PASS is rejected even when the targeted requirement improves; acceptance evidence is manual/autonomous/hybrid two-requirement scenarios that deliberately regress an earlier PASS and are blocked.

`REQ-AUTO-008` — Changes to verification manifests, verifier code, release-gate definitions, golden baselines, test-selection rules, skip/xfail policy, coverage thresholds, or security/path-policy fixtures MUST be treated as verification-surface changes and MUST trigger the complete deterministic suite plus independent correctness and architecture review under `REQ-AUTO-048`, with no requirement for a model reviewer when an eligible human or deterministic reviewer is used; acceptance evidence is manual-human-review, manual-deterministic-review, autonomous-independent-review, change-classification, and CI path-trigger tests.

`REQ-AUTO-009` — No implementation workflow or authoring actor MUST satisfy a failing requirement by deleting its evidence test, broadening an ignore rule, adding an unconditional skip/xfail, reducing a coverage or mutation threshold, replacing an exact assertion with a weaker existence assertion, or rewriting a golden baseline without a corresponding requirement-validating semantic diff; acceptance evidence is anti-evasion meta-tests that introduce each prohibited weakening in manual/autonomous/hybrid candidate fixtures and confirm gate failure.

`REQ-AUTO-010` — Release CI MUST treat every unexpected skipped, xfailed, xpassed, deselected mandatory, or collection-error test as failure, capability-specific tests MUST be omitted only from release profiles whose declared capability manifest explicitly excludes that capability, and every capability declared by a release profile MUST execute its required capability tests; acceptance evidence is skip/xfail/xpass/deselection and declared-capability-without-test negative controls.

`REQ-AUTO-011` — Critical verifier families MUST contain negative-control meta-tests that intentionally inject a known violation into a temporary copy or synthetic input and prove that the verifier fails for the intended machine-readable reason; acceptance evidence covers at least source mutation, path escape, dependency-origin mismatch, public-schema drift, lost Memo data, lost form method/property, relation corruption, unsafe SQL translation, and PostgreSQL parity corruption.

`REQ-AUTO-012` — Deterministic tests MUST control or explicitly record random seeds, Windows locale, Windows code page, timezone, current working directory, temporary paths, clock-dependent inputs, concurrency level, and network availability whenever those factors can affect results, and failed randomized/property tests MUST persist the reproducing seed/example; acceptance evidence is environment-variation replay tests.

`REQ-AUTO-013` — Automated tests and public fixture packages MUST use redistributable synthetic data only and MUST contain no copied production/customer DBF, FPT, DBC, SCX, VCX, credentials, recovery vaults, or sensitive Memo values; acceptance evidence is repository secret/data-pattern scanning plus fixture provenance records.

`REQ-AUTO-014` — The repository MUST maintain a versioned synthetic-fixture coverage matrix that enumerates supported artifact families, field types, code pages, Memo states, DBC/view cases, index cases, form/class structures, dynamic-code cases, malformed/corrupt cases, relationship cardinalities, PostgreSQL conversion cases, and expected release coverage, and CI MUST fail if a claimed supported category has no fixture; acceptance evidence is matrix-to-fixture exact coverage validation.

`REQ-AUTO-015` — Golden fixtures and snapshot outputs MUST carry content hashes and semantic version metadata, and updating a golden expectation MUST require a generated before/after semantic diff reviewed as test evidence rather than a blanket snapshot refresh; acceptance evidence is intentional-golden-update and unauthorized-refresh tests.

`REQ-AUTO-016` — Parsers, Windows path canonicalization, DBF/Memo boundary handling, structured query models, canonical SC2/VC2 parsing/rendering, SQL translation, and serialization schemas MUST have property-based or bounded fuzz tests for malformed, boundary, and adversarial inputs with discovered minimal failures retained as permanent regression fixtures; acceptance evidence is deterministic seeded fuzz/property jobs.

`REQ-AUTO-017` — Where two independent interpretations exist, CI MUST use differential tests rather than trusting one implementation, including pure parser versus FoxBin2Prg/VFP runtime facts, dbfbridge source values versus reconstructed or target values, and VFP query results versus translated PostgreSQL query results where semantics are declared equivalent; acceptance evidence is matching and deliberate-divergence fixtures.

`REQ-AUTO-018` — Round-trip-sensitive features MUST have metamorphic tests that preserve declared invariants across DBF/FPT reconstruction, FoxBin2Prg BIN2PRG/PRG2BIN, canonical form rendering, anonymization verification, serialization/deserialization, and PostgreSQL source-target canonicalization; acceptance evidence is invariant assertions before and after each round trip.

`REQ-AUTO-019` — Safety-critical modules for Windows path policy, source promotion, refactor transformation/validation, privacy boundary enforcement, SQL parameterization, PostgreSQL type/value conversion, and cutover-state transitions MUST undergo release-time mutation testing or equivalent deterministic fault injection, and survived critical mutants or injected faults MUST block release unless individually justified in a version-controlled allowlist with requirement references; acceptance evidence is mutation/fault-injection reports.

`REQ-AUTO-020` — Line and branch coverage thresholds MUST be version-controlled, measured on production modules rather than tests, and MUST NOT decrease across accepted candidate changes in any authoring mode without an explicit contract-evolution record, while coverage alone MUST NOT substitute for requirement-specific tests; acceptance evidence is manual/autonomous/hybrid baseline-comparison tests plus a deliberate threshold-reduction rejection.

`REQ-AUTO-021` — Concurrency, cancellation, timeout, retry, crash-recovery, resource-limit, and repeated-start/stop behaviors MUST have deterministic stress tests that assert cleanup of temporary files, locks, jobs, file handles, owned VFP workers, database transactions, and PostgreSQL staging state; acceptance evidence is repeated and fault-injected lifecycle tests.

`REQ-AUTO-022` — Every release-qualified MCP tool/resource/schema and every release-qualified Python Core model MUST have a machine-readable contract snapshot; the first qualified release snapshot MUST record predecessor state `INITIAL_RELEASE`, every later qualified release MUST be compared against the immediately preceding qualified release with incompatible changes failing qualification unless the Source of Truth explicitly authorizes the versioned break, and later publication MUST reference rather than regenerate the qualified snapshot; acceptance evidence is initial-snapshot, qualified-predecessor old-client/new-server, schema-diff, and publication-snapshot-identity tests.

`REQ-AUTO-023` — Dependency tests MUST verify both declared version compatibility and actual loaded module or executable origin so a shadow package, global installation, unexpected FoxBin2Prg tree, wrong VFP executable, or wrong ODBC driver cannot satisfy a capability merely by matching a name; acceptance evidence is shadow-origin and wrong-executable negative controls.

`REQ-AUTO-024` — Trusted-host requirements such as VFP9 SP2 COM execution, FoxBin2Prg binary regeneration, SYS(3054), VFP compile/build, structural index rebuild, psqlODBC access, and VFP-to-PostgreSQL transition MUST have dedicated trusted Windows verifier profiles whose absence prevents the release gate that claims the capability rather than silently skipping the tests; acceptance evidence is trusted-profile-present and trusted-profile-missing gate tests.

`REQ-AUTO-025` — Every release gate MUST have a machine-readable release-gate manifest listing the exact prerequisite requirement IDs, required deterministic suites, required trusted-host suites, public tool/resource/schema snapshot, explicitly unavailable future capabilities, package version, and expected artifacts; acceptance evidence is manifest schema validation plus exact prerequisite-closure checks.

`REQ-AUTO-026` — A release gate MUST rerun the smoke and compatibility suites of every earlier qualified release in the same canonical release lineage and MUST fail when a capability previously qualified in any earlier release disappears, changes schema incompatibly, changes default safety policy, or returns weaker evidence without an explicitly authorized contract evolution, regardless of whether the predecessor was publicly published; acceptance evidence is unpublished-qualified-predecessor, published-predecessor, cumulative release-regression, and incompatible-change tests.

`REQ-AUTO-027` — Completion of a release-gate requirement MUST create a deterministic release-candidate and qualification manifest on the exact clean local `target_ref` commit being evaluated; `LOCAL_QUALIFICATION` can complete against that commit without remote mutation, while remote integration/publication MUST preserve the qualification through either exact commit identity or the verified tree-equivalent mapping permitted by `REQ-AUTO-055`, and a tree-changed derived integration MUST be requalified on the final integrated tree before publication; acceptance evidence is local-qualification commit binding, no-remote-write local path, identity-fast-forward mapping, tree-equivalent-derived mapping, tree-changed requalification, artifact-identity preservation, and pre-integration publication refusal tests.

`REQ-AUTO-028` — Under `PUBLICATION` scope, public release automation MUST build or retrieve wheel and sdist artifacts whose hashes equal an eligible qualified release record, verify the final canonical integrated release commit and candidate-to-integration relation under `REQ-AUTO-055`, reproduce normalized artifact hashes from the integrated commit when qualification is transferred by tree equivalence, install the wheel into a clean supported Windows environment, execute the release-gate MCP smoke scenario through the official MCP client, and only then publish immutable artifacts and checksums through non-interactive trusted credentials authorized by `REQ-G00-053`; a production GitHub Release MUST verify destination identity `https://github.com/PeterPirog/mcp-vfp9sp2-toolchain`, while an explicitly authorized staging publisher can use a non-production destination that cannot be mistaken for the canonical release; acceptance evidence is exact-commit qualification, tree-equivalent qualification transfer, tree-changed requalification, qualification-artifact identity, canonical-destination verification, wrong-destination refusal, missing-authorization refusal, and authorized staging/production publication receipt tests.

`REQ-AUTO-029` — Under `PUBLICATION` scope, every public release MUST publish SHA-256 checksums, an SBOM or equivalent machine-readable dependency inventory, Source of Truth and Git commit provenance, exact tested dependency/runtime identities, release-gate evidence summary, release notes, and the immutable qualification-record identity; the first public release MUST mark publication predecessor state `INITIAL_RELEASE`, while later public releases MUST include upgrade notes from the previous published release even when additional unpublished qualified releases exist; acceptance evidence is first-publication, later-publication, qualification-record-binding, and asset-completeness validation.

`REQ-AUTO-030` — Under `PUBLICATION` scope, release automation MUST be idempotent and crash-resumable, MUST refuse to overwrite an existing published version or move an existing release tag to different content, MUST detect partial publication before retrying, and MUST preserve the qualified artifact identities so duplicate or divergent artifacts cannot be produced; acceptance evidence is interrupted-publication, duplicate-version, changed-qualified-artifact, and resumable-publication tests.

`REQ-AUTO-031` — Under `REMOTE_INTEGRATION` or `PUBLICATION` scope, the repository integration profile MUST enforce the same trusted integration safety invariant whether the canonical target branch is natively protected or unprotected: ordinary coding-agent credentials MUST NOT mutate remote refs or repository policy, the trusted integration layer MUST bind the observed remote `target_ref` commit and repository-policy snapshot before integration, deterministic gates, independent reviews, and required remote CI MUST pass for the exact candidate/base relation, and the resulting remote integration MUST satisfy the candidate-to-integration identity rules in `REQ-AUTO-055` while failing closed if the observed remote head or policy changes; existing branch protection or rulesets MUST be obeyed without automatic weakening, absence of branch protection MUST NOT itself block integration, and repository-policy mutation requires separate authorization under `REQ-G00-053`; acceptance evidence is protected-merge/squash/rebase, unprotected-fast-forward, remote-head-race, policy-change-race, no-authorization, ordinary-agent-no-push, and authorized-trusted-integration tests.

`REQ-AUTO-032` — Automatic CI retries MUST be limited to exact version-controlled check names independently classified as flaky with a finite retry budget, and deterministic test, requirement verifier, architecture, security, package, or release-gate failures MUST NOT be converted to success by generic rerun logic; acceptance evidence is flaky-allowlist and non-flaky-failure tests.

`REQ-AUTO-033` — Every integrated task in any authoring mode MUST retain an auditable evidence bundle linking authoring provenance, base commit, candidate commit, target requirement IDs, changed paths, deterministic gate results, requirement verifier results, independent reviews, resulting integration commit, and resulting compliance state; for remote integration the bundle MUST additionally bind remote repository/PR/CI/merge identities when present, while local integration MUST record remote-only fields as deterministically not applicable rather than fabricate them; acceptance evidence is manual/autonomous/hybrid local-integration bundles, protected/unprotected remote-integration bundles, missing-required-field, and mode/scope-mismatch validation.

`REQ-AUTO-034` — Before starting implementation against a revised Source of Truth, a deterministic contract-diff step MUST compare the last accepted repository contract snapshot with the new compiled contract, where the predecessor is the latest qualified/integrated contract snapshot for the canonical lineage or the captured bootstrap/brownfield baseline when no qualified release exists, and MUST classify every requirement ID as unchanged, added, explicitly superseded, or retired; silent disappearance, ID reuse, or semantic weakening MUST stop implementation before authoring work begins, and public publication status MUST NOT be required to establish the predecessor; acceptance evidence is manual/autonomous/hybrid baseline-predecessor, qualified-unpublished-predecessor, published-predecessor, added/unchanged/superseded/removed, and semantic-weakening fixtures.

`REQ-AUTO-035` — When an implementation planner splits one broad requirement into multiple bounded tasks, the requirement MUST remain non-PASS until every deterministic verifier component and acceptance artifact mapped to that requirement passes, and partial task completion MUST not be serialized as requirement completion; acceptance evidence is a multi-task single-requirement convergence fixture.

`REQ-AUTO-036` — An intermediate release gate MUST be independently publishable while later Source of Truth requirements remain pending, and its deterministic verifier MUST evaluate only its exact prerequisite closure plus cumulative earlier-release regressions while explicitly recording future capabilities as unavailable rather than failed; acceptance evidence is an early-release simulation with later requirements intentionally unimplemented.

`REQ-AUTO-037` — Repository documentation, capability matrices, generated schemas, generated manifests, examples, and user-facing help that describe implemented or release-qualified capability MUST be checked against the current registered implementation and release profile, and a code change that makes a qualified or published claim stale MUST fail integration until the claim is regenerated or corrected; acceptance evidence is qualified-unpublished claim drift, published-claim drift, and capability-drift fixtures.

`REQ-AUTO-038` — Generated contract, schema, capability, documentation-index, or verification artifacts MUST be reproducible from version-controlled authoritative inputs by documented deterministic commands, and no human or coding agent MUST hand-edit generated outputs when the generator or source model is the authoritative layer; acceptance evidence is regenerate-and-diff checks plus manual and autonomous hand-edited-generated-file negative fixtures.

`REQ-AUTO-039` — Before implementation intended to move a non-PASS requirement toward PASS, the workflow MUST first establish an executable deterministic verifier that demonstrates the current non-PASS condition or, when the baseline already satisfies the requirement, capture passing baseline evidence before modifying related code; acceptance evidence is test-first failing-baseline, already-satisfied-baseline, and implementation-before-verifier refusal fixtures.

`REQ-AUTO-040` — The compliance store MUST use explicit requirement states `UNASSESSED`, `PLANNED`, `NOT_IMPLEMENTED`, `PARTIAL`, `BLOCKED`, `PASS`, and `NOT_APPLICABLE`, and only `PASS` or a release-gate-permitted `NOT_APPLICABLE` with deterministic applicability evidence can satisfy prerequisite closure; acceptance evidence is state-transition, invalid-transition, blocked-as-nonpass, and unjustified-not-applicable tests.

`REQ-AUTO-041` — A `NOT_APPLICABLE` result MUST identify the deterministic applicability rule and evidence that makes the requirement irrelevant to the current start mode, host profile, project artifact graph, or release profile, and it MUST become non-PASS automatically if later evidence makes the requirement applicable; acceptance evidence is greenfield brownfield-only, absent-artifact, later-becomes-applicable, and unjustified-NA fixtures.

`REQ-AUTO-042` — A coding agent work packet MUST be generated from the hash-bound Source of Truth and requirement graph and contain the target requirement text, transitive prerequisite statuses, glossary terms used by the requirement, relevant architecture boundaries, verifier specification/state, acceptance evidence, release-gate consequences, and bounded repository context without altering normative meaning; acceptance evidence is deterministic work-packet generation and stale-hash refusal tests.

`REQ-AUTO-043` — Autonomous planning MUST prefer the smallest dependency-valid requirement or cohesive requirement set that can produce verified progress, MUST NOT mark unrelated future requirements complete merely because shared infrastructure was added, and MUST recompute compliance from verifier evidence after each merged change; acceptance evidence is shared-infrastructure, unrelated-requirement, and post-merge recomputation fixtures.

`REQ-AUTO-044` — A change to a direct dependency version, transitive lock result, vendored snapshot, external executable pin, VFPX corpus pin, or generated wheelhouse MUST be treated as a dependency-boundary change and MUST regenerate provenance, license inventory, SBOM/dependency inventory, compatibility evidence, affected differential tests, and cumulative release regressions before integration; acceptance evidence is direct-update, transitive-update, vendored-update, corpus-update, and unreviewed-lock-change fixtures.

`REQ-AUTO-045` — Dependency update automation MUST distinguish compatibility-range eligibility from approval to adopt a new resolved artifact, MUST reject unexpected origin or integrity changes even when the version string is acceptable, and MUST preserve the previously qualified lock when candidate update verification fails; acceptance evidence is same-version-different-hash, wrong-origin, failed-upgrade-rollback, and successful-update fixtures.

`REQ-AUTO-046` — Every retained evidence artifact MUST declare a sensitivity class and redaction policy, public CI/release evidence MUST exclude original DBF/Memo values, credentials, recovery material, sensitive absolute paths, and private application source unless the artifact class explicitly authorizes secure local retention, and publication automation MUST run canary leakage scans over the complete evidence/release bundle before upload; acceptance evidence is public-safe, secure-local, misclassified-sensitive, and leakage-blocking fixtures.

`REQ-AUTO-047` — Under `PUBLICATION` scope, every public release MUST produce a cryptographically verifiable provenance attestation from the trusted release workflow or an equivalent protected signing identity that binds the release version, qualified-release identity, canonical integrated Git commit, Source of Truth hash, dependency-lock hash, package hashes, SBOM/dependency inventory hash, and release-gate result, and ordinary coding-agent credentials MUST be unable to create a trusted attestation; acceptance evidence is valid-attestation, tampered-artifact, wrong-qualification, wrong-commit, wrong-SOT, and untrusted-signer tests.

`REQ-AUTO-048` — An independent correctness, architecture, or security review MUST be produced by a reviewer execution of class `HUMAN`, `MODEL`, `DETERMINISTIC_TOOL`, or `COMPOSITE` that did not author or modify the candidate change, receives the candidate diff and hash-bound requirement context independently, cannot convert deterministic verifier failures to PASS, records reviewer class plus a class-appropriate opaque identity/profile and reviewed commit/tree, records the effective model-routing snapshot/role when model-assisted, and satisfies `REQ-G00-057` plus `REQ-G00-069` when applicable; acceptance evidence is human-review, deterministic-tool-review, independent-model-review-with-route, builder-self-review refusal, reviewer-modifies-candidate refusal, stale-commit review, deterministic-failure-override refusal, composite-review, routing-change invalidation, and valid manual/autonomous/hybrid independent-review fixtures.

`REQ-AUTO-049` — Requirement evidence used by the compliance store MUST be freshness-bound to the evaluated Git commit or immutable artifact hash, Source of Truth hash, requirement-graph hash, verification-manifest hash, dependency-lock identity, effective configuration/policy identity, fixture/corpus identities, and relevant trusted-host capability identity, and any changed bound input MUST invalidate or force regeneration of affected PASS evidence before it can satisfy a merge or release closure; acceptance evidence is stale-commit, changed-SOT, changed-verifier, changed-lock, changed-policy, changed-fixture, changed-trusted-host, and unchanged-input reuse fixtures.

`REQ-AUTO-050` — Under `PUBLICATION` scope, every public release MUST publish or retain in a content-addressed immutable provenance bundle the exact frozen `spec/SOURCE_OF_TRUTH.md` bytes plus the canonical requirement graph, verification manifest, release-gate manifest, compatibility manifest, acquisition manifest, dependency lock, threat model, execution-profile snapshot, relevant `spec/schemas/` documents, qualified-release record, and release-attestation payload whose hashes are recorded by the release, so an auditor can reconstruct the executable contract without depending on chat history, a mutable branch, renamed tool-native files, or an external file that can disappear; acceptance evidence is clean-offline provenance-bundle reconstruction from canonical artifacts, qualification-binding, missing-member, wrong-hash, wrong-SOT-bytes, renamed-only-native-artifact, and mutable-reference-only failure tests.

`REQ-AUTO-051` — Every successful release qualification MUST create an immutable machine-readable qualified-release record containing release version, operation scope, authoring mode, clean local target commit/tree, Source of Truth hash, requirement-graph hash, verification-manifest hash, dependency-lock identity, release-gate-manifest hash, package/artifact hashes, contract-snapshot hash, cumulative predecessor-qualified identity, verifier evidence roots, independent-review evidence roots with reviewer classes, authoring/controller provenance roots, model-routing snapshot identities for model-derived work when present, and qualification result, while publication status is represented only by separate publication receipts and MUST NOT mutate the qualified-release record; acceptance evidence is first-qualified-release, manual-no-model-qualified-release, autonomous-qualified-release-with-routing, hybrid-qualified-release, chained-qualified-predecessor, immutable-record, separate-publication-receipt, and changed-input-new-identity tests.

`REQ-AUTO-052` — Release qualification, cumulative regression, upgrade qualification, and performance comparison MUST use the immediately preceding qualified release record in the canonical semantic-version lineage rather than require that predecessor to have been publicly published, and a later public publication MUST reference exactly the already-qualified artifact/contract identities instead of causing requalification with different bytes; acceptance evidence is multi-release-local-lineage through `1.0.0`, unpublished-qualified-predecessor upgrade/performance tests, later-publication identity equality, and divergent-publication-artifact refusal.

`REQ-AUTO-053` — Before remote integration, the trusted integration layer MUST perform a read-only repository-policy preflight for the exact canonical destination and effective `target_ref` and classify the integration mode as `NATIVE_PROTECTED` when authoritative branch protection or ruleset controls apply, `TRUSTED_UNPROTECTED` when authoritative evidence shows no such protection applies, or `POLICY_UNKNOWN` when the policy state cannot be established; both `NATIVE_PROTECTED` and `TRUSTED_UNPROTECTED` are valid supported modes, `POLICY_UNKNOWN` MUST block remote integration but MUST NOT block `LOCAL_QUALIFICATION`, and the preflight MUST record remote-head identity, protection/ruleset evidence, and the authorization identity used for subsequent remote mutation; acceptance evidence is protected-main, unprotected-main, ruleset-protected, unreadable-policy, wrong-destination, and local-qualification-despite-policy-unknown fixtures.

`REQ-AUTO-054` — In `NATIVE_PROTECTED` mode, the trusted integration layer MUST satisfy the repository's active native protection/ruleset constraints in addition to Source of Truth gates and MUST allow the platform to create a policy-derived merge, squash, or rebase integration commit only when the candidate/base relation is fully recorded and the resulting commit is handled by `REQ-AUTO-055`; in `TRUSTED_UNPROTECTED` mode, the trusted integration layer MUST verify the exact remote base commit, gates, independent reviews, and required remote CI before performing a non-force fast-forward update to the verified candidate whose base is the verified remote head, and any intervening remote-head change MUST invalidate integration evidence and require re-evaluation on the new base; neither mode can grant direct remote-write credentials to the coding agent; acceptance evidence is protected-merge, protected-squash, protected-rebase, unprotected-fast-forward, non-fast-forward refusal, concurrent-update refusal, native-policy-bypass refusal, and coding-agent-credential-boundary tests.

`REQ-AUTO-055` — Every remote integration MUST classify the final candidate-to-integration relation as `IDENTITY_FAST_FORWARD`, `TREE_EQUIVALENT_DERIVED`, or `TREE_CHANGED_DERIVED`: `IDENTITY_FAST_FORWARD` requires the final remote commit to equal the verified candidate; `TREE_EQUIVALENT_DERIVED` permits a different merge/squash/rebase commit only when its Git tree equals the verified candidate tree and post-integration deterministic checks confirm the same requirement/contract state; `TREE_CHANGED_DERIVED` requires full post-integration deterministic verification of the final tree and invalidates any candidate-qualified release identity for publication until the final integrated tree is qualified again; publication can reuse candidate-qualified artifacts after `TREE_EQUIVALENT_DERIVED` only when normalized rebuilds from the integrated commit reproduce the same artifact hashes and no qualification input other than commit identity changed; acceptance evidence is fast-forward identity, protected merge/squash/rebase tree-equivalence, changed-base derived-tree requalification, artifact-hash equality, commit-sensitive-build refusal, and stale-candidate-qualification publication refusal tests.

## Phase 3 — VFPX VFP9 SP2 offline knowledge system

`REQ-P03-001` — The repository MUST contain or reproducibly generate an offline normalized knowledge corpus from the pinned VFPX HelpFile `sources/dv_foxhelp` source tree, including HTML topics and HHC/HHK navigation/index metadata, with no live website dependency at request time; acceptance evidence is a deterministic corpus build and offline search test.

`REQ-P03-002` — Every normalized help topic MUST retain upstream file identity, VFPX commit, HelpFile version, title, aliases/index keywords, hierarchy, cleaned searchable text, code examples, cross-links, source hash, and local citation locator; acceptance evidence is topic-schema snapshots and source-to-topic traceability tests.

`REQ-P03-003` — The knowledge normalizer MUST identify commands, functions, system variables, properties, methods, events, base classes, controls, object members, file-format topics, DBC/data topics, index/Rushmore topics, build/runtime topics, and error messages from the VFP9 SP2 corpus without importing a separate older-version grammar; acceptance evidence is category coverage fixtures.

`REQ-P03-004` — The knowledge catalog MUST classify each topic as `VFP9SP2_CANONICAL`, `VFP9SP2_BACKWARD_COMPATIBLE`, `VFP9SP2_SEDNA_OR_EXTENSION`, or `REFERENCE_GENERAL` based only on evidence present in the pinned VFPX corpus; acceptance evidence is classification fixtures and unknown-state handling.

`REQ-P03-005` — The parser and refactoring subsystems MUST resolve syntax and object/member questions against `VFP9SP2_CANONICAL` knowledge first, MUST consult VFP9-SP2-documented backward-compatible topics only when source evidence or explicit compatibility analysis calls for them, and MUST exclude Sedna or extension topics from validating or generating core VFP9 SP2 behavior unless the analyzed project or runtime profile explicitly proves that extension is present; acceptance evidence is lookup-priority, compatibility-topic, and extension-exclusion tests.

`REQ-P03-006` — The knowledge service MUST expose exact-title lookup, alias/index lookup, full-text search, symbol/member search, error-code lookup, related-topic traversal, and topic retrieval with bounded excerpts and local source citations; acceptance evidence is deterministic retrieval tests over commands, functions, controls, methods, properties, and file structures.

`REQ-P03-007` — The semantic analyzer MUST be able to attach relevant VFP9 SP2 help-topic IDs to source constructs, findings, form members, DBC objects, index expressions, runtime errors, and refactor decisions so an MCP client can explain why a construct is valid or risky; acceptance evidence is cross-link fixtures from code/form/data findings to knowledge topics.

`REQ-P03-008` — The corpus build MUST emit a completeness manifest covering expected topic/index/navigation inputs, parse failures, duplicate titles, unresolved links, and category counts, and a materially incomplete corpus MUST downgrade knowledge-dependent analysis instead of silently appearing complete; acceptance evidence is broken-corpus tests.

`REQ-P03-009` — The local knowledge index MUST be immutable during normal MCP operation and MUST record its generator version and content fingerprint in every project audit snapshot that relies on documentation evidence; acceptance evidence is knowledge-fingerprint propagation tests.

## Phase 4 — DBF/FPT data plane for original and anonymized datasets

`REQ-P04-001` — The data plane MUST read Visual FoxPro DBF tables both with and without FPT memo companions through dbfbridge and MUST treat memo presence, memo absence, missing memo, invalid memo pointer, corrupt memo block, and non-text binary/general content as distinct machine-readable states; acceptance evidence is table fixtures for each state.

`REQ-P04-002` — The data plane MUST support original, anonymized, and workspace DBF/FPT trees with identical public query schemas while keeping dataset role and lineage in every value-bearing result; acceptance evidence is the same query suite run against paired original and pseudonymized datasets.

`REQ-P04-003` — DBF schema inspection MUST expose field order, name, VFP type, width, decimals, nullable state where available, code-page evidence, memo association, record count, deleted-state support, structural CDX/IDX companion presence, and source hashes; acceptance evidence is schema snapshots covering every VFP field type declared supported by the synthetic-fixture coverage matrix.

`REQ-P04-004` — Record reading MUST preserve VFP logical values, dates, datetimes, numeric precision, NULL versus empty distinctions, deleted-record identity, memo text, and raw-record provenance supported by dbfbridge without inventing values for undecodable or binary content; acceptance evidence is value-fidelity fixtures and dbfbridge round-trip checks.

`REQ-P04-005` — Value-bearing data tools MUST be available as a core local-server capability for allowed dataset roots rather than being excluded from the product, while logs, progress events, caches, and unrelated audit reports MUST remain value-redacted; acceptance evidence is successful bounded value queries plus whole-log canary leakage tests.

`REQ-P04-006` — Table scans MUST support deterministic pagination, selected columns, deleted-record policy, NULL policy, stable record locators, memo inclusion policy, and response byte limits; acceptance evidence is pagination/no-duplication tests over large memo and non-memo tables.

`REQ-P04-007` — The service MUST support exact and case-aware text search across Character and Memo fields, including bounded substring search and regular-expression search with timeout/resource limits, while preserving code-page provenance; acceptance evidence is cp1250/cp852/Mazovia-compatible text and memo search fixtures.

`REQ-P04-008` — The table profiler MUST compute record counts, deleted counts, NULL/empty counts, min/max for safe scalar types, length statistics, exact or bounded distinct counts, frequency summaries, candidate-key evidence, duplicate evidence, and memo-size statistics without requiring the entire table in RAM; acceptance evidence is streaming-memory tests and deterministic profiles.

`REQ-P04-009` — The query subsystem MUST support large datasets with bounded memory through streaming reads and an ephemeral spill-to-disk relational workspace, preserving source record locators so query results remain traceable to DBF records; acceptance evidence is a multi-table dataset larger than the configured memory threshold.

`REQ-P04-010` — Missing or damaged companion files MUST produce `PARTIAL` or `FAIL` according to the requested operation and MUST never cause silent omission of memo-dependent data from an answer; acceptance evidence is missing/corrupt FPT and companion-recovery fixtures.

`REQ-P04-011` — The data plane MUST provide schema and statistical comparison between two dataset IDs, including original-versus-anonymized comparison of schema, record/deleted counts, NULL/empty distributions, scalar summaries, memo-size summaries, and other Phase-4-available profile evidence while avoiding recovery-vault access and reverse-identity disclosure; relationship/key semantics not yet available from later phases MUST remain explicitly unavailable rather than being fabricated; acceptance evidence is paired-dataset schema/count/distribution comparison plus an expected-unavailable later-relation check.

`REQ-P04-012` — The MCP server MUST expose the implemented dataset registration, table schema, bounded row reading, profiling, value search, and VFP9-SP2 Help operations as soon as their Core contracts pass, without waiting for semantic-graph or PostgreSQL phases; acceptance evidence is an official MCP client data-explorer scenario over DBF-only and DBF+FPT fixtures.

`REQ-P04-013` — Cross-table queries, relationship profiling, migration planning, and any operation that combines DBF with FPT, CDX/IDX, DBC companions, or multiple tables MUST use an explicit consistency mode, with `SNAPSHOT_CONSISTENT` as the default for correctness-sensitive operations and `LIVE_BEST_EFFORT` permitted only when the caller explicitly accepts possible concurrent source changes; acceptance evidence is consistency-mode schema tests and concurrent-writer fixtures.

`REQ-P04-014` — A `SNAPSHOT_CONSISTENT` dataset snapshot MUST copy or otherwise freeze the complete required companion-file closure into an isolated read-only analysis snapshot, fingerprint files before and after acquisition, retry or fail when source mutation is detected, and never combine DBF records from one source moment with Memo or index/container evidence from another; acceptance evidence is concurrent DBF/FPT/CDX mutation tests and cross-file fingerprint assertions.

`REQ-P04-015` — File sharing violations, locked files, transient access denial, truncated live files, changing record counts, changing FPT blocks, and changing companion sets MUST produce typed consistency/access outcomes with bounded retry policy rather than partial silent answers; acceptance evidence is Windows file-sharing, lock, truncation, mutation, and retry-exhaustion fixtures.

`REQ-P04-016` — Every data-bearing result MUST identify the dataset snapshot or live-consistency token from which it was computed so later relation, query, optimization, anonymization, and PostgreSQL migration evidence cannot be combined across incompatible source states without an explicit comparison operation; acceptance evidence is stale-snapshot and cross-snapshot mixing rejection tests.

`REQ-P04-017` — Raw values from an `ORIGINAL` dataset MUST enter MCP responses or question-context evidence only through an explicitly value-bearing operation and an effective host/dataset exposure policy, every returned value-bearing fragment MUST retain dataset role and snapshot identity, and automatic context assembly MUST support schema/statistics-only or anonymized-value modes so unrelated model prompts do not receive original values by default; acceptance evidence is explicit-original-value, denied-original-value, anonymized-context, schema-only-context, and role-tag propagation tests.

## Release Gate 0.4.0 — Windows VFP Data & Help Explorer

`REQ-R01-001` — Release `0.4.0` MUST be publishable and practically usable on Windows only after the exact canonical `0.4.0` release closure defined by the Source of Truth passes, providing MCP capability discovery, project/dataset registration, VFPX VFP9 SP2 Help search, DBF schema inspection, DBF/FPT row and Memo reading, profiles, bounded value search, jobs/cancellation, source immutability, and Windows path policy; acceptance evidence is a clean-wheel offline Windows MCP session against representative original and anonymized datasets.

`REQ-R01-002` — Release `0.4.0` MUST pass its machine-readable release-gate manifest, the complete deterministic regression profile for its prerequisite closure, every earlier qualified-release smoke/compatibility suite, clean-wheel Windows installation, official MCP client smoke testing, expected-unavailable future-capability checks, artifact/qualification-provenance validation, and generation of an immutable qualified-release record before the release task can be PASS; acceptance evidence is the retained release-gate report bound to Source of Truth SHA, exact clean local target commit/tree, package hash, verifier/review evidence roots, and qualified-release identity, while remote CI/merge/publication identities are required only when the active operation scope makes them applicable.

`REQ-R01-003` — Release `0.4.0` MUST execute the greenfield scenario defined by `REQ-G00-015` from a completely empty repository through B0 and the exact `0.4.0` release closure in the selected authoring mode with no undeclared bootstrap artifact; `AUTONOMOUS` execution MUST contain no direct human source-code editing, while `MANUAL` and `HYBRID` execution MUST retain the authoring provenance required by `REQ-G00-055`, and the produced package MUST pass the same clean-wheel MCP Data & Help Explorer acceptance as the ordinary release candidate; acceptance evidence is a retained empty-repository-to-0.4.0 execution manifest bound to Source of Truth, requirement graph, execution profile, authoring mode, qualified commit/tree, and package hashes.

## Phase 5 — VFP artifacts, lexical parser and whole-application semantic graph

`REQ-P05-001` — The artifact scanner MUST inventory and correlate `DBF/FPT/CDX/IDX`, `SCX/SCT`, `VCX/VCT`, `FRX/FRT`, `LBX/LBT`, `MNX/MNT`, `PJX/PJT`, `DBC/DCT/DCX`, `PRG`, `H`, `MPR`, `FPW`, and detected COM/OCX/DLL/FLL/executable references using normalized Windows paths and SHA-256 identities; acceptance evidence is the multi-artifact synthetic-fixture matrix and deterministic manifest snapshots for every declared artifact family.

`REQ-P05-002` — Pure table-based artifact readers MUST reuse the dbfbridge record boundary and artifact-specific normalization, and unknown or binary fields MUST remain typed opaque data with size/hash instead of fabricated VFP source text; acceptance evidence is binary-canary fixtures across designer families.

`REQ-P05-003` — The text lexer MUST correctly separate executable code from comments, strings, bracket literals, line continuations, preprocessor regions, `TEXT...ENDTEXT`, name expressions, macro substitution, and embedded SQL so later analysis does not create symbol/reference facts from inert text; acceptance evidence is adversarial lexical fixtures with exact spans.

`REQ-P05-004` — The semantic parser MUST model VFP9 SP2 procedures, functions, parameters, locals/public/private variables, classes, methods, properties, events, preprocessor symbols, aliases, table/field references, commands, functions, method/property access, and error-handling constructs with source spans; acceptance evidence is AST/semantic snapshots.

`REQ-P05-005` — The call and dependency graph MUST capture direct calls, `DO`/`DO FORM`, method calls, class creation, `SET PROCEDURE`, `SET CLASSLIB`, includes, project membership, report/menu execution, external binaries, and unresolved dynamic targets, with uncertain dynamic edges explicitly typed; acceptance evidence is direct/dynamic graph fixtures.

`REQ-P05-006` — The data-flow model MUST track work areas and aliases sufficiently to correlate `USE`, `SELECT`, `SET RELATION`, `SET ORDER`, `SEEK`, `LOCATE`, `SCAN`, `REPLACE`, aggregates, `SELECT-SQL`, local/remote views, SQL Pass-Through, CursorAdapter, and DataEnvironment cursor use with table/field identities; acceptance evidence is scenario traces.

`REQ-P05-007` — The application-lifecycle model MUST identify PJX main-program evidence, startup PRGs, CONFIG.FPW effects, procedure/class libraries, `READ EVENTS`/`CLEAR EVENTS`, form entry points, shutdown paths, and deployment/build dependencies while preserving unresolved dynamic lifecycle branches; acceptance evidence is lifecycle fixtures.

`REQ-P05-008` — The external-dependency analyzer MUST inventory COM/OLE/ActiveX identifiers, OCX controls, DECLARE-DLL/native calls, FLL/DLL references, filesystem paths, executable launches, automation servers, and remote connection endpoints without contacting those endpoints; acceptance evidence is dependency fixtures and zero-network sentinels.

`REQ-P05-009` — The semantic graph MUST store artifacts, modules, procedures, functions, classes, forms, controls, methods, properties, events, tables, fields, aliases, DBC objects, views, connections, indexes, external components, findings, and knowledge topics as typed nodes with typed evidence-bearing edges; acceptance evidence is a versioned graph schema plus graph snapshots over the multi-artifact synthetic-fixture matrix.

`REQ-P05-010` — Project completeness MUST be computed per detected domain and MUST distinguish `COMPLETE`, `PARTIAL`, `HEURISTIC`, `UNKNOWN`, `NOT_IMPLEMENTED`, and `NOT_APPLICABLE`, with top-level completeness blocked by any relevant incomplete domain; acceptance evidence is completeness fixtures.

`REQ-P05-011` — The service MUST support bounded graph queries by node kind, identity, name, source location, dependency direction, relation path, and neighborhood depth so MCP clients can answer dependency questions without downloading the entire graph; acceptance evidence is pagination and graph-slice tests.

`REQ-P05-012` — Incremental project re-indexing MUST use source/artifact fingerprints and dependency invalidation so unchanged artifacts can be reused while every changed artifact and every graph/model result transitively dependent on it is recomputed, and uncertainty in dependency impact MUST fall back to broader recomputation rather than stale reuse; acceptance evidence is changed-leaf, changed-shared-dependency, deleted-file, renamed-file, and uncertain-impact fixtures.

`REQ-P05-013` — Incremental semantic indexing MUST be observationally equivalent to a clean full rebuild for the same project snapshot, configuration, knowledge corpus, and dependency identities, including stable IDs, completeness states, relation evidence, and graph queries; acceptance evidence is differential incremental-versus-full-rebuild tests over multi-step edit sequences.

`REQ-P05-014` — The semantic model MUST track the effective VFP data-access environment and its provenance, including relevant CONFIG.FPW and source/runtime changes to `SET EXACT`, `SET ANSI`, `SET COLLATE`, `SET DELETED`, `SET NEAR`, `SET NULL`, `SET DATE`, `SET CENTURY`, `SET ENGINEBEHAVIOR`, `SET OPTIMIZE`, and `SET MULTILOCKS`, and dynamic or unresolved changes MUST remain explicit unknown state rather than assumed defaults; acceptance evidence is startup/config/runtime-change traces and ambiguous-dynamic-setting fixtures.

## Phase 6 — FoxBin2Prg and authoritative VFP9 SP2 backend

`REQ-P06-001` — FoxBin2Prg analysis conversion MUST run against a scratch or workspace copy of complete artifact companion sets rather than writing generated SC2/VC2/PJ2/DC2/other text beside immutable source artifacts; acceptance evidence is source-tree timestamp/hash sentinels during BIN2PRG.

`REQ-P06-002` — The FoxBin2Prg adapter MUST support the bidirectional pairs PJX/PJ2, SCX/SC2, VCX/VC2, FRX/FR2, LBX/LB2, DBC/DC2, DBF/DB2, and MNX/MN2 exposed by the pinned integration baseline and MUST report unsupported/failed conversion explicitly; acceptance evidence is conversion fixtures for each used family.

`REQ-P06-003` — The FoxBin2Prg adapter MUST use a pinned deterministic configuration derived from repository-controlled settings, record the effective configuration with each conversion, and reject an unexpected executable/source origin; acceptance evidence is configuration fingerprint and origin-verification tests.

`REQ-P06-004` — The VFP9 backend MUST discover configured VFP availability and exact version/build without launching a mutable project session during basic capability discovery, and older Visual FoxPro major/minor versions MUST never satisfy the VFP9 SP2 refactor/build capability; acceptance evidence is version-probe fixtures.

`REQ-P06-005` — Known VFP9 SP2 builds 9.0.0.5815 and 9.0.0.7423 MUST be recognized explicitly, and an unrecognized VFP9 build MUST remain visible as unknown rather than being silently labeled as either known baseline; acceptance evidence is build-classification tests.

`REQ-P06-006` — VFP execution MUST use supervised owned workers in which each worker owns one VFP9 automation process, runs one job at a time, initializes a deterministic environment, clears project/work-area state between jobs, recycles on contamination/failure, and never kills unrelated interactive `vfp9.exe` processes; acceptance evidence is worker-isolation tests.

`REQ-P06-007` — The enhanced backend MUST expose authoritative runtime CDX/tag and DBC metadata, including available tag names/expressions/orders and container/runtime metadata, while preserving a distinction from pure-parser or heuristic facts; acceptance evidence is trusted-host comparison fixtures.

`REQ-P06-008` — The enhanced backend MUST expose controlled runtime language/object inventory using VFP9 SP2 probes such as `ALANGUAGE()` and `AMEMBERS()` where relevant and MUST attach runtime build/probe provenance to the result; acceptance evidence is JSON-safe inventory snapshots.

`REQ-P06-009` — Rushmore/runtime query evidence MUST be collectable through `SYS(3054)` and controlled benchmark scripts with exact input/query/context/source hashes, and runtime-generated temporary files MUST stay outside immutable project roots; acceptance evidence is trusted-host profiling fixtures.

`REQ-P06-010` — Compiler and build validation MUST run only in explicit workspaces/scratch areas and MUST expose structured diagnostics for every supported target kind among PRG, form/class, project, APP, EXE, and DLL without altering original project files; acceptance evidence is valid and invalid compile/build fixtures for every target kind declared supported by the capability manifest.

`REQ-P06-011` — Where pure parsing, FoxBin2Prg, VFP runtime, and VFPX Help evidence overlap, the service MUST compare normalized facts, store agreement/disagreement explicitly, and prefer an authoritative source only for the dimensions actually verified by that source; acceptance evidence is matched and intentionally divergent conformance fixtures.

`REQ-P06-012` — The architecture MUST keep Python process architecture independent from legacy component architecture by using supervised out-of-process boundaries whenever an in-process 32-bit VFP/COM/ODBC/OCX/FLL/DLL dependency is incompatible with the main Python process, and capability discovery MUST report the effective architecture path instead of attempting to load architecture-incompatible components into one process; acceptance evidence is 64-bit-Python/32-bit-VFP, matching-architecture helper, incompatible-in-process refusal, and capability-report fixtures.

`REQ-P06-013` — Autonomous VFP9/FoxBin2Prg workers MUST operate without requiring interactive desktop decisions, MUST detect timeout or modal-dialog/hung-automation conditions, MUST capture deterministic diagnostics where possible, MUST terminate or recycle only the owned worker process under supervisor policy, and MUST NOT use global keystroke/UI automation to dismiss unknown dialogs; acceptance evidence is compile error, intentional modal dialog, hung automation, timeout, owned-process cleanup, and unrelated-interactive-VFP preservation tests.

`REQ-P06-014` — The trusted VFP9 SP2 runtime profile MUST discover the Windows session ID, window-station/desktop visibility, and user-interactive state before launching VFP COM or FoxBin2Prg operations that can surface GUI or modal UI, MUST reject Session 0 or another non-interactive desktop as incapable of satisfying trusted VFP automation, and MUST execute such workers in an explicitly provisioned logged-on interactive user session under the supervisor timeout/modal-detection rules without weakening `REQ-P06-013`; acceptance evidence is interactive-session success, Session-0 refusal, invisible-window-station refusal, modal-dialog timeout/recycle, and unrelated-interactive-process preservation tests.

`REQ-P06-015` — The FoxBin2Prg adapter MUST bind each conversion to explicit source text/code-page provenance derived from the project and table metadata available for the affected artifact set, MUST generate or select only repository-controlled FoxBin2Prg/VFP execution settings that preserve that provenance, MUST record the effective settings and detected code-page context with each BIN2PRG/PRG2BIN cycle, and MUST fail refactor or round-trip validation when Polish or other non-ASCII text changes unexpectedly; acceptance evidence is cp1250, cp852, Mazovia-compatible, mixed-code-page, wrong-configuration, and SCX/VCX text-fidelity round-trip fixtures.

## Phase 7 — Deep form and class analysis

`REQ-P07-001` — Form analysis MUST cover SCX/SCT forms and formsets plus VCX/VCT classes and MUST merge pure table evidence with FoxBin2Prg canonical SC2/VC2 evidence when available without changing public model shapes; acceptance evidence is dual-backend form fixtures.

`REQ-P07-002` — The normalized form model MUST represent object hierarchy, base class, class library, object names, control classes, dimensions/positions, relevant properties, methods/events, contained controls, pageframes/pages, grids/columns, command groups, data-bound controls, and binary/opaque property payloads with provenance; acceptance evidence is structural form snapshots.

`REQ-P07-003` — The class model MUST represent inheritance chains across VCX/VCT and PRG-defined classes, inherited versus overridden properties/methods, class-library dependencies, and unresolved base classes; acceptance evidence is multi-level inheritance fixtures.

`REQ-P07-004` — The form-code analyzer MUST parse method and event code into the same VFP9 SP2 semantic model as PRG source and MUST connect calls, table access, field access, class usage, globals, and external dependencies back to the owning form object and method; acceptance evidence is method-level graph assertions.

`REQ-P07-005` — The DataEnvironment analyzer MUST model cursors, aliases, tables/views, relations, orders, filter/expression properties, buffering-related settings, and form/control bindings, and MUST connect them to the database relation graph; acceptance evidence is DataEnvironment fixtures with bound controls.

`REQ-P07-006` — The control-binding analyzer MUST identify ControlSource, RecordSource, RowSource, relational/list sources, calculated expressions, dynamic properties, and source-code assignments where resolvable, with explicit unresolved states for dynamic expressions; acceptance evidence is binding fixtures.

`REQ-P07-007` — The form analyzer MUST identify duplicate or near-duplicate methods, oversized event handlers, repeated table-access patterns, excessive Refresh/Timer/Paint work, fragile macro/dynamic code, hidden cross-form coupling, undeclared globals, and class-inheritance duplication as evidence-backed refactoring candidates rather than automatic defects; acceptance evidence is candidate-detection fixtures.

`REQ-P07-008` — The form analyzer MUST expose object-level and method-level impact analysis showing callers, callees, data dependencies, field bindings, class dependencies, project entry points, and downstream forms/reports that could be affected by a change; acceptance evidence is dependency-slice tests.

`REQ-P07-009` — The form service MUST expose bounded inspection and search by form/class name, object path, control type, property, method/event, referenced table/field, called procedure/class, and finding kind; acceptance evidence is query fixtures across several forms.

`REQ-P07-010` — The form analysis result MUST link relevant object members and syntax constructs to pinned VFP9 SP2 Help topics so a client can answer questions about a property, event, control, class, or method with exact local documentation evidence; acceptance evidence is form-to-help cross-link tests.

## Phase 8 — DBC, views and unified application data model

`REQ-P08-001` — DBC analysis MUST normalize tables, fields, indexes, relations, stored procedures, triggers/rules/defaults where available, connections, local views, remote views, and object identities from pure file evidence plus VFP runtime enrichment; acceptance evidence is the DBC synthetic-fixture matrix covering tables, relations, rules, triggers, stored procedures, local views, remote views, connections, and malformed or opaque cases.

`REQ-P08-002` — Stored-procedure and expression text recovered from DBC evidence MUST enter the same VFP9 SP2 lexical/semantic analysis pipeline as PRG/form code with source provenance identifying the DBC object; acceptance evidence is DBC-code symbol/reference fixtures.

`REQ-P08-003` — Local and remote view analysis MUST identify source tables, selected fields, joins, filters, update rules where recoverable, connection dependencies, and source-code consumers, with unresolved dynamic SQL explicitly represented; acceptance evidence is view dependency fixtures.

`REQ-P08-004` — Connection analysis MUST inventory connection names, endpoint/server/database metadata that is safe to expose, authentication mode indicators where available, and source consumers without returning stored passwords or secrets; acceptance evidence is redaction fixtures.

`REQ-P08-005` — CursorAdapter and SQL Pass-Through analysis MUST identify creation/configuration, SelectCmd/UpdateCmd/InsertCmd/DeleteCmd or SPT SQL, connection usage, cursor schema/use, and surrounding transaction/error handling where statically resolvable; acceptance evidence is source/form fixtures.

`REQ-P08-006` — The unified application data model MUST connect DBC metadata, DBF schemas, DataEnvironment cursors, views, CursorAdapters, SPT, work-area access, relations, indexes, control bindings, and value-profile evidence into one queryable graph; acceptance evidence is cross-layer path queries.

`REQ-P08-007` — Impact analysis MUST be able to answer which forms, methods, reports, menus, procedures, views, indexes, and data bindings depend on a selected table, field, relation, view, class, or form object; acceptance evidence is forward/reverse dependency queries.

`REQ-P08-008` — The runtime DBC/CDX interpretation MUST be compared with pure interpretation and disagreements MUST be surfaced as conformance findings rather than silently replaced; acceptance evidence is intentional mismatch fixtures.

## Phase 9 — Structured questions, joins, relationships and dependency reasoning

`REQ-P09-001` — The Core Service MUST expose a structured read-only data-query model supporting table selection, projection, filters, boolean expressions, sorting, limits, grouping, aggregates, distinct values, joins, and relation-path traversal without accepting arbitrary shell commands or VFP write statements; acceptance evidence is JSON Schema and query-planner tests.

`REQ-P09-002` — The data-query engine MUST support Character and Memo predicates, numeric/date/datetime comparisons, logical predicates, NULL/empty predicates, deleted-record policy, bounded `IN` lists, and safe pattern matching with deterministic result semantics documented independently from VFP execution semantics; acceptance evidence is operator fixtures.

`REQ-P09-003` — The relational query engine MUST support joins across DBF tables using declared DBC relations, source-derived relations, user-selected keys, and inferred high-confidence relations, and every joined result MUST identify which relation evidence was used; acceptance evidence is declared, inferred, and explicit-key join fixtures.

`REQ-P09-004` — The application model MUST distinguish `DECLARED`, `SOURCE_OBSERVED`, `INFERRED_HIGH`, `INFERRED_LOW`, and `USER_SPECIFIED` relationship provenance so a client can explain certainty rather than presenting every inferred link as a schema fact; acceptance evidence is relation-provenance snapshots.

`REQ-P09-005` — The relation inference engine MUST combine field names/types/widths, uniqueness, index expressions, DBC metadata, source join/seek/relation usage, and optional value-overlap/orphan evidence while keeping probabilistic inference separate from authoritative metadata; acceptance evidence is positive, ambiguous, and false-friend datasets.

`REQ-P09-006` — The server MUST expose relation explanation that reports endpoints, fields/expressions, cardinality evidence, indexes, source references, DBC references, overlap/orphan statistics where computed, and confidence; acceptance evidence is human-readable and machine-readable explanation snapshots.

`REQ-P09-007` — The service MUST expose dataset-aware value search that can locate a supplied value or pattern across selected tables/fields, including memo fields, with strict result/byte limits and explicit dataset role; acceptance evidence is multi-table search across original and anonymized datasets.

`REQ-P09-008` — The service MUST expose `question context` retrieval that accepts a natural-language question and returns ranked project, table, field, relation, form, source, finding, and VFP9-SP2-help evidence for an external MCP client model to compose the final answer, without requiring a second embedded LLM inside the server; acceptance evidence is deterministic retrieval fixtures for data, form, and code questions.

`REQ-P09-009` — The query planner MUST emit an explainable plan showing selected datasets, tables, indexes or scan strategy where known, relation path, filters, projections, aggregates, row/byte caps, and whether VFP runtime confirmation is involved; acceptance evidence is plan snapshots before execution.

`REQ-P09-010` — The VFP runtime backend MUST be able to confirm selected read-only data questions or expression semantics under VFP9 SP2 in a controlled read-only context when neutral query semantics are insufficient, and confirmed results MUST be labeled separately from pure-query results; acceptance evidence is cross-engine fixtures.

`REQ-P09-011` — Every data answer payload MUST retain source dataset ID, table identity, field identities, record locators or aggregate provenance, relation evidence, and query-plan identity so the external model can cite where an answer came from; acceptance evidence is traceability tests from result cells/aggregates back to source metadata.

`REQ-P09-012` — The MCP server MUST expose the implemented source, symbol, reference, form, DBC, relation, impact, graph-query, and question-context operations after this phase without waiting for performance, refactoring, privacy, or PostgreSQL delivery; acceptance evidence is an official MCP client application-analysis scenario.

## Release Gate 0.5.0 — VFP Application Analyzer

`REQ-R02-001` — Release `0.5.0` MUST be publishable and practically usable on Windows only after the exact canonical `0.5.0` release closure defined by the Source of Truth passes, providing whole-project source analysis, symbols/references, FoxBin-backed forms/classes, DataEnvironment, DBC/views/connections, dependency and impact graphs, cross-table relations, structured joins, and question-oriented evidence over existing VFP applications; acceptance evidence is an offline Windows MCP audit of a synthetic multi-artifact VFP9 SP2 application.

`REQ-R02-002` — Release `0.5.0` MUST pass its machine-readable release-gate manifest, the complete deterministic regression profile for its prerequisite closure, every earlier qualified-release smoke/compatibility suite, clean-wheel Windows installation, official MCP client smoke testing, expected-unavailable future-capability checks, artifact/qualification-provenance validation, and generation of an immutable qualified-release record before the release task can be PASS; acceptance evidence is the retained release-gate report bound to Source of Truth SHA, exact clean local target commit/tree, package hash, verifier/review evidence roots, and qualified-release identity, while remote CI/merge/publication identities are required only when the active operation scope makes them applicable.

## Phase 10 — Performance, indexes and Rushmore

`REQ-P10-001` — The performance analyzer MUST inventory xBase and SQL data-access operations, filters, seeks, scans, aggregates, relation/order changes, buffering/locking/transaction patterns, form Refresh/Timer/Paint work, DataEnvironment startup work, remote-view/SPT/CursorAdapter access, COM crossings, and file/network I/O candidates with source spans; acceptance evidence is pattern fixtures.

`REQ-P10-002` — The index analyzer MUST correlate CDX/IDX runtime and heuristic tag facts with source expressions, seek/order/filter predicates, DBC keys, relation expressions, and data cardinality so exact-match, partial-match, missing-index, and stale/unknown cases are distinct; acceptance evidence is index-expression fixtures.

`REQ-P10-003` — Performance findings MUST use `MEASURED`, `RUNTIME_PLAN_CONFIRMED`, `DOCUMENTED_CANDIDATE`, `PREDICTED`, `NOT_TESTED`, and `REJECTED_CORRECTNESS_RISK`, and no predicted benefit MUST be serialized as measured evidence; acceptance evidence is state-guard tests.

`REQ-P10-004` — The VFP9 SP2 backend MUST support `SYS(3054)` capture for selected safe queries and work-area operations and MUST bind captured optimization evidence to the exact project snapshot, dataset, expression/query, index state, and VFP build; acceptance evidence is trusted-host Rushmore fixtures.

`REQ-P10-005` — The benchmark harness MUST support cold/warm distinctions, repeated timing, bounded iterations, local versus network-path context, exact source/dataset/index fingerprints, and before/after workspace comparison for a proposed optimization; acceptance evidence is machine-readable benchmark snapshots.

`REQ-P10-006` — Performance recommendations that alter code, indexes, form DataEnvironment, or query structure MUST be representable as refactor/optimization plans and MUST pass the same workspace compile/round-trip/correctness validation before promotion; acceptance evidence is one end-to-end performance refactor fixture.

`REQ-P10-007` — Index experiments and REINDEX operations MUST occur only on explicit workspace or anonymized copies, never on immutable original source data during analysis; acceptance evidence is write sentinels and workspace-only index tests.

`REQ-P10-008` — The performance service MUST expose bounded queries by form/method/table/index/finding and provide a concise explanation connecting code location, runtime evidence, index evidence, VFP9 SP2 documentation, and measured or predicted status; acceptance evidence is explanation snapshots.

`REQ-P10-009` — The MCP server MUST expose index, Rushmore, runtime-plan, benchmark, and performance-explanation operations when this phase passes, and every optimization finding MUST remain traceable to source, data/index state, VFP build, and evidence status; acceptance evidence is an official MCP client optimization scenario on a trusted VFP9 SP2 host.

## Release Gate 0.6.0 — VFP Optimization Assistant

`REQ-R03-001` — Release `0.6.0` MUST be publishable and practically usable on Windows only after the exact canonical `0.6.0` release closure defined by the Source of Truth passes, providing CDX/IDX analysis, authoritative VFP runtime evidence, SYS(3054), benchmark support, query/index recommendations, and form/data-access performance findings without requiring controlled refactoring or PostgreSQL migration; acceptance evidence is a trusted-host before/after optimization case with correctness preserved.

`REQ-R03-002` — Release `0.6.0` MUST pass its machine-readable release-gate manifest, the complete deterministic regression profile for its prerequisite closure, every earlier qualified-release smoke/compatibility suite, clean-wheel Windows installation, official MCP client smoke testing, expected-unavailable future-capability checks, artifact/qualification-provenance validation, and generation of an immutable qualified-release record before the release task can be PASS; acceptance evidence is the retained release-gate report bound to Source of Truth SHA, exact clean local target commit/tree, package hash, verifier/review evidence roots, and qualified-release identity, while remote CI/merge/publication identities are required only when the active operation scope makes them applicable.

## Phase 11 — Controlled refactoring of forms, classes and related source

`REQ-P11-001` — Refactoring MUST operate first on an isolated workspace created from an exact immutable source snapshot, and every plan MUST carry pre-change hashes, target artifacts, companion-file closure, intended transformations, invariants, validation steps, and rollback metadata; acceptance evidence is workspace/plan schema tests.

`REQ-P11-002` — The refactor planner MUST support SCX/SCT form changes, VCX/VCT class changes, and directly related PRG/H code changes needed to preserve form behavior, rather than limiting refactoring to textual PRG files; acceptance evidence is multi-artifact plan fixtures.

`REQ-P11-003` — SCX/SCT and VCX/VCT binary refactoring MUST use FoxBin2Prg BIN2PRG to canonical SC2/VC2 text in the workspace, apply structured edits to a parsed canonical representation, and use FoxBin2Prg PRG2BIN to regenerate binary artifacts; acceptance evidence is no-direct-binary-write enforcement and round-trip fixtures.

`REQ-P11-004` — The canonical SC2/VC2 editor MUST represent object boundaries, class/base-class declarations, property assignments, method/event bodies, contained objects, ordering metadata needed for stable regeneration, and unrecognized text blocks without lossy reformatting; acceptance evidence is parse-edit-render idempotence fixtures.

`REQ-P11-005` — The form refactor engine MUST support structured transformations including method-body replacement, method extraction, helper-method introduction, safe method/variable rename with reference updates, property change, control property/binding change, contained-control add/remove/rename, DataEnvironment cursor/relation/property change, and class-library/base-class reference change where validation can prove the result; acceptance evidence is one fixture per transformation family.

`REQ-P11-006` — Every refactor transformation MUST define preconditions and postconditions and MUST refuse an edit when target identity, source hash, semantic reference resolution, or canonical structure is ambiguous; acceptance evidence is ambiguous-target failure fixtures.

`REQ-P11-007` — Reference-aware renames MUST update resolvable form methods, PRG methods/functions, control/object references, class references, and source call sites across the project graph while leaving dynamic or unresolved references as blocking findings unless explicitly handled in the plan; acceptance evidence is static and dynamic rename fixtures.

`REQ-P11-008` — Refactoring MUST preserve or explicitly account for method/event execution order, object hierarchy, DataEnvironment relationships, ControlSource/RecordSource bindings, class inheritance, project membership, companion files, and code-page/text fidelity; acceptance evidence is pre/post semantic invariant comparisons.

`REQ-P11-009` — After PRG2BIN regeneration, the workspace MUST run VFP9 SP2 compiler validation for affected forms/classes/code and MUST fail the refactor result if binary regeneration or required compile validation fails; acceptance evidence is successful and deliberately broken refactor fixtures.

`REQ-P11-010` — Where a project file is available, refactor validation MUST support a workspace project build or equivalent bounded compile closure to detect downstream breakage beyond the directly edited form, with build outputs kept outside the source tree; acceptance evidence is project-level validation fixtures.

`REQ-P11-011` — Every regenerated binary artifact MUST undergo a final FoxBin2Prg BIN2PRG round-trip and normalized semantic comparison against the intended canonical representation so serialization drift, lost methods/properties, or unexpected changes become blocking findings; acceptance evidence is round-trip-diff tests.

`REQ-P11-012` — The refactor validator MUST produce a structured before/after semantic diff covering objects, classes, properties, methods/events, source references, data bindings, DataEnvironment, dependencies, compiler/build diagnostics, and unresolved risks rather than relying on binary file diffs alone; acceptance evidence is semantic-diff snapshots.

`REQ-P11-013` — The refactor validator MUST support runtime smoke tests for explicitly configured trusted profiles, MUST execute user code only when the profile names the permitted entry points and workspace dataset, and MUST not execute arbitrary production event code by default merely to claim validation; acceptance evidence is default-no-execution, allowlisted-entry-point, dataset-isolation, timeout, and explicit-smoke-test fixtures.

`REQ-P11-014` — The MCP surface MUST expose plan, preview, apply-to-workspace, validate, diff, discard, and export-refactored-artifacts operations so an agent can iteratively refactor a form without touching the original application until validation is complete; acceptance evidence is a complete multi-step refactor session.

`REQ-P11-015` — Source promotion MUST be a separate explicitly enabled operation that verifies exact precondition hashes, creates a recoverable backup or transactional replacement set, promotes the complete companion-file closure atomically as far as Windows filesystem semantics permit, and refuses any source drift; acceptance evidence is promotion success, drift refusal, and rollback tests.

## Release Gate 0.7.0 — Safe VFP Refactoring

`REQ-R04-001` — Release `0.7.0` MUST be publishable and practically usable on Windows only after the exact canonical `0.7.0` release closure defined by the Source of Truth passes, providing plan/preview/workspace-apply/validate/diff/export refactoring for SCX/SCT, VCX/VCT, and related PRG/H code through FoxBin2Prg plus VFP9 SP2 compile/build validation, while source promotion remains disabled by default; acceptance evidence is an end-to-end form refactor with canonical round-trip, compile/build validation, semantic diff, and unchanged originals.

`REQ-R04-002` — Release `0.7.0` MUST pass its machine-readable release-gate manifest, the complete deterministic regression profile for its prerequisite closure, every earlier qualified-release smoke/compatibility suite, clean-wheel Windows installation, official MCP client smoke testing, expected-unavailable future-capability checks, artifact/qualification-provenance validation, and generation of an immutable qualified-release record before the release task can be PASS; acceptance evidence is the retained release-gate report bound to Source of Truth SHA, exact clean local target commit/tree, package hash, verifier/review evidence roots, and qualified-release identity, while remote CI/merge/publication identities are required only when the active operation scope makes them applicable.

## Phase 12 — Privacy, anonymized-data lineage and DBF_Anonymizer integration

`REQ-P12-001` — The privacy adapter MUST call only public `dbf_anonymizer` 1.x APIs and MUST not inspect its private modules or recovery-vault schema; acceptance evidence is root-public import tests.

`REQ-P12-002` — Before pseudonymization, the toolchain MUST derive versioned table, relation, candidate-key, DBC-key, index-expression, memo-identifier, code-page, and source-usage metadata from its application model and pass supported metadata with provenance into DBF_Anonymizer planning/preflight; acceptance evidence is frozen metadata fixtures.

`REQ-P12-003` — `vfp_anonymize_plan` MUST remain source-read-only and MUST report selected data roots, relation/index assurance, memo policy, output/vault policy, VFP index-backend need, and blocking ambiguities without creating pseudonymized output or a recovery vault; acceptance evidence is filesystem snapshots.

`REQ-P12-004` — `vfp_anonymize` MUST write only to configured output/vault roots, preserve the original dataset byte-identically, delegate transformation/verification to DBF_Anonymizer, and register the resulting dataset as a new `ANONYMIZED` dataset with lineage to the original dataset ID; acceptance evidence is an end-to-end multi-table run.

`REQ-P12-005` — When changed indexed data require valid structural indexes, the toolchain MUST provide the VFP9 SP2 index backend needed for rebuild/verification on staged anonymized copies and MUST never register a copied stale CDX/IDX as valid; acceptance evidence is VFP-backed index rebuild and no-backend refusal fixtures.

`REQ-P12-006` — `vfp_anonymize_verify` MUST combine DBF_Anonymizer verification with toolchain schema, relationship, index, record-count, memo-state, and selected aggregate comparison while keeping reverse mappings inaccessible; acceptance evidence is a verified paired dataset.

`REQ-P12-007` — The service MUST support side-by-side analysis of original and anonymized datasets, including the same structured query against both datasets and comparison of schema, counts, relationships, key uniqueness, orphan counts, and aggregate distributions, while explicitly labeling non-comparable pseudonymized values; acceptance evidence is paired-query comparison fixtures.

`REQ-P12-008` — Transfer-bundle creation and verification MUST delegate to DBF_Anonymizer and public outputs MUST exclude recovery databases, original values, reversible offsets, secrets, and sensitive internal vault paths; acceptance evidence is canary leakage and hostile-bundle tests.

`REQ-P12-009` — Recovery MUST be disabled by default and a disabled recovery tool MUST fail before opening the vault; when enabled, recovery MUST accept only configured sensitive-vault/output roots, delegate to the public recovery API, and return metadata rather than recovered record contents in the MCP response; acceptance evidence is disabled and enabled recovery tests.

`REQ-P12-010` — The server MUST verify compatible dbfbridge and DBF_Anonymizer distribution versions and module origins before privacy operations and MUST fail closed on duplicate/shadow or incompatible installations; acceptance evidence is clean, mismatched, and shadow-package environments.

`REQ-P12-011` — The privacy adapter MUST integrate only the root-public DBF_Anonymizer service surface `capabilities`, `build_plan`, `preflight`, `pseudonymize`, `verify_dataset`, `recover`, `create_transfer_bundle`, `verify_transfer_bundle`, and the public `IndexBackend` protocol for VFP-backed index rebuild/verification, without reaching into private engine modules; acceptance evidence is a consumer test importing only these root-public symbols and an injected VFP index-backend fixture.

## Release Gate 0.8.0 — Privacy & Anonymized Dataset Workflows

`REQ-R05-001` — Release `0.8.0` MUST be publishable and practically usable on Windows only after the exact canonical `0.8.0` release closure defined by the Source of Truth passes, providing pseudonymization planning, execution, verification, transfer-bundle workflows, VFP-backed index rebuild where needed, and side-by-side original/anonymized analysis without exposing recovery secrets; acceptance evidence is an end-to-end privacy workflow over related DBF/FPT tables.

`REQ-R05-002` — Release `0.8.0` MUST pass its machine-readable release-gate manifest, the complete deterministic regression profile for its prerequisite closure, every earlier qualified-release smoke/compatibility suite, clean-wheel Windows installation, official MCP client smoke testing, expected-unavailable future-capability checks, artifact/qualification-provenance validation, and generation of an immutable qualified-release record before the release task can be PASS; acceptance evidence is the retained release-gate report bound to Source of Truth SHA, exact clean local target commit/tree, package hash, verifier/review evidence roots, and qualified-release identity, while remote CI/merge/publication identities are required only when the active operation scope makes them applicable.

## Phase 13 — Canonical relational target model and PostgreSQL schema design

`REQ-P13-001` — The Core Service MUST introduce a versioned canonical `RelationalTargetModel` derived from VFP project, DBC, DBF/FPT, CDX/IDX, source-code, form/DataEnvironment, view, relation, and data-profile evidence before any PostgreSQL DDL is generated; acceptance evidence is a stable model schema plus project-to-model fixtures covering every relational-mapping category in the synthetic-fixture coverage matrix.

`REQ-P13-002` — PostgreSQL MUST be the first production relational target, with PostgreSQL 18 as the initial supported production-major baseline, each qualified release that claims PostgreSQL capability MUST record the exact tested supported 18.x patch level in its compatibility manifest, and the version-capability profile MUST keep target SQL generation isolated from one hard-coded server release so later supported PostgreSQL majors can be added by conformance tests; later publication MUST expose the same tested-server identity; acceptance evidence is exact-server-version discovery, target-profile tests, PostgreSQL 18 integration evidence, publication-identity equality, and rejection of unsupported beta/development targets in production release profiles.

`REQ-P13-003` — The PostgreSQL runtime adapter MUST use Psycopg 3 public APIs for typed parameterized SQL, transactions, metadata queries, and high-throughput `COPY` loading rather than shelling out to `psql` for normal migration execution; acceptance evidence is adapter contract tests and COPY-based load fixtures.

`REQ-P13-004` — Schema evolution and bulk data movement MUST remain separate concerns, with generated versioned DDL or an Alembic-compatible schema layer for relational schema changes and a separate data-migration engine for DBF/FPT payload transfer; acceptance evidence is independent schema-plan and data-load artifacts plus rollback tests.

`REQ-P13-005` — PostgreSQL connections MUST be represented by opaque configured target IDs whose credentials never enter project graphs, MCP payloads, generated source files, logs, or migration manifests, while server/database/schema/version/collation facts safe for diagnostics remain available; acceptance evidence is secret-canary redaction tests.

`REQ-P13-006` — The relational model MUST preserve original VFP table/field/object names and separately carry deterministic PostgreSQL physical-name mappings so truncation, case folding, reserved words, national characters, duplicate names, and naming-policy changes never destroy source identity; acceptance evidence is adversarial name-mapping fixtures and reversible metadata lookups.

`REQ-P13-007` — The type mapper MUST translate VFP DBF field types, widths, scales, nullable semantics, and observed value ranges into PostgreSQL types through explicit rules with per-column rationale and confidence, and MUST refuse lossy narrowing unless a migration plan explicitly approves it; acceptance evidence is a complete supported-type matrix and overflow/precision fixtures.

`REQ-P13-008` — Character, Memo, code-page, and Unicode migration MUST normalize text to PostgreSQL UTF-8 while retaining source encoding/code-page provenance and reporting undecodable or lossy values as explicit migration errors rather than silent replacement; acceptance evidence is cp1250, cp852, Mazovia-compatible, mixed-text, and invalid-byte fixtures.

`REQ-P13-009` — VFP NULL, empty Character values, blank fixed-width values, zero dates where encountered, deleted-record state, and other legacy sentinel conventions MUST be modeled explicitly before PostgreSQL translation so NULL/empty semantics are not silently changed; acceptance evidence is semantic mapping fixtures and generated transformation rules.

`REQ-P13-010` — Memo text fields MUST map to a lossless PostgreSQL text strategy with source memo hashes and length validation, while General/binary or otherwise non-text memo payloads MUST use an explicit `BYTEA`, externalized-object, or manual-migration decision rather than being coerced to text; acceptance evidence is text-memo and binary/opaque payload fixtures.

`REQ-P13-011` — Primary-key and candidate-key proposals MUST combine DBC declarations, CDX/IDX uniqueness, source usage, record uniqueness, NULL/empty behavior, and data-profile evidence, and each proposed key MUST retain evidence and confidence instead of being inferred from a field name alone; acceptance evidence is authoritative, inferred, ambiguous, and invalid-key fixtures.

`REQ-P13-012` — The relational planner MUST permit promotion of a discovered relationship to an enforced PostgreSQL foreign key only when its referenced key is suitable and orphan, NULL, collation, type, and cardinality semantics have passed configured validation, and lower-confidence relationships MUST remain documented or inferred relations without automatic FK enforcement; acceptance evidence is FK promotion, orphan, type/collation mismatch, composite-key, and refusal fixtures.

`REQ-P13-013` — The index translator MUST map supported VFP candidate/primary/regular tags and source-observed access patterns to PostgreSQL indexes, including composite, expression, descending, and partial-index candidates where semantics are proven, while unsupported VFP expressions/collations remain explicit migration findings; acceptance evidence is CDX-to-index translation fixtures.

`REQ-P13-014` — VFP CDX `FOR` conditions and equivalent filtered-access semantics MUST be considered as PostgreSQL partial-index candidates only after the predicate is translated and validated against VFP9 SP2 semantics; acceptance evidence is accepted and rejected partial-index fixtures.

`REQ-P13-015` — DBC defaults, validation rules, field/table rules, triggers, stored-procedure dependencies, and referential behavior MUST be classified into PostgreSQL `DEFAULT`, `CHECK`, FK action, trigger/function, generated expression, application-layer rule, or manual-decision targets with source provenance; acceptance evidence is a rule-classification matrix and fixtures.

`REQ-P13-016` — Local views and source `SELECT-SQL` definitions MUST be candidates for PostgreSQL views or parameterized queries only after semantic translation, dependency resolution, and result-equivalence validation, while remote views and connections MUST retain their external-system semantics rather than being flattened blindly; acceptance evidence is local/remote view fixtures.

`REQ-P13-017` — The PostgreSQL schema generator MUST emit deterministic idempotence-aware migration artifacts containing schemas, tables, columns, comments with VFP provenance, keys, constraints, indexes, views, sequences/identity choices, and required helper objects in dependency order; acceptance evidence is reproducible DDL snapshots and clean-database application tests.

`REQ-P13-018` — Generated PostgreSQL constraints and indexes MUST carry stable source-model identities in comments or migration metadata so an operator can trace every target object back to VFP tables, fields, DBC objects, index tags, source references, and evidence that justified it; acceptance evidence is target-to-source traceability tests.

`REQ-P13-019` — VFP AutoIncrement, integer identity, generated-key, and application-assigned key patterns MUST be classified explicitly before PostgreSQL mapping, and any PostgreSQL identity/sequence choice MUST preserve existing values, key ownership, restart position, and concurrency semantics; acceptance evidence is imported-existing-key, generated-new-key, and mixed-key fixtures.

`REQ-P13-020` — VFP DateTime values MUST map through an explicit timezone policy, with timezone-naive preservation as the default candidate unless project evidence justifies another target, and implicit host-local timezone conversion MUST not occur during migration; acceptance evidence is DateTime fixtures executed under different Windows timezone settings.

`REQ-P13-021` — The PostgreSQL collation and comparison policy MUST be explicit where relevant and MUST account for VFP code page/collation, case behavior, trailing-space behavior, index expressions, joins, uniqueness, and ordering before semantic equivalence is claimed; acceptance evidence is Polish-text, case, padding, uniqueness, and ordering fixtures.

`REQ-P13-022` — VFP Currency, Numeric, Float, Double, Integer, generated-key, and other numeric source semantics MUST retain explicit precision, scale, rounding, overflow, and comparison policy during PostgreSQL design, and floating-point values MUST NOT be silently treated as exact decimals merely to simplify parity checks; acceptance evidence is boundary, rounding, overflow, currency, floating-point, and mixed-comparison fixtures.

`REQ-P13-023` — PostgreSQL plans MUST use schema-qualified object references and an explicit safe `search_path` policy, and release-qualified target roles MUST follow least-privilege separation between inspection, schema migration, bulk loading, validation, transition application access, and production cutover capabilities where those capabilities are present; acceptance evidence is hostile-shadow-schema, wrong-role, privilege-escalation, and qualified-object tests.

`REQ-P13-024` — The PostgreSQL runtime adapter MUST enforce bounded per-target connection management with a configured maximum concurrent connection count, acquisition timeout or backpressure, deterministic transaction cleanup, cancellation/error release, connection health/reset policy, and evidence for in-use and waiting capacity; an internal Psycopg pool, a null-pool or external-pool integration, or direct connections can satisfy the design only when the same bounds and cleanup semantics are enforced, and job fan-out MUST NOT create unbounded connection growth; acceptance evidence is max-cap, wait-timeout, cancellation-leak, failed-transaction-reset, multi-target-isolation, sync/async/external-pool, and concurrency-stress tests.

## Phase 14 — VFP SQL and xBase access translation

`REQ-P14-001` — The SQL translator MUST parse supported VFP9 SP2 `SELECT-SQL` and related DML through the semantic parser or a dedicated AST rather than regex substitution, and MUST produce a structured PostgreSQL translation plus unsupported-node diagnostics; acceptance evidence is AST translation fixtures.

`REQ-P14-002` — The translator MUST explicitly model semantic differences in functions, operators, string comparison/padding, NULL behavior, date/datetime arithmetic, logical values, case/collation, aliases, TOP/limits, joins, grouping, aggregates, and VFP-specific constructs before claiming PostgreSQL equivalence; acceptance evidence is a semantic compatibility matrix with positive and negative fixtures.

`REQ-P14-003` — XBase data-access patterns such as `SEEK`, `LOCATE`, `SCAN`, `SET FILTER`, `SET RELATION`, `SET ORDER`, `COUNT`, `SUM`, `REPLACE`, and work-area navigation MUST be transformable into relational access-plan candidates where semantics are provable, without pretending that every procedural VFP sequence has a one-statement SQL equivalent; acceptance evidence is access-pattern translation fixtures.

`REQ-P14-004` — Every generated application query MUST use parameter binding for values and identifier-safe composition for object names, and migration/refactor code MUST not construct executable PostgreSQL SQL by concatenating untrusted field values; acceptance evidence is SQL-injection property tests.

`REQ-P14-005` — Unsupported, dynamically constructed, macro-expanded, runtime-dependent, collation-sensitive, or otherwise ambiguous VFP SQL/access constructs MUST fail translation closed or remain `MANUAL_REVIEW` with exact source spans and reasons rather than emitting approximate SQL as equivalent; acceptance evidence is ambiguous/dynamic query fixtures.

`REQ-P14-006` — The service MUST expose translation explanation linking each PostgreSQL query fragment to the originating VFP source span, VFPX Help evidence, relation/index model, semantic transformation rule, and validation status; acceptance evidence is explain snapshots for every SQL compatibility-matrix translation category.

`REQ-P14-007` — VFP buffering, transaction, locking, optimistic-concurrency, and error-retry behavior that affects a translated data-access path MUST be modeled alongside SQL translation and assigned a PostgreSQL transaction/isolation/concurrency strategy or `MANUAL_REVIEW`; acceptance evidence is explicit table-buffering, transaction, optimistic-conflict, rollback, retry, and unsupported-concurrency fixtures.

`REQ-P14-008` — Translation and parity analysis MUST account for effective VFP environment state plus physical-record and work-area semantics including `RECNO()`, `RECCOUNT()`, `GO`/`GOTO`, `SKIP`, `EOF()`, `BOF()`, `FOUND()`, current order, deleted-record visibility, and code that depends on stable physical record numbers or implicit record order, and semantics that cannot survive relational migration MUST become an explicit compatibility strategy or `MANUAL_REVIEW`; acceptance evidence is physical-order, deleted-record, seek/found, navigation, PACK-change, and unsupported-dependency fixtures.

`REQ-P14-009` — Cross-engine equivalence MUST treat result order as semantically significant only when VFP behavior or translated SQL establishes an order, MUST compare otherwise unordered relational results using an order-independent canonical strategy, and MUST report application code that accidentally depends on unspecified SQL row order as a compatibility finding; acceptance evidence is ordered, unordered, duplicate-row, and accidental-natural-order fixtures.

## Release Gate 0.9.0 — PostgreSQL Relational Designer

`REQ-R06-001` — Release `0.9.0` MUST be publishable and practically usable on Windows only after the exact canonical `0.9.0` release closure defined by the Source of Truth passes, providing an evidence-backed RelationalTargetModel, PostgreSQL schema/constraint/index/view design, deterministic DDL generation, VFP SQL/xBase translation candidates, and migration-readiness findings without production-target data migration; acceptance evidence is a complete relational-design package generated from the release-gate multi-artifact fixture matrix.

`REQ-R06-002` — Release `0.9.0` MUST pass its machine-readable release-gate manifest, the complete deterministic regression profile for its prerequisite closure, every earlier qualified-release smoke/compatibility suite, clean-wheel Windows installation, official MCP client smoke testing, expected-unavailable future-capability checks, artifact/qualification-provenance validation, and generation of an immutable qualified-release record before the release task can be PASS; acceptance evidence is the retained release-gate report bound to Source of Truth SHA, exact clean local target commit/tree, package hash, verifier/review evidence roots, and qualified-release identity, while remote CI/merge/publication identities are required only when the active operation scope makes them applicable.

## Phase 15 — PostgreSQL shadow migration, parity and validation

`REQ-P15-001` — Data migration MUST load first into a controlled staging area or equivalent transactional migration context where type conversion, rejected rows, key validation, and relation checks can complete before target publication; acceptance evidence is staging-success and rejection/rollback fixtures.

`REQ-P15-002` — Bulk DBF/FPT transfer MUST stream through dbfbridge and Psycopg `COPY` or an equivalently bounded PostgreSQL protocol path so large tables and Memo data do not require full-table materialization in process memory; acceptance evidence is large-table bounded-memory integration tests.

`REQ-P15-003` — Every migrated target row MUST retain deterministic migration lineage through primary/candidate keys or an internal migration mapping that can identify the originating dataset, table, and DBF record locator without exposing reversible anonymization secrets; acceptance evidence is source-record-to-target-row traceability tests.

`REQ-P15-004` — Deleted DBF records MUST follow an explicit per-migration policy such as exclude, archive, or migrate-with-tombstone metadata and MUST never disappear through an undocumented default; acceptance evidence is deleted-record policy fixtures.

`REQ-P15-005` — Migration verification MUST compare source and PostgreSQL row counts, deleted-record policy counts, NULL/empty distributions, scalar ranges, Memo lengths and canonical content hashes for every Memo payload type with a defined canonical representation, key uniqueness, rejected rows, and deterministic canonical row signatures for all configured tables; acceptance evidence is exact-match, text-Memo, opaque-Memo-status, and deliberate-corruption tests.

`REQ-P15-006` — Referential verification MUST compare declared and promoted relationships, orphan counts, cardinality, composite-key behavior, and FK enforcement results between source evidence and PostgreSQL target before a migration receives `PASS`; acceptance evidence is relation-preservation tests.

`REQ-P15-007` — Behavioral query verification MUST execute every translated query classified `EQUIVALENCE_TESTABLE` by the versioned SQL compatibility matrix against both the authoritative VFP/DBF side and PostgreSQL target, MUST normalize only explicitly documented semantic differences, MUST report row/value/order mismatches as blocking or explicitly accepted differences, and MUST classify queries that cannot be executed on both sides as `MANUAL_REVIEW` rather than equivalent; acceptance evidence is complete compatibility-matrix cross-engine equivalence, mismatch, and untestable-query fixtures.

`REQ-P15-008` — The migration system MUST support repeatable snapshot migrations, MUST report incremental synchronization as unavailable when no proven change-detection strategy exists, MUST enable incremental synchronization only through an explicitly proven strategy such as application journaling, reliable business timestamps/keys, controlled dual-write, or deterministic table diff, and MUST not claim generic DBF change-data-capture where no reliable source signal exists; acceptance evidence is unavailable-state, supported-strategy, changed-source, reconciliation, and false-CDC-claim tests.

`REQ-P15-009` — Long PostgreSQL migration jobs MUST be checkpointable and safely resumable by table or deterministic chunk, with source snapshot, target schema, conversion policy, and completed-unit fingerprints preventing resume against changed inputs; acceptance evidence is interrupted-load resume, changed-source refusal, and duplicate-prevention tests.

`REQ-P15-010` — Every PostgreSQL target MUST have an explicit environment role `SHADOW`, `STAGING`, or `PRODUCTION` bound to a verified server/database/schema identity, mutating migration tools MUST default-deny `PRODUCTION`, and production mutation MUST require a separate explicit target policy plus identity revalidation at execution time; acceptance evidence is wrong-database, changed-DNS/connection-target, shadow-success, production-default-deny, and explicitly-authorized-production fixtures.

`REQ-P15-011` — Schema or data migration publication against one PostgreSQL target identity MUST use a single-writer migration lease or PostgreSQL advisory-lock equivalent with durable owner/job evidence so concurrent tool instances cannot apply overlapping schema, load, validation-publication, or cutover steps; acceptance evidence is competing-run, stale-lock recovery, crash-release, and different-target concurrency tests.

## Release Gate 0.10.0 — PostgreSQL Shadow Migrator

`REQ-R07-001` — Release `0.10.0` MUST be publishable and practically usable on Windows only after the exact canonical `0.10.0` release closure defined by the Source of Truth passes, providing isolated PostgreSQL target creation, streaming DBF/FPT loading, checkpoint/resume, row/schema/key/relation/Memo verification, source-to-target lineage, and cross-engine query comparison while DBF remains authoritative; acceptance evidence is a complete shadow migration with parity report and no production VFP write-path change.

`REQ-R07-002` — Release `0.10.0` MUST pass its machine-readable release-gate manifest, the complete deterministic regression profile for its prerequisite closure, every earlier qualified-release smoke/compatibility suite, clean-wheel Windows installation, official MCP client smoke testing, expected-unavailable future-capability checks, artifact/qualification-provenance validation, and generation of an immutable qualified-release record before the release task can be PASS; acceptance evidence is the retained release-gate report bound to Source of Truth SHA, exact clean local target commit/tree, package hash, verifier/review evidence roots, and qualified-release identity, while remote CI/merge/publication identities are required only when the active operation scope makes them applicable.

## Phase 16 — VFP-to-PostgreSQL transition, shadow operation and cutover

`REQ-P16-001` — The modernization architecture MUST support a shadow PostgreSQL stage in which DBF remains authoritative while PostgreSQL is refreshed, queried, profiled, and compared without changing production VFP write behavior; acceptance evidence is shadow-refresh and comparison workflows.

`REQ-P16-002` — The Windows transition profile MUST support validation of VFP9 SP2 access to PostgreSQL through the official PostgreSQL ODBC driver and MUST validate each access mechanism selected by the transition plan from SQL Pass-Through, remote views, or CursorAdapter, with the selected access mode represented explicitly in the migration plan; acceptance evidence is trusted-host connectivity plus read/write fixtures for every mechanism declared used by the plan.

`REQ-P16-003` — The service MUST analyze existing VFP data-access code and generate migration candidates identifying which DBF-local operations can remain local temporarily, which can be redirected through SPT/remote view/CursorAdapter, and which require code refactoring for PostgreSQL semantics; acceptance evidence is per-operation transition classifications.

`REQ-P16-004` — Migration of VFP application reads to PostgreSQL MUST proceed by dependency-bounded slices with before/after form, procedure, query, and performance validation rather than by global search-and-replace of DBF access commands; acceptance evidence is one end-to-end migrated feature slice.

`REQ-P16-005` — Generic dual-write from VFP DBF and PostgreSQL MUST not be enabled merely to simplify cutover, and any dual-write plan MUST define transaction/failure ordering, idempotency, reconciliation, rollback, and conflict behavior for the exact tables involved; acceptance evidence is dual-write policy refusal plus one explicitly modeled fixture.

`REQ-P16-006` — The final cutover planner MUST produce a machine-readable sequence covering preconditions, freeze or final-delta strategy, final validation, target activation, VFP connection/configuration changes, smoke tests, rollback point, and post-cutover reconciliation; acceptance evidence is a complete cutover-plan fixture.

`REQ-P16-007` — The MCP surface MUST add `vfp_relational_model`, `vfp_postgres_plan`, `vfp_postgres_generate_ddl`, `vfp_postgres_translate_sql`, `vfp_postgres_migrate`, `vfp_postgres_validate`, `vfp_postgres_compare`, `vfp_postgres_transition_plan`, and `vfp_postgres_cutover_plan`, with mutating target operations requiring explicit target policy and project/dataset identities; acceptance evidence is official MCP-client contract tests.

`REQ-P16-008` — The MCP resource surface MUST expose bounded read-only views for the relational target model, PostgreSQL migration plan/status, source-to-target mappings, translated-query status, validation findings, and cutover readiness without returning database credentials or unbounded migrated row data; acceptance evidence is resource-schema and secret-redaction tests.

`REQ-P16-009` — Each release that supports VFP-to-PostgreSQL transition through ODBC MUST record and test an exact 32-bit Windows psqlODBC driver version compatible with the 32-bit VFP9 SP2 process, and capability discovery MUST report the observed driver identity and architecture instead of treating any PostgreSQL ODBC installation as equivalent; acceptance evidence is trusted-host driver discovery plus connection/read/write tests.

`REQ-P16-010` — A cutover plan MUST model data authority as an explicit state machine and identify the last fully reversible point, the point after which rollback requires reconciliation or forward repair, prerequisites for crossing each boundary, and the verified backup/snapshot or recovery evidence available at that boundary; acceptance evidence is pre-authority rollback, post-authority divergence, failed-cutover recovery, and successful-authority-transfer fixtures.

## Release Gate 0.11.0 — VFP/PostgreSQL Transition Assistant

`REQ-R08-001` — Release `0.11.0` MUST be publishable and practically usable on Windows only after the exact canonical `0.11.0` release closure defined by the Source of Truth passes, providing dependency-bounded feature-slice transition planning, psqlODBC/SPT/remote-view/CursorAdapter validation, controlled read/write migration candidates, final-delta planning, reconciliation, rollback, and cutover planning while generic dual-write remains refused unless explicitly proven safe; acceptance evidence is one trusted-host feature slice moved to PostgreSQL with rollback evidence.

`REQ-R08-002` — Release `0.11.0` MUST pass its machine-readable release-gate manifest, the complete deterministic regression profile for its prerequisite closure, every earlier qualified-release smoke/compatibility suite, clean-wheel Windows installation, official MCP client smoke testing, expected-unavailable future-capability checks, artifact/qualification-provenance validation, and generation of an immutable qualified-release record before the release task can be PASS; acceptance evidence is the retained release-gate report bound to Source of Truth SHA, exact clean local target commit/tree, package hash, verifier/review evidence roots, and qualified-release identity, while remote CI/merge/publication identities are required only when the active operation scope makes them applicable.

## Phase 17 — MCP 2026-07-28 / Python SDK v2 surface stabilization

`REQ-P17-001` — The repository MUST retain and complete the progressively published MCP server using the official Python `mcp` SDK with compatibility `mcp>=2,<3`, MUST use `mcp==2.2.0` as the initial architecture baseline for this Source of Truth revision, and MUST keep the MCP server as a thin adapter over the Core Service with no duplicated DBF parsing, semantic analysis, form parsing, FoxBin2Prg logic, VFP COM logic, query-engine logic, privacy logic, PostgreSQL migration logic, or refactor logic; a later 2.x baseline change MUST pass dependency-boundary and MCP contract conformance before adoption; acceptance evidence is baseline-version, official-client, dependency-origin, and import-boundary tests.

`REQ-P17-002` — The server MUST support local `stdio` as the default production transport, MUST keep Streamable HTTP disabled unless an explicit Windows-host policy enables it, and when Streamable HTTP is enabled both transports MUST expose the same typed domain contracts and authorization decisions with loopback binding as the default network scope; acceptance evidence is disabled-by-default, explicit-enable, loopback-binding, authorization, and official-client transport-equivalence tests.

`REQ-P17-003` — The stable tool registry MUST include project/session operations `vfp_capabilities`, `vfp_project_open`, `vfp_project_close`, `vfp_dataset_register`, `vfp_dataset_list`, `vfp_scan`, `vfp_audit`, `vfp_job_status`, and `vfp_job_cancel`; acceptance evidence is a versioned registry snapshot.

`REQ-P17-004` — The stable data tool registry MUST include `vfp_read_table_schema`, `vfp_read_table_rows`, `vfp_profile_table`, `vfp_search_data`, `vfp_query_data`, `vfp_explain_query`, `vfp_explain_relation`, and `vfp_compare_datasets`; acceptance evidence is positive/negative schema and bounded-result tests for every tool.

`REQ-P17-005` — The stable code/model tool registry MUST include `vfp_read_artifact`, `vfp_read_source`, `vfp_find_symbol`, `vfp_find_references`, `vfp_query_model`, `vfp_impact_analysis`, `vfp_analyze_database`, `vfp_analyze_indexes`, and `vfp_analyze_performance`; acceptance evidence is tool contract tests.

`REQ-P17-006` — The stable form tool registry MUST include `vfp_form_inspect`, `vfp_form_search`, `vfp_form_impact`, `vfp_refactor_form_plan`, `vfp_refactor_preview`, `vfp_refactor_apply_workspace`, `vfp_refactor_validate`, `vfp_refactor_diff`, `vfp_refactor_discard`, `vfp_refactor_export`, and policy-gated `vfp_refactor_promote`; acceptance evidence is an official MCP client refactor session.

`REQ-P17-007` — The stable knowledge tool registry MUST include `vfp_help_search`, `vfp_help_topic`, `vfp_help_for_symbol`, and `vfp_question_context`, with all help results restricted to the pinned VFPX VFP9 SP2 corpus; acceptance evidence is corpus-origin assertions in tool results.

`REQ-P17-008` — The stable privacy tool registry MUST include `vfp_anonymize_plan`, `vfp_anonymize`, `vfp_anonymize_verify`, `vfp_anonymize_export`, and policy-gated `vfp_recover_data`; acceptance evidence is registry/policy tests.

`REQ-P17-009` — The stable resource templates MUST include `vfp://server/capabilities`, `vfp://knowledge/status`, `vfp://knowledge/topic/{topic_id}`, `vfp://project/{project_id}/manifest`, `vfp://project/{project_id}/audit`, `vfp://project/{project_id}/model/summary`, `vfp://project/{project_id}/finding/{finding_id}`, `vfp://project/{project_id}/form/{artifact_id}`, `vfp://dataset/{dataset_id}/manifest`, `vfp://dataset/{dataset_id}/table/{artifact_id}/schema`, `vfp://project/{project_id}/indexes/{artifact_id}`, `vfp://refactor/{refactor_id}`, and `vfp://job/{job_id}`; acceptance evidence is resource template snapshots.

`REQ-P17-010` — MCP resources MUST remain read-only bounded views, while large data rows, graph neighborhoods, source text, help result sets, query results, and diffs MUST use bounded cursor/limit tools rather than unbounded resource bodies; acceptance evidence is response-byte and pagination tests.

`REQ-P17-011` — Every MCP tool input and structured output MUST derive from versioned typed models and generated JSON Schema, and dispatch, permissions, status, and error classification MUST not depend on free-form natural-language parsing; acceptance evidence is malformed-input/property tests.

`REQ-P17-012` — `vfp_question_context` MUST accept a user question plus project/dataset scope and return ranked evidence from VFP source, forms/classes, data schemas/values, relationships, findings, indexes/performance, and VFP9 SP2 Help so the connected LLM can answer cross-domain questions with traceable evidence; acceptance evidence is mixed questions such as 'which form edits this field and what values occur in it?' and 'what depends on this table?'.

`REQ-P17-013` — Long MCP operations MUST connect protocol progress/cancellation to the Core job manager and MUST leave deterministic result/status retrieval by `job_id` after cancellation, disconnect, or client restart; acceptance evidence is reconnect and cancellation tests.

`REQ-P17-014` — Server identity and `vfp_capabilities` MUST expose semantic version, dialect, negotiated/supported MCP protocol revision, MCP SDK baseline, MCP conformance-referee identity used for qualification, Windows platform, VFP build, FoxBin2Prg pin/state, VFPX Help corpus identity, dbfbridge state, DBF_Anonymizer state, value-query policy, refactor/promotion policy, recovery policy, and PostgreSQL transition baseline without launching VFP; acceptance evidence is capability snapshots.

`REQ-P17-015` — The final MCP registry MUST incorporate the PostgreSQL modernization tools and resources defined by the relational, translation, migration, transition, and cutover phases into the same capability, authorization, schema-versioning, job, progress, cancellation, and bounded-result rules as the VFP-native tools; acceptance evidence is one official-client registry snapshot covering both VFP-native and PostgreSQL modernization surfaces.

`REQ-P17-016` — The complete MCP-surface phase MUST stabilize and reconcile progressively qualified tools rather than delay their first availability, and every earlier qualified release MUST remain usable with the subset of tools proven by its release gate whether or not that release has been publicly published; acceptance evidence is backward-compatibility tests from qualified releases 0.4.0 through 0.11.0 into the complete registry.

`REQ-P17-017` — For MCP `stdio` transport, standard output MUST be reserved exclusively for protocol framing/messages and all human diagnostics, logs, tracebacks, progress diagnostics outside protocol notifications, and startup notices MUST use standard error or configured log sinks; acceptance evidence is protocol-parser tests with warning/error injection and zero-nonprotocol-stdout assertions.

`REQ-P17-018` — Streamable HTTP exposure beyond loopback MUST remain disabled unless an explicit host policy defines authenticated access and transport protection through the server or a trusted local reverse proxy, and unauthenticated non-loopback binding MUST fail closed; acceptance evidence is loopback-default, unauthenticated-remote-refusal, authenticated-policy, proxy-policy, and transport-equivalence tests.

`REQ-P17-019` — Every release-qualified MCP tool, resource template, Core public model, console entry point, machine-readable error code, and configuration schema MUST carry a compatibility identity tied to the product semantic version, and a breaking public-contract change MUST require explicit contract-evolution authorization plus either a versioned coexistence/adapter path or a declared breaking-release boundary; public publication MUST expose the same qualified compatibility identity; acceptance evidence is additive-change, compatible-deprecation, unauthorized-breaking-change, versioned-adapter, declared-breaking-boundary, and publication-identity tests.

`REQ-P17-020` — Deprecation of a previously release-qualified public contract MUST be machine-readable in capability/schema metadata with replacement guidance and first-deprecated version, MUST remain functional for at least the immediately following qualified release unless an explicit safety/security contract evolution requires immediate disablement, and removal MUST be covered by old-client/new-server tests; public publication state MUST NOT shorten the qualified deprecation window; acceptance evidence is normal qualified deprecation window, unpublished-predecessor, replacement metadata, premature-removal, and emergency-disable fixtures.

`REQ-P17-021` — The MCP wire-protocol baseline MUST be the final `2026-07-28` Model Context Protocol specification independently of the Python SDK version, the server MUST intentionally negotiate or emit that protocol revision rather than assuming an SDK default, draft/future protocol revisions including an unfinished successor MUST NOT become active without explicit contract evolution, and release qualification MUST pass the pinned official server conformance referee defined by `REQ-P17-023`; acceptance evidence is protocol-version negotiation, explicit-baseline, future-draft refusal, official-client/conformance, stateless-request, and wrong-protocol fixtures.

`REQ-P17-022` — MCP tool `inputSchema` and `outputSchema` MUST follow the `2026-07-28` specification's JSON Schema 2020-12 semantics, tool input roots MUST remain objects, output schemas can describe any JSON value permitted by the protocol, schema references MUST remain local or bundled rather than being dereferenced from the network, and schema validation MUST enforce configured depth/size/time limits; acceptance evidence is composition/reference, non-object-output, input-root-refusal, external-reference-blocking, validation-budget, and official-client schema fixtures.

`REQ-P17-023` — MCP `2026-07-28` server conformance MUST use the official `modelcontextprotocol/conformance` frozen requirement set `requirements/2026-07-28.yaml` anchored to `@modelcontextprotocol/conformance@0.2.0-alpha.10`; the initial acquisition baseline MUST verify that requirement file from repository commit `7169291ec0b68eb370fddcd9947313ab0d5e4156` with Git blob identity `b0c4f8560429e8f4b6c89833cc0b35405bc004ff`, qualification MUST execute the server role with `--requirements 2026-07-28`, scored failures MUST block conformance, and `not_scored` scenarios MUST remain visible without becoming PASS substitutes; acceptance evidence is pinned-referee identity, frozen-requirement-set, server-required-scenario, scored-failure, not-scored-visibility, and changed-referee dependency-boundary tests.

## Phase 18 — Full-system testing, packaging and 1.0 closure

`REQ-P18-001` — The repository MUST provide redistributable synthetic VFP9 SP2 fixtures covering DBF with and without FPT, Character/Memo/General or opaque binary cases, deleted/NULL records, Polish code pages, CDX/IDX, DBC relations/views/connections, PRG/H/MPR, SCX/SCT, VCX/VCT, PJX/PJT, FRX/FRT, LBX/LBT, MNX/MNT, DataEnvironment, external dependencies, original/anonymized dataset pairs, malformed files, ambiguous dynamic code, relational-target mappings, translated SQL, PostgreSQL staging/target fixtures, migration mismatches, and VFP-to-PostgreSQL transition cases; acceptance evidence is fixture provenance documentation.

`REQ-P18-002` — CI MUST run on supported Windows Python versions and MUST include formatting, linting, strict typing, compile checks, unit/integration/property/security tests, no-VFP pure analysis tests, VFPX corpus tests, dbfbridge consumer tests, DBF_Anonymizer consumer tests, MCP official-client tests, PostgreSQL 18 integration tests, Psycopg migration tests, SQL-translation tests, package tests, and dependency-origin checks; acceptance evidence is mandatory workflow jobs.

`REQ-P18-003` — Trusted VFP9 SP2 CI or release validation MUST run separately from untrusted pull-request code and MUST cover FoxBin2Prg BIN2PRG/PRG2BIN, VFP worker isolation, CDX/DBC runtime inspection, compiler/build validation, SYS(3054), form/class refactor round-trips, project-build closure, and VFP index rebuild for anonymized data, VFP-to-PostgreSQL ODBC transition evidence, and cross-engine query-equivalence evidence; acceptance evidence is signed or retained trusted-host artifacts.

`REQ-P18-004` — The form/class regression corpus MUST include golden SCX/SCT and VCX/VCT fixtures whose FoxBin2Prg canonical text, object graph, method/property hashes, and post-refactor round-trip structures are asserted so refactoring cannot silently lose designer content; acceptance evidence is golden-fixture tests.

`REQ-P18-005` — The knowledge regression suite MUST verify the pinned VFPX HelpFile commit/version, corpus input counts/fingerprints, topic lookup, title/index alias lookup, member lookup, help-to-source links, and rejection of an injected older-version manual as normative knowledge; acceptance evidence is corpus drift tests.

`REQ-P18-006` — The package MUST build installable Windows wheel/sdist artifacts with console entry points for CLI and MCP server, work without repository checkout, and install fully offline from a generated locked wheelhouse; acceptance evidence is clean-machine installation and stdio server smoke tests.

`REQ-P18-007` — The repository MUST maintain machine-readable benchmarks for project scan, semantic indexing, DBF/Memo profiling, value search, relational query/join, graph query, Help search, MCP overhead, FoxBin2Prg conversion, form refactor round-trip, privacy planning, relational-model generation, SQL translation, PostgreSQL COPY loading, source/target parity verification, and VFP runtime operations where available; acceptance evidence is a committed synthetic baseline.

`REQ-P18-008` — Documentation MUST be English-first and cover Windows installation, VFP9 SP2 setup, pinned VFPX Help corpus, FoxBin2Prg setup, offline deployment, project/dataset roles, original-versus-anonymized analysis, data questions, form analysis, refactoring workflow, promotion/rollback, VFP validation, privacy/recovery, relational target modeling, PostgreSQL DDL/SQL translation, shadow migration, parity validation, VFP ODBC transition, cutover/rollback, MCP tools/resources, path policy, and troubleshooting; acceptance evidence is link/schema/example tests.

`REQ-P18-009` — The implementation/completeness matrix MUST be generated or deterministically checked against registered analyzers, tools, resources, dependency states, and trusted runtime tests so documentation cannot claim available data, form-refactor, Help, privacy, VFP, PostgreSQL modernization, transition, cutover-readiness, or MCP capability when executable evidence is absent; acceptance evidence is drift tests.

`REQ-P18-010` — Before the complete target architecture is declared contract-frozen, the repository MUST freeze versioned Core models, error codes, capability catalog, project/dataset/session schemas, semantic graph schema, data-query schema, form model, RefactorPlan schema, RelationalTargetModel schema, PostgreSQL target-plan schema, SQL-translation schema, migration/validation/cutover schemas, finding/completeness vocabularies, MCP protocol revision, MCP tool names, resource templates, JSON Schema dialect, host-policy schema, VFPX Help corpus identity, FoxBin2Prg pin, and compatible dbfbridge, DBF_Anonymizer, MCP SDK, Psycopg, PostgreSQL major-version, and psqlODBC ranges/baselines; acceptance evidence is contract snapshots.

`REQ-P18-011` — The final target-architecture acceptance MUST install the product offline on Windows, start the MCP server over stdio, open a multi-artifact VFP9 SP2 project, register original and anonymized DBF/FPT datasets, answer bounded data/relation questions including Memo content, analyze forms/classes and dependency impact, retrieve VFP9 SP2 Help evidence, run database/index/Rushmore analysis, perform and validate a FoxBin2Prg/VFP9 form refactor, execute privacy verification, derive a RelationalTargetModel, generate and apply PostgreSQL 18 DDL to an isolated target, migrate the release-acceptance DBF/FPT fixture matrix by streaming COPY, validate structural/data/relation/query parity, exercise a trusted VFP-to-PostgreSQL transition slice, and prove immutable original sources except during explicitly enabled promotion; acceptance evidence is one machine-readable end-to-end manifest with all assertions passing.

`REQ-P18-012` — Release `1.0.0` MUST qualify only after the complete target-architecture acceptance passes and can be publicly published only from that exact qualified identity under `PUBLICATION` scope, while the existence and usability of qualified releases 0.4.0 through 0.11.0 MUST remain independent of unfinished later milestones and independent of public publication; acceptance evidence is a qualified release matrix mapping every version to proven capabilities and intentionally unavailable future capabilities plus qualification/publication identity checks.


`REQ-P18-013` — The complete release regression suite MUST execute deterministic evidence for every mandatory requirement in the frozen contract and MUST produce a machine-readable coverage report showing 100 percent requirement-verifier coverage, zero unknown requirement IDs, zero missing required evidence classes, and zero unexpected skipped/xfail/xpass tests; acceptance evidence is the final requirement-coverage report.

`REQ-P18-014` — The complete release regression suite MUST replay every prior qualified release-gate MCP smoke scenario against the final server so `1.0.0` cannot pass by replacing earlier useful behavior with a different final-only workflow, independent of whether earlier qualified releases were publicly published; acceptance evidence is cumulative qualified `0.4.0` through `0.11.0` client-scenario results.

`REQ-P18-015` — Under `PUBLICATION` scope, final publication acceptance MUST prove at least two independent remote change/review/CI/integration cycles under the frozen Source of Truth using declared authoring-mode provenance, preserve the Source of Truth hash and execution-profile hash, complete all configured deterministic verifiers and independent reviews, produce a fresh read-only final requirements/architecture/security/compatibility audit, and bind the public `1.0.0` publication to an eligible qualified `1.0.0` identity after the integration-commit rules in `REQ-AUTO-055`; acceptance evidence is durable manual/autonomous/hybrid-capable remote execution/evidence bundles, qualification/integration/publication identity proof, and final release report.

`REQ-P18-016` — Release-qualified package installation and MCP startup MUST be tested from the distribution artifacts rather than an editable source checkout for every supported Python version, and tests MUST prove that runtime code does not accidentally depend on repository-only files, developer tools, test fixtures, Git metadata, current working directory, or network downloads; acceptance evidence is clean Windows qualified-artifact installation matrices.

`REQ-P18-017` — The product MUST support a local private-acceptance profile that can run selected release-gate analyses against operator-owned real VFP9 SP2 applications and datasets outside the repository while recording only configured redacted findings, hashes, capability statuses, timing, and verifier results in reusable evidence; acceptance evidence is a synthetic stand-in exercising the private-profile path plus leakage scans proving that private source/data is not copied into repository or release artifacts.

`REQ-P18-018` — Absence of an operator private-acceptance corpus MUST NOT be represented as PASS and MUST be reported as `NOT_CONFIGURED` without blocking public release gates, while a configured private-acceptance profile that fails MUST block only the corresponding local deployment-qualification claim until resolved; acceptance evidence is absent-profile, passing-profile, failing-profile, and public-release-independence tests.

`REQ-P18-019` — The repository MUST provide a deterministic deployment-qualification report that distinguishes public release qualification from host-specific qualification and records Windows version, Python architecture, VFP9 build, FoxBin2Prg identity, ODBC identity where relevant, project/dataset snapshot identities, enabled capabilities, private-acceptance status, and unresolved limitations without exposing sensitive values; acceptance evidence is no-VFP, full-VFP, PostgreSQL-transition, and redaction fixtures.

`REQ-P18-020` — Release builds MUST be reproducible at the logical artifact level from the same qualified commit, lock inputs, and build configuration, with wheel/sdist contents, generated schemas/manifests, dependency inventory, and executable entry-point behavior matching after normalization of permitted archive metadata; acceptance evidence is two independent clean Windows builds with normalized artifact comparison.

`REQ-P18-021` — The complete target architecture MUST pass an independent `GREENFIELD_FULL_BUILD` acceptance that starts from a completely empty repository, performs deterministic bootstrap, implements the requirement graph through the same release-qualification gates under `LOCAL_QUALIFICATION` in a declared `MANUAL`, `AUTONOMOUS`, or `HYBRID` authoring mode, installs the final distribution on Windows, and passes the final MCP/VFP/PostgreSQL acceptance without importing source or generated implementation artifacts from the brownfield repository or performing remote repository/publication mutation; the mode-specific provenance rules in `REQ-G00-054` through `REQ-G00-056` MUST remain satisfied; acceptance evidence is a retained empty-repository-to-qualified-1.0 execution manifest with authoring-mode provenance, zero-remote-mutation evidence, and artifact-origin audit.

`REQ-P18-022` — The complete target architecture MUST pass a `GREENFIELD_BROWNFIELD_EQUIVALENCE` acceptance that compares independently qualified greenfield and brownfield builds of the same release and proves equivalent public package metadata, Core schemas, MCP tool/resource schemas, error registry, capability catalog, release-gate behavior, and deterministic fixture results, with only explicitly recorded compatibility migrations permitted to differ; acceptance evidence is a machine-readable cross-build differential report.

`REQ-P18-023` — Release upgrade qualification MUST use the immediately preceding qualified release record: the first qualified release MUST record predecessor state `INITIAL_RELEASE`, and every later qualified release MUST test an in-place package upgrade from the preceding qualified release artifacts on clean Windows hosts while preserving or deterministically migrating supported configuration, persistent Core state, caches according to cache policy, public command availability, and MCP contract compatibility; public publication state MUST NOT change the predecessor used for qualification; acceptance evidence is initial-qualified-no-predecessor plus qualified-release-to-qualified-release upgrade matrices for every supported Python version and unpublished-predecessor tests.

`REQ-P18-024` — Every qualified release MUST verify that its locked wheelhouse contains every Python artifact required for clean offline installation of all capabilities claimed by that release profile, that each wheelhouse artifact matches the dependency lock and provenance inventory, and that installation fails clearly rather than reaching the network when an artifact is intentionally removed; later public publication MUST use the same qualified wheelhouse/dependency identities; acceptance evidence is complete-wheelhouse, tampered-wheelhouse, missing-wheel, network-blocked install, and publication-identity tests.

`REQ-P18-025` — Release qualification MUST verify the declared Windows support matrix rather than a single host, and every `TESTED` Windows/process-architecture profile claimed by the release MUST complete package install, capability discovery, required non-VFP tests, and profile-specific trusted-host tests where applicable; acceptance evidence is the release support-matrix execution report.

`REQ-P18-026` — Release qualification MUST use a deterministic performance predecessor from the immediately preceding qualified release record: the first qualified release MUST capture the normalized release-critical synthetic benchmark baseline without a predecessor comparison, while every later qualified release MUST compare those benchmarks against the preceding qualified release on the same normalized benchmark-host profile, record statistically robust relative deltas and resource use, and block only version-controlled regression budgets for designated critical benchmarks rather than unstable universal wall-clock thresholds; acceptance evidence is initial-qualified-baseline, unpublished-qualified-predecessor, no-regression, intentional-regression, noisy-sample, and approved-budget-change fixtures.

`REQ-P18-027` — Each qualified release profile MUST define a versioned offline asset manifest for non-Python components required by its claimed capabilities, including the normalized VFPX Help corpus and FoxBin2Prg assets when applicable, and offline qualification MUST either install those redistributable assets from hash-verified release/cache artifacts or verify operator-provided local assets by the same identity rules while never bundling unlicensed VFP proprietary assets; later public publication MUST expose the same qualified asset-manifest identity; acceptance evidence is complete-asset, missing-asset, tampered-asset, operator-provided-VFP, unauthorized-VFP-bundle, and publication-identity tests.

`REQ-P18-028` — The clean offline installation acceptance MUST begin with network access blocked before package and non-Python asset installation, use only the locked wheelhouse plus the versioned offline asset manifest/cache and explicitly operator-provided proprietary VFP assets, and finish with capability discovery proving which optional trusted capabilities are available or unavailable without any implicit download; acceptance evidence is a fully network-blocked installation from empty Python environment and empty product installation root.

`REQ-P18-029` — Before release `1.0.0` can qualify, dependency qualification MUST re-evaluate the pinned DBF_Anonymizer baseline and MUST use a stable compatible `1.x` release when one has passed the public-boundary and privacy conformance suite; if the qualified profile retains a prerelease or development DBF_Anonymizer baseline, it MUST carry an explicit machine-readable exception bound to the exact version, commit, and artifact hashes, document why no tested stable candidate is adopted, pass the complete privacy and end-to-end regression suite, and record the residual dependency-maturity risk in qualified-release provenance; acceptance evidence is stable-baseline adoption, prerelease-without-exception refusal, prerelease-exception qualification, incompatible-stable-candidate refusal, and provenance-reconstruction tests.

`REQ-P18-030` — Until Python 3.15 enters the supported runtime range through an explicit compatibility change, Windows CI MUST execute a non-support-claiming Python 3.15 forward-compatibility profile using an exact interpreter identity frozen for each run, MUST record dependency-install, package-build, import, unit/contract, and representative integration outcomes, and MUST publish the result as advisory evidence whose test failures do not by themselves fail a release gate or expand supported-Python metadata; acceptance evidence is exact-interpreter report, incompatible-dependency report, no-support-claim guard, advisory-failure isolation, and later explicit-promotion-to-supported-range fixtures.


---

# 3. Start-mode architecture

Two supported starting modes lead to one target product:

```text
GREENFIELD
empty directory or no-product/no-commit repository
        |
        v
deterministic repository bootstrap
        |
        v
Bootstrap Gate B0
        |
        +----------------------+
                               |
BROWNFIELD                     |
existing implementation        |
        |                      |
        v                      |
brownfield baseline            |
compatibility migration        |
        |                      |
        +----------+-----------+
                   |
                   v
         same requirement graph
                   |
                   v
         same progressive releases
                   |
                   v
                1.0.0
```

The starting mode affects initialization and compatibility evidence only. Product semantics and release contracts are shared.

---

# 4. Normative precedence and glossary

Normative precedence:

```text
1. this Source of Truth
2. hash-bound portable requirement/verification derived artifacts
3. pinned external authorities within their assigned technical domains
4. implemented public contracts and deterministic evidence
5. repository documentation and examples
6. historical notes, prompts and conversations
```

A conflict is surfaced as a finding. Lower layers do not silently redefine higher layers.

Core vocabulary:

| Term | Meaning |
|---|---|
| Project | One registered Visual FoxPro application/source root plus its immutable snapshot identity. |
| Dataset | One registered VFP data collection with role `ORIGINAL`, `ANONYMIZED`, or `WORKSPACE` and explicit lineage. |
| Artifact | One identified VFP/source/data/external file or logical object with stable provenance. |
| Snapshot | A fingerprinted, internally consistent immutable view of source or dataset inputs used by an operation. |
| Evidence | Machine-readable provenance supporting a fact, inference, validation state, or finding. |
| Capability | A declared operation class available on the current Windows host under the effective policy. |
| Completeness | Domain-specific state describing how much of the detected project can be interpreted with current evidence. |
| Finding | A structured diagnostic, risk, incompatibility, optimization candidate, ambiguity, or validation result. |
| Workspace | An isolated writable copy outside immutable original source/data roots. |
| RefactorPlan | A versioned change intent with preconditions, affected identities, transformations, validation and rollback evidence. |
| RelationalTargetModel | Canonical evidence-backed relational representation derived from VFP semantics before PostgreSQL DDL generation. |
| Migration | Controlled source-to-target schema/data transformation with lineage and validation. |
| Release gate | Deterministic closure proving one publishable capability level while later capabilities can remain unavailable. |
| Public release qualification | Evidence that the distributable product satisfies a release gate on declared supported Windows profiles. |
| Deployment qualification | Evidence for one concrete Windows/VFP/PostgreSQL host and optionally one private operator corpus. |
| Execution profile | Tool-specific binding that runs the same portable contract using Converge or another coding system. |
| Verification manifest | Tool-neutral mapping from requirement IDs to deterministic verifier semantics and evidence classes. |
| Requirement graph | Tool-neutral acyclic prerequisite/release mapping for executable requirements. |

---

# 5. Canonical applicability mapping

Applicability is a structured graph attribute. The default is `ALWAYS`; only the overrides below replace that default.

```yaml
applicability_mapping:
  default: ALWAYS

  overrides:
    START_AMBIGUOUS:
      selector:
        include: [REQ-G00-002]
      expression:
        start_mode: AMBIGUOUS

    GREENFIELD_ONLY:
      selector:
        include:
          - REQ-G00-003..REQ-G00-008
          - REQ-G00-010..REQ-G00-012
          - REQ-G00-015..REQ-G00-019
          - REQ-G00-021
          - REQ-G00-022
          - REQ-B00-001..REQ-B00-002
      expression:
        start_mode: GREENFIELD

    BROWNFIELD_ONLY:
      selector:
        include:
          - REQ-G00-042
          - REQ-G00-044..REQ-G00-045
          - REQ-G00-047..REQ-G00-051
          - REQ-B00-003
          - REQ-P00-020..REQ-P00-022
      expression:
        start_mode: BROWNFIELD

    CROSS_START_PAIR:
      selector:
        include: [REQ-G00-014]
      expression:
        release_context: CROSS_START_PAIR_AVAILABLE

    REMOTE_INTEGRATION_ONLY:
      selector:
        include:
          - REQ-AUTO-031
          - REQ-AUTO-053..REQ-AUTO-055
      expression:
        operation_scope: [REMOTE_INTEGRATION, PUBLICATION]

    AUTONOMOUS_AUTHORING_ONLY:
      selector:
        include:
          - REQ-AUTO-042..REQ-AUTO-043
      expression:
        authoring_mode: [AUTONOMOUS, HYBRID]

    PUBLICATION_ONLY:
      selector:
        include:
          - REQ-AUTO-028..REQ-AUTO-030
          - REQ-AUTO-047
          - REQ-AUTO-050
          - REQ-P18-015
      expression:
        operation_scope: [PUBLICATION]

    RELEASE_0_4_0:
      selector:
        include: [REQ-R01-*]
      expression:
        release_profile: 0.4.0

    RELEASE_0_5_0:
      selector:
        include: [REQ-R02-*]
      expression:
        release_profile: 0.5.0

    RELEASE_0_6_0:
      selector:
        include: [REQ-R03-*]
      expression:
        release_profile: 0.6.0

    RELEASE_0_7_0:
      selector:
        include: [REQ-R04-*]
      expression:
        release_profile: 0.7.0

    RELEASE_0_8_0:
      selector:
        include: [REQ-R05-*]
      expression:
        release_profile: 0.8.0

    RELEASE_0_9_0:
      selector:
        include: [REQ-R06-*]
      expression:
        release_profile: 0.9.0

    RELEASE_0_10_0:
      selector:
        include: [REQ-R07-*]
      expression:
        release_profile: 0.10.0

    RELEASE_0_11_0:
      selector:
        include: [REQ-R08-*]
      expression:
        release_profile: 0.11.0
```

No requirement can match more than one applicability override unless a later Source of Truth revision introduces an explicit boolean-composition schema and contract-evolution record.

---

# 6. Canonical lifecycle mapping

Lifecycle assignment is deterministic and uses only selectors accepted by `REQ-PORT-024`. Rules are applied in the order shown.

```yaml
lifecycle_mapping:
  BOOTSTRAP:
    include:
      - REQ-G00-001..REQ-G00-008
      - REQ-G00-010..REQ-G00-013
      - REQ-G00-015..REQ-G00-019
      - REQ-G00-021
      - REQ-G00-022
      - REQ-G00-023..REQ-G00-025
      - REQ-G00-026..REQ-G00-074
      - REQ-B00-*
      - REQ-P00-020..REQ-P00-022
      - REQ-PORT-*
      - REQ-AUTO-001..REQ-AUTO-005
      - REQ-AUTO-040..REQ-AUTO-042

  RELEASE_GUARD:
    include:
      - REQ-G00-009
      - REQ-G00-014
      - REQ-P00-012
      - REQ-P00-015
      - REQ-P00-024
      - REQ-P00-026
      - REQ-AUTO-010
      - REQ-AUTO-022
      - REQ-AUTO-024..REQ-AUTO-030
      - REQ-AUTO-036
      - REQ-AUTO-047
      - REQ-AUTO-050
      - REQ-AUTO-051..REQ-AUTO-052
      - REQ-R01-*
      - REQ-R02-*
      - REQ-R03-*
      - REQ-R04-*
      - REQ-R05-*
      - REQ-R06-*
      - REQ-R07-*
      - REQ-R08-*
      - REQ-P18-020
      - REQ-P18-023..REQ-P18-028

  DEPLOYMENT_GUARD:
    include:
      - REQ-P18-017..REQ-P18-019

  FINAL_ACCEPTANCE:
    include:
      - REQ-P18-010..REQ-P18-016
      - REQ-P18-021..REQ-P18-022
      - REQ-P18-029..REQ-P18-030

  MERGE_GUARD:
    include:
      - REQ-AUTO-006..REQ-AUTO-009
      - REQ-AUTO-011..REQ-AUTO-021
      - REQ-AUTO-023
      - REQ-AUTO-031..REQ-AUTO-035
      - REQ-AUTO-037..REQ-AUTO-039
      - REQ-AUTO-043..REQ-AUTO-046
      - REQ-AUTO-048..REQ-AUTO-049
      - REQ-AUTO-053..REQ-AUTO-055

  IMPLEMENTATION:
    include:
      - REQ-G00-020
      - REQ-P00-*
      - REQ-P01-*
      - REQ-P02-*
      - REQ-P03-*
      - REQ-P04-*
      - REQ-P05-*
      - REQ-P06-*
      - REQ-P07-*
      - REQ-P08-*
      - REQ-P09-*
      - REQ-P10-*
      - REQ-P11-*
      - REQ-P12-*
      - REQ-P13-*
      - REQ-P14-*
      - REQ-P15-*
      - REQ-P16-*
      - REQ-P17-*
      - REQ-P18-001..REQ-P18-009
```

Earlier lifecycle rules take precedence over later family wildcards. The self-consistency verifier expands every selector, rejects duplicate final classification, rejects unclassified IDs, and compares the expanded map with the generated requirement graph.

---

# 7. Canonical execution contract

The machine-readable requirement graph derives from the applicability and lifecycle maps rather than Markdown position. Milestones intentionally select only capability needed by that release; later-phase integration requirements do not block earlier useful releases.

```yaml
lifecycle:
  BOOTSTRAP:
    activation: start-state preparation
  IMPLEMENTATION:
    activation: explicit prerequisites satisfied
  MERGE_GUARD:
    activation: every candidate integration subject to operation-scope applicability
  RELEASE_GUARD:
    activation: named release qualification subject to operation-scope applicability
  DEPLOYMENT_GUARD:
    activation: host/private deployment qualification
  FINAL_ACCEPTANCE:
    activation: 1.0 closure

start_readiness:
  GREENFIELD_READY: B0
  BROWNFIELD_READY: BR0

authoring_mode:
  default: MANUAL
  MANUAL:
    coding_agent_required: false
    default_execution_profile: generic
  AUTONOMOUS:
    coding_agent_required: true
    default_execution_profile: converge
    undeclared_human_source_edit: forbidden
  HYBRID:
    coding_agent_required: optional
    default_execution_profile: generic
    actor_attribution: yes

execution_controller:
  generic:
    controller_class: HUMAN_OPERATED_OR_HYBRID
    converge_required: false
  converge:
    controller_class: AUTONOMOUS_OR_HYBRID
    coding_agent_required: true
    origin: https://github.com/PeterPirog/converge-orchestrator
    commit: 1be97b75cf3b51f5ad0c2f212288f0a9edb3899b
    tree: d47b3c74b7b597dec503b4d3dca9db60e5488c93
    acquisition: [BOUND_TOOL_ROOT, CONNECTED_PINNED, OFFLINE_CACHE]

operation_scope:
  default: LOCAL_QUALIFICATION
  LOCAL_QUALIFICATION:
    remote_mutation: false
    publication: false
  REMOTE_INTEGRATION:
    remote_mutation: true
    publication: false
    branch_policy_modes: [NATIVE_PROTECTED, TRUSTED_UNPROTECTED]
  PUBLICATION:
    remote_mutation: true
    publication: true
    branch_policy_modes: [NATIVE_PROTECTED, TRUSTED_UNPROTECTED]

milestones:
  P00_DOMAIN:
    after: [START_READY]
    selector:
      include: [REQ-P00-*]
      exclude: [REQ-P00-005, REQ-P00-006, REQ-P00-008, REQ-P00-027]
      lifecycle: [IMPLEMENTATION]

  P01_CORE:
    after: [P00_DOMAIN]
    selector:
      include: [REQ-P01-*]
      exclude: [REQ-P01-011..REQ-P01-013]
      lifecycle: [IMPLEMENTATION]

  P02_SECURITY:
    after: [P01_CORE]
    selector:
      include: [REQ-P02-*]
      lifecycle: [IMPLEMENTATION]

  P01_MCP_MIN:
    after: [P02_SECURITY]
    selector:
      include:
        - REQ-P01-011..REQ-P01-013
        - REQ-G00-020
        - REQ-P17-001
        - REQ-P17-002
        - REQ-P17-011
        - REQ-P17-014
        - REQ-P17-017..REQ-P17-019
        - REQ-P17-021..REQ-P17-023
      lifecycle: [IMPLEMENTATION]

  P03_KNOWLEDGE:
    after: [P01_MCP_MIN]
    selector:
      include: [REQ-P03-*]
      exclude: [REQ-P03-007]
      lifecycle: [IMPLEMENTATION]

  P04_DATA:
    after: [P03_KNOWLEDGE]
    selector:
      include: [REQ-P04-*]
      lifecycle: [IMPLEMENTATION]

  P05_SEMANTIC_GRAPH:
    after: [P04_DATA]
    selector:
      include: [REQ-P05-*, REQ-P03-007]
      lifecycle: [IMPLEMENTATION]

  P06_FOXBIN_ANALYSIS:
    after: [P05_SEMANTIC_GRAPH]
    selector:
      include: [REQ-P00-006, REQ-P06-001..REQ-P06-003]
      lifecycle: [IMPLEMENTATION]

  P07_FORMS_CLASSES:
    after: [P06_FOXBIN_ANALYSIS]
    selector:
      include: [REQ-P07-*]
      lifecycle: [IMPLEMENTATION]

  P08_DBC_MODEL:
    after: [P07_FORMS_CLASSES]
    selector:
      include: [REQ-P08-*]
      lifecycle: [IMPLEMENTATION]

  P09_REASONING:
    after: [P08_DBC_MODEL]
    selector:
      include: [REQ-P09-*]
      lifecycle: [IMPLEMENTATION]

  P10_OPTIMIZATION:
    after: [P09_REASONING]
    selector:
      include:
        - REQ-P06-004..REQ-P06-009
        - REQ-P06-011..REQ-P06-014
        - REQ-P10-*
      lifecycle: [IMPLEMENTATION]

  P11_REFACTOR:
    after: [P10_OPTIMIZATION]
    selector:
      include:
        - REQ-P00-005
        - REQ-P06-010
        - REQ-P06-015
        - REQ-P11-*
      lifecycle: [IMPLEMENTATION]

  P12_PRIVACY:
    after: [P11_REFACTOR]
    selector:
      include: [REQ-P00-008, REQ-P12-*]
      lifecycle: [IMPLEMENTATION]

  P13_RELATIONAL_MODEL:
    after: [P12_PRIVACY]
    selector:
      include: [REQ-P00-027, REQ-P13-*]
      lifecycle: [IMPLEMENTATION]

  P14_TRANSLATION:
    after: [P13_RELATIONAL_MODEL]
    selector:
      include: [REQ-P14-*]
      lifecycle: [IMPLEMENTATION]

  P15_SHADOW_MIGRATION:
    after: [P14_TRANSLATION]
    selector:
      include: [REQ-P15-*]
      lifecycle: [IMPLEMENTATION]

  P16_TRANSITION:
    after: [P15_SHADOW_MIGRATION]
    selector:
      include: [REQ-P16-*]
      lifecycle: [IMPLEMENTATION]

  P17_MCP_STABILIZATION:
    after: [P16_TRANSITION]
    selector:
      include: [REQ-P17-*]
      lifecycle: [IMPLEMENTATION]

  P18_FINAL:
    after: [P17_MCP_STABILIZATION]
    selector:
      include: [REQ-P18-*]
      lifecycle: [IMPLEMENTATION, FINAL_ACCEPTANCE]

release_closure:
  0.4.0: [START_READY, P00_DOMAIN, P01_CORE, P02_SECURITY, P01_MCP_MIN, P03_KNOWLEDGE, P04_DATA, activated_governance]
  0.5.0: [0.4.0, P05_SEMANTIC_GRAPH, P06_FOXBIN_ANALYSIS, P07_FORMS_CLASSES, P08_DBC_MODEL, P09_REASONING, activated_governance]
  0.6.0: [0.5.0, P10_OPTIMIZATION, activated_governance]
  0.7.0: [0.6.0, P11_REFACTOR, activated_governance]
  0.8.0: [0.7.0, P12_PRIVACY, activated_governance]
  0.9.0: [0.8.0, P13_RELATIONAL_MODEL, P14_TRANSLATION, activated_governance]
  0.10.0: [0.9.0, P15_SHADOW_MIGRATION, activated_governance]
  0.11.0: [0.10.0, P16_TRANSITION, activated_governance]
  1.0.0: [0.11.0, P17_MCP_STABILIZATION, P18_FINAL, all_applicable_final_governance]
```

`START_READY` resolves to B0 for `GREENFIELD` and BR0 for `BROWNFIELD`. `activated_governance` contains active `MERGE_GUARD` and current-release `RELEASE_GUARD` requirements after structured applicability evaluation. `all_applicable_final_governance` adds active final-release governance without activating `DEPLOYMENT_GUARD` unless deployment qualification is explicitly requested. Under `LOCAL_QUALIFICATION`, remote-integration/publication-only requirements are deterministically not applicable and the full release lineage through qualified `1.0.0` remains reachable without remote writes. `REMOTE_INTEGRATION` activates authorized remote integration guards, and `PUBLICATION` additionally activates public-release obligations.

The milestone map owns phase activation. A requirement can live physically in an earlier or later document phase for architectural grouping while becoming release-blocking only when selected by a canonical milestone or governance closure.

---

# 8. Dependency order

```text
GREENFIELD                           BROWNFIELD
    |                                   |
G00 start-state/bootstrap          brownfield baseline
    |                                   |
B0 repository foundation          compatibility preservation
    |                                   |
    +-----------------+-----------------+
                      |
                    P00 domain/platform/pins
                      |
                    P01 Core + early MCP
                      |
                    P02 Windows safety
                      |
          P2A autonomous verification governance
             (cross-cutting from this point onward)
                      |
                    P03 VFP9 SP2 knowledge
                      |
                    P04 DBF/FPT data plane
                      |
            +---- release 0.4.0: Data & Help Explorer
                      |
                    P05 semantic graph
                      |
                    P06 FoxBin analysis bridge
                      |
                    P07 forms/classes
                      |
                    P08 DBC/views/unified data model
                      |
                    P09 cross-domain questions
                      |
            +---- release 0.5.0: Application Analyzer
                      |
                    P10 VFP runtime + optimization
                      |
            +---- release 0.6.0: Optimization Assistant
                      |
                    P11 compile/build + controlled refactoring
                      |
            +---- release 0.7.0: Safe Refactoring
                      |
                    P12 privacy/anonymization
                      |
            +---- release 0.8.0: Privacy Workflows
                      |
                    P13 relational target model
                      |
                    P14 SQL/xBase translation
                      |
            +---- release 0.9.0: PostgreSQL Relational Designer
                      |
                    P15 PostgreSQL shadow migration
                      |
            +---- release 0.10.0: Shadow Migrator
                      |
                    P16 VFP/PostgreSQL transition
                      |
            +---- release 0.11.0: Transition Assistant
                      |
                    P17 complete MCP contract stabilization
                      |
                    P18 complete-system acceptance
                      |
            +---- release 1.0.0
```

This order keeps migration dependent on application understanding rather than treating DBF conversion as a standalone file-copy task.

---

# 9. Progressive release matrix

| Gate / Release | Practical use | Main capability set | Later work still absent |
|---|---|---|---|
| B0 | repository foundation | greenfield bootstrap, package/test/docs/CI/portable verification foundation | product capabilities |
| 0.4.0 | inspect real VFP data immediately | DBF/FPT/Memo, Help, profiles, value search, original/anonymized datasets | whole-app semantics, optimization, refactor, PostgreSQL |
| 0.5.0 | investigate existing VFP applications | symbols, references, forms/classes, DBC, relations, impact, question context | runtime optimization, writes/refactor, PostgreSQL |
| 0.6.0 | optimize existing applications | CDX/IDX, Rushmore, SYS(3054), benchmark/performance evidence | controlled refactor, PostgreSQL |
| 0.7.0 | safely change VFP code/forms | workspace refactor, FoxBin2Prg round-trip, VFP compile/build, semantic diff | privacy workflows, PostgreSQL |
| 0.8.0 | create and analyze privacy-safe datasets | DBF_Anonymizer integration, lineage, verification, bundles | PostgreSQL modernization |
| 0.9.0 | design the future PostgreSQL database | relational target model, DDL, keys/FKs/indexes, SQL/xBase translation | target data loading |
| 0.10.0 | build a verified PostgreSQL shadow | streaming migration, resume, parity validation, cross-engine comparisons | production transition |
| 0.11.0 | migrate bounded application slices | ODBC/SPT/remote-view/CursorAdapter transition, reconciliation, rollback/cutover plans | complete contract freeze |
| 1.0.0 | complete modernization platform | unified stable MCP surface and complete acceptance evidence | normal post-1.0 evolution |

Every published version remains useful on its own. A later release expands the same Core/MCP architecture rather than replacing it with a parallel implementation.

---

# 10. Authority and responsibility boundaries

```text
MCP client / reasoning model
            |
            v
       MCP adapter
            |
            v
   VFPToolchain Core Service
      /       |        \
     /        |         \
data/query  semantics   refactor
   |          |            |
dbfbridge   VFPX Help      +--> FoxBin2Prg
   |        + parser       +--> VFP9 SP2
   |
   +--> DBF_Anonymizer
   |
   +--> RelationalTargetModel --> PostgreSQL
```

`dbfbridge` owns low-level DBF/FPT Direct Read and Direct Write mechanics.

`DBF_Anonymizer` owns reversible pseudonymization, recovery-vault behavior, dataset verification and transfer-bundle privacy logic.

FoxBin2Prg owns canonical bidirectional conversion between supported VFP binary designer/project/database artifacts and text representations.

VFPX HelpFile supplies the local VFP9 SP2 language/object/documentation corpus.

`mcp-vfp9sp2-toolchain` owns project/dataset context, semantic modeling, relationship discovery, data questions, form understanding, impact analysis, optimization evidence, controlled refactoring, PostgreSQL target modeling, migration validation, Windows isolation and MCP transport.

---

# 11. Reproducible dependency and configuration model

Compatibility ranges and architecture baselines are separate concepts:

```text
Source of Truth architecture baseline
        |
        v
approved exact direct baseline
        |
        +--> compatibility range remains broader
        |
        v
fully resolved immutable dependency lock
        |
        +--> transitive artifact hashes
        +--> wheelhouse
        +--> SBOM / license inventory
        +--> release provenance
```

Initial architecture baselines in this revision include:

```text
dbfbridge          1.1.1
DBF_Anonymizer     1.0.0.dev0 @ 02763d7c34b19335e560ef9597a54aed7790968d
MCP protocol       2026-07-28
MCP Python SDK     2.2.0
MCP conformance    @modelcontextprotocol/conformance@0.2.0-alpha.10 / requirements 2026-07-28
Psycopg             3.3.6
PostgreSQL server   18.6
psqlODBC            REL-18_00_0002 (32-bit trusted VFP transition profile)
```

A later baseline is adopted through verified dependency evolution, not merely because an upstream package became newer.

Configuration uses a versioned schema. Effective configuration is a deterministic, redacted, hashable product input rather than hidden process state.

Microsoft VFP9 SP2 assets are local/operator-provided unless documented redistribution rights exist for a specific asset.


---
---

# 12. Canonical artifacts and offline source acquisition

The minimal supported initial filesystem can be exactly:

```text
PROJECT_HOME\
  <operator-selected SOT file>
```

Everything else can be absent. The operator/build system supplies `PROJECT_HOME` and `bootstrap_sot_path`; the bootstrap derives or creates the remaining workspace roles as needed.

The pre-repository bootstrap boundary is logical rather than file-based:

```json
{
  "project_home": "D:\\Opencode projects\\Project VFP",
  "bootstrap_sot_path": "D:\\Opencode projects\\Project VFP\\MCP_VFP9SP2_TOOLCHAIN_SOURCE_OF_TRUTH.md"
}
```

The JSON above is only an illustrative serialization. A CLI, UI, API, or other adapter can supply the same two operator-provided logical values. Absolute machine paths belong to run control/evidence, not the portable product contract.


`REPO_ROOT` occupancy is interpreted as follows:

| REPO_ROOT state | Start interpretation | Mutation before classification |
| --- | --- | --- |
| does not exist | GREENFIELD | creation allowed after inspection |
| exists and is empty | GREENFIELD | creation allowed after inspection |
| verified partial bootstrap for the same SOT/root | GREENFIELD resume | only idempotent resume writes |
| recognizable target product with clean committed Git baseline | BROWNFIELD | external pre-mutation baseline first |
| recognizable target product without clean committed Git baseline | AMBIGUOUS | no writes; operator remediation |
| any other non-empty content | AMBIGUOUS | no writes until explicit decision |

The presence of Converge, another Git repository, TEMP, venv, caches, logs, or other sibling content under `PROJECT_HOME` does not change this table.

For brownfield, Git-ignored local files inside `REPO_ROOT` are not automatically product state. They are treated as non-authoritative local state, admitted only under deterministic repository-scoped ignore evaluation and protected from bootstrap-path collisions or cleanup.

The execution workspace has two distinct scopes:

```text
PROJECT_HOME  = operator-selected absolute Windows directory
REPO_ROOT     = PROJECT_HOME\mcp-vfp9sp2-toolchain
```

`PROJECT_HOME` is an execution container, not a Git/source root. It can contain sibling tools and ephemeral state. `REPO_ROOT` is the only canonical target-repository root.

The canonical public repository identity is `https://github.com/PeterPirog/mcp-vfp9sp2-toolchain`. Local greenfield development can begin without a remote; brownfield forks or mirrors remain distinguishable from the canonical production destination.

A valid non-normative example matching the established operator workflow is:

```text
D:\Opencode projects\Project VFP\
  MCP_VFP9SP2_TOOLCHAIN_SOURCE_OF_TRUTH.md   possible sole initial file
  Converge\                         optional orchestration tool/checkout
  SOT\                              optional alternative SOT location
  TEMP\                             optional execution scratch
  .venv\                            optional Python virtual environment
  cache\                            optional dependency/source cache
  other-repository\                 optional unrelated clone
  mcp-vfp9sp2-toolchain\            REPO_ROOT
    spec\
    execution-profiles\
    release-gates\
    evidence\
    third_party\
    src\
    tests\
    docs\
    tools\
    .github\
```

The drive letter and `PROJECT_HOME` absolute path are not normative. The operator/build system chooses them; all target-project operations remain explicitly rooted at `REPO_ROOT`.


The first committed repository is self-describing. The exact Source of Truth and its portable derived control plane live at fixed paths:

```text
spec/
  SOURCE_OF_TRUTH.md
  requirements.graph.json
  verification.manifest.json
  compatibility.manifest.json
  acquisition.manifest.json
  dependency-lock.json
  threat-model.json
  schemas/
    requirement-graph.schema.json
    verification-manifest.schema.json
    compatibility-manifest.schema.json
    acquisition-manifest.schema.json
    dependency-lock.schema.json
    threat-model.schema.json
    bootstrap-invocation.schema.json
    brownfield-start-baseline.schema.json
    release-gate.schema.json
    evidence-index.schema.json
    capability-snapshot.schema.json
    provenance-record.schema.json
    execution-profile.schema.json

execution-profiles/
  converge.yaml
  generic.json

release-gates/
evidence/
third_party/
src/vfp_toolchain/
tests/
docs/
tools/
.github/workflows/
```

Portable logical artifacts remain authoritative across execution tools. A runner-specific lock, CI file, cache, or orchestrator configuration can coexist only as a derived or auxiliary representation.

```text
Source of Truth
      |
      +--> canonical requirement graph
      +--> canonical verification manifest
      +--> canonical compatibility/acquisition/dependency manifests
      +--> canonical release-gate manifests
      |
      v
RFC 8785 / canonical logical JSON hashes
```

External source preparation follows one identity model:

```text
connected preparation -> approved immutable origin -> verify -> local cache
offline preparation   -> preseeded local cache      -> verify
runtime request       -> no dependency acquisition
```

Non-Python release assets are tracked separately from proprietary operator-provided VFP assets.

---

# 13. Evidence hierarchy

```text
VFP9_RUNTIME_CONFIRMED
FOXBIN2PRG_CANONICAL
VFPX_HELP_VFP9SP2
DBFBRIDGE_DIRECT
DBC_DECLARED
PURE_PARSER
SOURCE_OBSERVED
DATA_PROFILED
INFERRED_HIGH
INFERRED_LOW
HEURISTIC_CDX
UNRESOLVED_DYNAMIC
```

Evidence types verify different dimensions. Disagreement remains visible instead of disappearing behind a global precedence rule.

---

# 14. Windows trust zones

```text
ZONE A — immutable VFP application source
ZONE B — registered ORIGINAL / ANONYMIZED datasets
ZONE C — analysis state and value-redacted caches
ZONE D — scratch and ephemeral relational workspaces
ZONE E — VFP refactor workspace
ZONE F — ordinary output and migration artifacts
ZONE G — sensitive recovery vault
ZONE H — isolated PostgreSQL shadow / migration target
```

Write activity stays outside immutable source zones until an explicit promotion path.

---

# 15. Target architecture modules

```text
vfp_toolchain
  core / models / errors / capabilities / policy / jobs
  project / datasets
  knowledge
  language / semantic
  forms
  analysis / performance
  backends
  vfp_runtime
  refactor
  privacy
  relational
  postgres
  mcp
```

Transport adapters remain thin. Domain behavior stays in the Core layers.

---

# 16. Data-question flow

```text
dataset_id
   |
dbfbridge streaming read
   |
schema + records + Memo
   |
profiles + relations
   |
bounded query engine
   |
traceable result
   |
question context for MCP client model
```

Rows, aggregates and relation evidence retain source dataset/table/field identities.

---

# 17. Form-analysis and refactor flow

```text
SCX/SCT or VCX/VCT
        |
pure evidence + FoxBin2Prg BIN2PRG
        |
normalized form/class model
        |
semantic graph + impact
        |
workspace RefactorPlan
        |
structured SC2/VC2 edit
        |
FoxBin2Prg PRG2BIN
        |
VFP9 SP2 compile/build
        |
final BIN2PRG
        |
semantic before/after validation
        |
export or explicit promotion
```

Original designer binaries stay outside first-party direct patch logic.

---

# 18. Relational modernization flow

```text
VFP application + datasets
        |
semantic graph / DBC / CDX / data profiles
        |
RelationalTargetModel
        |
PostgreSQL schema and SQL translation
        |
shadow target
        |
streaming DBF/FPT migration
        |
structural / data / relation / query parity
        |
bounded VFP feature transition
        |
cutover and rollback planning
```

A discovered VFP relation and an enforced PostgreSQL foreign key remain separate concepts until validation promotes the relation.

---

# 19. PostgreSQL migration separation

```text
SCHEMA EVOLUTION
  deterministic DDL
  versioned revisions
  constraints and indexes

DATA MOVEMENT
  dbfbridge streaming
  typed conversion
  Psycopg COPY
  checkpoint/resume
  validation
```

Schema revision history and bulk data movement remain independent workflows.

---

# 20. Portable autonomous verification model

```text
immutable Source of Truth
        |
        v
portable requirement set / Converge contract.json
        |
        +--> exact mandatory requirement ID set
        |
        v
verification manifest
        |
        +--> REQ -> deterministic verifier(s)
        +--> fixture/capability profile
        +--> release-gate dependencies
        |
        v
candidate change
        |
        +--> target verifier
        +--> full deterministic quality gates
        +--> all previously PASS mandatory verifiers
        +--> independent correctness review
        +--> independent architecture review
        +--> independent security review
        +--> GitHub CI status checks
        |
        v
merge
        |
        v
release-gate verifier
        |
        +--> exact prerequisite closure
        +--> all previous release smoke suites
        +--> clean package install
        +--> official MCP client smoke
        +--> provenance/artifact checks
        |
        v
publish
```

No model-generated statement is release evidence by itself. Machine-verifiable evidence and retained provenance decide PASS.

The verification system treats tests as part of the protected architecture surface. Removing or weakening a failing test is not a valid repair.

---

# 21. Publication philosophy

Repository value appears before the complete modernization target.

The first publication solves DBF/FPT and VFP9-SP2 knowledge problems.

The next publication solves whole-application understanding.

Later publications add optimization, refactoring, privacy, relational design, shadow migration and production transition.

The complete 1.0 package is a maturity point, not the first useful package.

Qualification and publication are separate states: every release version can be fully qualified locally, while public GitHub integration and publication occur only under an explicitly authorized operation scope and reference the same qualified artifacts.

Remote integration is independent of whether GitHub branch protection is enabled. Native protection/rulesets, when present, add enforced constraints; when absent, the trusted integration layer supplies gate sequencing and race-safe fast-forward behavior without changing repository policy.

Authoring mode is orthogonal to repository integration mode: manual, autonomous, and hybrid candidates use the same product/verifier/release contract. Native protected integration can yield a policy-derived merge/squash/rebase commit, so candidate qualification transfers only through explicit tree-equivalence evidence; a changed integration tree is requalified before publication.

Independent review is implementation-neutral. Supported reviewer classes are human, model-based, deterministic-tool-based, and composite. Manual authoring remains usable without an LLM or coding agent; autonomous authoring uses a separate non-authoring review execution.

Execution control is separate from authoring semantics. Manual mode defaults to the portable generic profile and uses human-operated documented procedures without an autonomous orchestrator; autonomous mode defaults to Converge; hybrid mode defaults to generic and can explicitly attach Converge or another conforming agent bridge.

The autonomous controller is not assumed to pre-exist inside `PROJECT_HOME`. A minimal pre-controller bootstrap can verify an explicitly bound controller or provision the pinned adapter from an approved connected source or matching offline cache, then hands off the unchanged bootstrap identity before any product mutation.

The controller code and the model routes are separate dependencies. The controller can be pinned by commit/tree while each autonomous run freezes an exact model-routing snapshot only after validating the role contract and the currently bound provider/gateway; no model vendor is part of product semantics.

The autonomous runtime configuration is a third, separate bootstrap dependency: it is generated outside the target repository from frozen bootstrap identities after B0/BR0 and before controller launch. This removes the circular assumption that `converge.yaml` or a controller-runnable Git repository already exists at time zero.

For model-authored execution, the external frozen Source of Truth is also a protected execution input: runtime configuration points to it read-only, while the trusted bootstrap layer retains the only authority needed to manage the protection boundary outside the model-authored process.

The manual generic profile is likewise not assumed to pre-exist. Before it exists, the frozen Source of Truth itself carries `MANUAL_BOOTSTRAP_V1`; after B0/BR0, the committed generic profile and canonical control plane take over.

---

# 22. Execution profiles

The Source of Truth is independent of the coding tool. Execution profiles bind the same contract to a concrete runner.

```text
Source of Truth
      |
      v
portable requirement set
      |
      v
portable verification manifest
      |
      +--> embedded MANUAL_BOOTSTRAP_V1 (time zero only)
      |
      +--> generic adapter (default after bootstrap for MANUAL / HYBRID)
      |
      +--> Converge adapter (default for AUTONOMOUS)
      |
      +--> alternative conforming adapter
```

## 22.1 Time-zero manual bootstrap reference

`MANUAL_BOOTSTRAP_V1` is the logical reference consumed directly from this frozen Source of Truth before repository-local profiles or scripts exist.

```yaml
manual_bootstrap_v1:
  inputs:
    - project_home
    - bootstrap_sot_path
  defaults:
    operation_scope: LOCAL_QUALIFICATION
    authoring_mode: MANUAL
    execution_adapter_after_bootstrap: generic
  host_baseline:
    - windows
    - git
    - supported_python
  phases:
    - bind_and_canonicalize_inputs
    - hash_source_of_truth
    - derive_repo_root
    - inspect_and_classify_before_mutation
    - prepare_start_mode_workspace
    - materialize_exact_source_of_truth
    - build_bootstrap_control_plane_candidate
    - generate_generic_profile_and_verifier_dispatch
    - seal_candidate_tree
    - run_bootstrap_preflight
    - create_or_advance_trusted_local_bootstrap_commit
    - verify_committed_tree_and_working_state
    - evaluate_B0_or_BR0
    - handoff_to_committed_generic_profile
  time_zero_external_project_artifacts: []
  autonomous_controller_dependency: none
```

## 22.2 Time-zero autonomous bootstrap reference

`AUTONOMOUS_BOOTSTRAP_V1` prepares only the deterministic controller-runnable bootstrap seed and external runtime configuration. Product-feature implementation starts after B0/BR0 and controller/model preflight.

```yaml
autonomous_bootstrap_v1:
  inputs:
    - project_home
    - bootstrap_sot_path
    - model_routing_binding
  defaults:
    operation_scope: LOCAL_QUALIFICATION
    authoring_mode: AUTONOMOUS
    execution_adapter: converge
  phases:
    - bind_and_canonicalize_inputs
    - hash_source_of_truth
    - derive_and_classify_repo_root
    - acquire_and_verify_controller
    - resolve_and_freeze_model_routing
    - create_or_prepare_bootstrap_seed
    - seal_and_verify_bootstrap_candidate
    - run_bootstrap_or_brownfield_preflight
    - create_or_advance_trusted_bootstrap_seed_commit
    - evaluate_B0_or_BR0
    - generate_external_controller_runtime_config
    - establish_and_verify_external_sot_write_protection
    - run_controller_environment_preflight
    - run_autonomous_model_preflight
    - handoff_seed_config_protection_and_routing
  product_feature_mutation_before_handoff: disabled
  runtime_config_location: outside_repo_root
```

## 22.3 Autonomous model-role reference

`AUTONOMOUS_MODEL_ROLE_CONTRACT_V1` separates stable logical roles from run-specific provider/model routing.

```yaml
autonomous_model_role_contract_v1:
  roles:
    - SCOUT
    - PLANNER
    - BUILDER
    - CORRECTNESS_REVIEWER
    - ARCHITECTURE_REVIEWER
    - SECURITY_REVIEWER
  routing_identity_scope: per_run
  provider_model_ids: execution_profile_data
  fallback_policy: finite_ordered
  implicit_best_available_selection: disabled
  secrets_in_snapshot: disabled
```

Every adapter preserves:

```text
requirement ID
requirement meaning
deterministic verifier meaning
evidence class
release-gate membership
PASS / FAIL semantics
```

The implementation tool can differ. The product contract remains unchanged.

---

# 23. Greenfield bootstrap model

For `MANUAL`, the first control path is the embedded `MANUAL_BOOTSTRAP_V1`; for `AUTONOMOUS`, the first control path is embedded `AUTONOMOUS_BOOTSTRAP_V1`, which creates only a controller-runnable B0/BR0 seed plus external runtime configuration before handing off to the pinned controller. Repository-local execution profiles become authoritative only after their bootstrap candidate is committed and the applicable readiness gate passes.

For a completely empty target repository:

```text
empty target
   |
   v
start-state classification = GREENFIELD
   |
   v
canonical package / tests / docs / CI / portable manifests
   |
   v
truthful empty capability state
   |
   v
Bootstrap Gate B0
   |
   v
Phase 0 and normal requirement graph
```

Bootstrap establishes infrastructure only. It does not simulate future VFP capabilities.

---

# 24. Brownfield transition model

The current repository baseline already contains `src/vfp_toolchain`, CLI/OpenCode adapters, knowledge files, vendored dependencies and partial audit tooling.

Transition logic:

```text
clean committed target_ref
      |
      v
external BROWNFIELD_PREFLIGHT
(no REPO_ROOT mutation)
      |
      v
isolated candidate tree/worktree
      |
      +--> retained start baseline
      +--> canonical SOT/control plane
      +--> brownfield dependency lock
      |
      v
BROWNFIELD_BOOTSTRAP_PREFLIGHT
      |
      v
trusted bootstrap commit
(parent = original HEAD)
      |
      v
fast-forward target_ref
+ clean REPO_ROOT
      |
      v
BR0
      |
      +--> keep compatible working behavior
      +--> mark stale documentation
      +--> isolate legacy vendored integrations
      +--> introduce target public dependency adapters
      +--> prove parity / intentional supersession
      |
      v
progressive release gates
```

Repository documentation describes current implementation state. The Source of Truth defines target product behavior.

---

# 25. Default Converge execution profile

Earlier pre-freeze IDs were superseded before the stable contract was established because their physical phase ordering did not match architecture dependencies. From the current stable contract onward, ID evolution follows the explicit contract-evolution rules.

At autonomous controller handoff, the external frozen Source of Truth is protected by an OS-enforced write boundary for the model-authored execution identity; its byte hash remains unchanged and Converge receives `project.require_spec_read_only: true`.

The default Converge execution profile maps the portable verification manifest to `converge.yaml` requirement verifiers. Other coding tools use equivalent adapters. In every profile, incomplete mandatory-verifier coverage is a preflight failure. Release-gate verifiers provide usable stopping points and prevent later unfinished work from blocking publication of earlier proven capability sets.

End of Source of Truth.
