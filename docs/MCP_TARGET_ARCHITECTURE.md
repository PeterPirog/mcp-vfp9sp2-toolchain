# MCP-ready target architecture for vfp-integration-toolchain

Status: architectural contract. MCP transport is **not implemented yet**.

Target host:

```text
Windows
Microsoft Visual FoxPro 9.0 SP2 installed for enhanced/runtime/write capabilities
Python 3.10+
Offline-capable knowledge and data tooling
```

Target dialect:

`microsoft.visual-foxpro.9.0.sp2`

## 1. Architectural decision

Do not build business logic directly into OpenCode TypeScript tools and later rewrite it for MCP.

Use this structure:

```text
                    +--------------------+
                    | OpenCode adapter   |  current
                    +---------+----------+
                              |
                    +---------v----------+
                    | Core service API   |
                    | typed JSON models  |
                    +---------+----------+
                              |
              +---------------+----------------+
              |                                |
     +--------v---------+             +--------v---------+
     | Pure Python READ |             | VFP9 adapter     |
     | no VFP required  |             | Windows/VFP COM  |
     +--------+---------+             +--------+---------+
              |                                |
     DBF/FPT/designer tables          FoxBin2Prg/runtime/compiler
     static parser/knowledge          COMPILE/BUILD/REINDEX/SYS()
     hashes/index heuristics
              |
     +--------v---------+
     | Privacy services |
     | dbfbridge + anon |
     +------------------+

Future:

                    +--------------------+
                    | MCP server adapter |
                    +---------+----------+
                              |
                    same Core service API
```

MCP is a transport layer, not the domain layer.

## 2. Capability classes

Every operation must declare one of these runtime requirements:

```text
PURE_READ
PURE_WRITE_COPY
VFP_READ_ENHANCED
VFP_WRITE_WORKSPACE
VFP_BUILD_VALIDATE
PRIVACY_SENSITIVE
```

### PURE_READ

Must work without Visual FoxPro installed.

Examples:

```text
artifact detection
file inventory
SHA256 manifests
PRG/H text search
DBF/FPT schema read
DBF/FPT data read/export
SCX/VCX/FRX/LBX/MNX/PJX/DBC raw table/memo read
static method/property extraction where possible
CDX/IDX structural heuristic read
local knowledge lookup
known-issue lookup
source dependency scanning
encoding/code-page analysis
```

### PURE_WRITE_COPY

Writes only new output/copies and does not require VFP where file semantics do not require VFP rebuild.

Examples:

```text
JSON/JSONL/CSV/XLSX export
reports/manifests
safe copied DBF/FPT reconstruction through dbfbridge
anonymization of tables that do not require VFP CDX rebuild
```

### VFP_READ_ENHANCED

Requires installed VFP9 SP2, but must remain source-read-only.

Examples:

```text
FoxBin2Prg BIN2PRG canonical text export
ALANGUAGE/AMEMBERS runtime inventory
runtime CDX/tag introspection
DBC runtime introspection
SYS(3054) query/Rushmore profiling
compile-only scratch syntax validation
```

### VFP_WRITE_WORKSPACE

Requires VFP9 SP2 and an explicit isolated workspace.

Examples:

```text
apply SCX/SCT method patch to copy
REINDEX anonymized/copied DBF
index experiments on copied tables
controlled DBC changes on copies
```

### VFP_BUILD_VALIDATE

Requires VFP9 SP2 and an explicit isolated workspace.

Examples:

```text
COMPILE
COMPILE FORM
BUILD PROJECT/APP/EXE/DLL
reopen form/class/report
final FoxBin2Prg round-trip
smoke/regression validation
```

### PRIVACY_SENSITIVE

Operations handling reversible anonymization dictionaries or original sensitive values.

They need stronger path/log/output policies regardless of whether VFP is required.

## 3. READ without Visual FoxPro — mandatory design goal

A missing VFP installation must not disable read-only project inspection.

The pure backend must understand that VFP designer/project/database artifacts are table-based files with memo companions and should expose structured READ access without using VFP COM.

Required artifact families:

```text
DBF + optional FPT/CDX/IDX
SCX + SCT
VCX + VCT
FRX + FRT
LBX + LBT
MNX + MNT
PJX + PJT
DBC + DCT + DCX
PRG / H / MPR and other textual code
```

The pure reader should expose raw/normalized records and text memo fields. It must not pretend that binary OBJCODE or other binary payloads are source text.

For each result report provenance/confidence:

```text
PURE_PARSER
FOXBIN2PRG
VFP9_RUNTIME
HEURISTIC_CDX
```

When VFP is available, enhanced results can supersede/verify pure-read results without changing the public response schema.

## 4. FoxBin2Prg role

FoxBin2Prg is the preferred canonical semantic text converter for VFP binary designer artifacts when VFP9 is available.

Upstream:

`https://github.com/fdbozzo/foxbin2prg`

Current upstream README describes support for:

```text
PJX/SCX/VCX/FRX/LBX/DBC/DBF/MNX
<->
PJ2/SC2/VC2/FR2/LB2/DC2/DB2/MN2
```

The toolchain source-analysis plane must use only BIN2PRG against source.

Future PRG2BIN/write usage, if ever enabled, must occur only in a controlled workspace and is not the default refactoring mechanism.

For offline deployment, maintain a pinned, license-attributed FoxBin2Prg dependency strategy. Do not silently download latest upstream code at runtime.

## 5. dbfbridge role

`dbfbridge` is the core data-format layer.

Upstream:

`https://github.com/PeterPirog/dbfbridge`

It already provides a typed Python API suitable for a future service/MCP backend:

```text
export_dbf()
reconstruct_dbf()
verify_conversion()
check_conversion_quality()
```

Key architectural benefits:

- no VFP required for DBF/FPT read/export/reconstruction,
- streaming JSONL path,
- schema metadata,
- memo handling,
- Polish cp1250/cp852/Mazovia support,
- checksums/manifests,
- canonical/raw round-trip diagnostics,
- structured result objects rather than console scraping.

The current repository already vendors a pinned dbfbridge snapshot. Keep this model for offline reproducibility, but provide a deterministic update script and provenance manifest rather than manual copying.

## 6. DBF_Anonymizer role

Upstream:

`https://github.com/PeterPirog/DBF_Anonymizer`

The anonymizer is a natural privacy subsystem of this toolchain.

Its public Python API includes:

```text
anonymize_directory()
make_dbf_recovery()
self_test()
```

Useful characteristics:

- global deterministic mapping across tables,
- preservation of text-key relationships,
- byte-length-aware Character pseudonyms,
- reversible SQLite dictionary,
- memo masking/keeping,
- date/datetime offset support,
- staging + atomic publication,
- DBF export/reconstruction through dbfbridge,
- VFP REINDEX for structural CDX output,
- round-trip self-test.

Do not duplicate this logic inside `vfp-integration-toolchain`. Integrate it through a stable adapter/service boundary.

## 7. Offline dependency model

The production/offline toolchain must not `pip install` or `git clone` dependencies at request time.

Preferred dependency layout:

```text
third_party/
  dbfbridge/
      source snapshot
      LICENSE
      VERSION.txt
  dbf_anonymizer/
      source snapshot
      LICENSE
      VERSION.txt
  foxbin2prg/
      source/runtime snapshot or configured local installation
      LICENSE/attribution
      VERSION.txt
  vfpx_help/
      normalized offline corpus or pinned source snapshot/index
      LICENSE/attribution
      VERSION.txt
```

Existing `tools/dbfbridge/` may remain during transition, but the long-term layout should separate third-party/vendored code from first-party tool adapters.

Every dependency snapshot must record:

```text
upstream URL
upstream commit
package/version
license
vendored date
SHA256 manifest
local modifications, if any
```

## 8. Core service layer

Create a transport-neutral Python package, for example:

```text
src/vfp_toolchain/
  service.py
  models.py
  capabilities.py
  errors.py
  safety.py
  knowledge/
  read/
  vfp_runtime/
  data/
  privacy/
  refactor/
  performance/
```

The service layer returns typed JSON-serializable results and does not print UI text.

Both current CLI/OpenCode tools and future MCP tools call this layer.

## 9. Stable operation contract

Every operation returns a common envelope:

```json
{
  "status": "PASS|PARTIAL|FAIL",
  "operation": "...",
  "requires": ["PURE_READ"],
  "backend": "PURE_PYTHON|VFP9_RUNTIME|FOXBIN2PRG|DBFBRIDGE|DBF_ANONYMIZER",
  "sourceModified": false,
  "warnings": [],
  "errors": [],
  "artifacts": [],
  "data": {}
}
```

Use machine-readable error codes instead of parsing prose.

Examples:

```text
VFP9_NOT_INSTALLED
VFP9_WRONG_VERSION
SOURCE_WRITE_FORBIDDEN
SOURCE_HASH_CHANGED
MISSING_COMPANION
MISSING_FPT
MISSING_STRUCTURAL_CDX
CDX_REBUILD_REQUIRES_VFP9
ANON_DICTIONARY_SENSITIVE
ANON_DICTIONARY_MISMATCH
KNOWLEDGE_INCOMPLETE
HEURISTIC_RESULT
```

## 10. Future MCP surface

When MCP is implemented, expose only thin tool/resource adapters.

Recommended MCP resources:

```text
vfp://knowledge/status
vfp://knowledge/language/<name>
vfp://knowledge/issues/<id>
vfp://project/<id>/manifest
vfp://project/<id>/audit
vfp://project/<id>/form/<name>
vfp://project/<id>/table/<name>/schema
vfp://project/<id>/indexes/<table>
```

Recommended MCP tools:

```text
vfp_capabilities
vfp_detect
vfp_snapshot
vfp_read_artifact
vfp_read_table_schema
vfp_read_table_data
vfp_audit
vfp_find_symbol
vfp_find_references
vfp_analyze_indexes
vfp_analyze_performance
vfp_anonymize
vfp_anonymization_self_test
vfp_validate_snippet
vfp_create_refactor_workspace
vfp_apply_refactor_plan
vfp_validate_form
```

MCP resources should be read-only. Mutating operations remain MCP tools with explicit path/safety policy.

## 11. Capability discovery

Before using an operation, clients should be able to call:

```text
vfp_capabilities
```

Example response:

```json
{
  "platform": "windows",
  "python": true,
  "vfp9": {
    "installed": true,
    "version": "9.0.0.7423"
  },
  "foxbin2prg": true,
  "dbfbridge": true,
  "anonymizer": true,
  "modes": {
    "pureRead": true,
    "vfpEnhancedRead": true,
    "workspaceWrite": false,
    "buildValidate": false
  }
}
```

When VFP is absent:

```json
{
  "modes": {
    "pureRead": true,
    "vfpEnhancedRead": false,
    "workspaceWrite": false,
    "buildValidate": false
  }
}
```

Pure READ operations must still be available.

## 12. Project sessions vs global server state

Future MCP requests must not rely on a single mutable VFP global environment shared between clients.

Represent each audited project/workspace with an explicit project/session identifier and paths.

Do not keep these implicitly global:

```text
current project
current work area
current SET state
current VFP application object
current workspace
```

VFP COM execution should be serialized or isolated per worker because VFP has process/global state and work-area state.

## 13. VFP process pool policy

Do not launch one uncontrolled VFP instance for each tiny request forever, and do not share one mutable instance between unrelated projects.

Future design should support a small supervised worker pool:

```text
worker -> dedicated VFP9 COM instance -> one job at a time
```

Each job initializes a known environment and tears down/clears project-specific state.

A worker may be recycled after N jobs or on runtime contamination/failure.

Never globally kill all `vfp9.exe` processes.

## 14. Path-security model

For a server/MCP architecture path security is mandatory.

Define configured roots:

```text
allowedReadRoots
allowedOutputRoots
allowedWorkspaceRoots
sensitiveDictionaryRoots
```

Canonicalize Windows paths and reject traversal/symlink/junction escapes.

Source paths are immutable by default.

Write-capable tools must receive a separate workspace/output path and must never infer permission merely because a path is writable by Windows.

## 15. Sensitive data/logging model

Default logs/results must not echo full DBF field values.

For anonymization especially:

- dictionary path is sensitive,
- original values must not appear in error messages unless explicitly requested in a secure diagnostic mode,
- salts/secrets must never be committed,
- `dictionary.sqlite3` must be excluded from Git and general audit exports,
- recovery operation should require explicit opt-in.

## 16. Pure-read designer parser roadmap

To meet the no-VFP READ requirement, implement direct read-only parsers for VFP table-based designer artifacts.

Initial approach:

1. use dbfbridge/dbfread-level table and memo reading,
2. use locally vendored VFP9 Help/file-format knowledge,
3. map known fields to normalized artifact records,
4. parse textual memo fields (`METHODS`, `PROPERTIES`, expressions, names),
5. retain unknown/binary fields losslessly as metadata/hash, not fabricated source,
6. compare pure-parser output with FoxBin2Prg on fixtures when VFP is available.

FoxBin2Prg remains the canonical enhanced reference, but READ availability does not depend on it.

## 17. Two-backend verification strategy

For files readable both ways:

```text
PURE PARSER
    vs
FOXBIN2PRG/VFP9
```

Build conformance fixtures and compare:

```text
object count
object names/classes
method names/source hashes
property names/values
DataEnvironment objects
project file entries
report/menu structures
```

Differences become parser issues, not silently accepted discrepancies.

## 18. Anonymization capability split

`vfp_anonymize` must advertise whether a job requires VFP.

### No structural CDX

```text
DBF/FPT -> dbfbridge -> anonymizer -> reconstructed DBF/FPT
```

Can operate without VFP when all required file semantics can be reconstructed safely.

### Structural CDX present

Output must have rebuilt indexes after changed indexed values.

Preferred:

```text
copy definitions/metadata -> anonymize DBF/FPT -> VFP9 REINDEX on output copy -> verify tags
```

Without VFP:

```text
status = PARTIAL/UNAVAILABLE_FOR_VALID_CDX_OUTPUT
errorCode = CDX_REBUILD_REQUIRES_VFP9
```

Do not ship stale source CDX as if it matched anonymized data.

## 19. Anonymization and referential consistency

The global dictionary strategy is valuable because the same Character value maps consistently across tables.

However, the integration layer must also detect/consider:

```text
DBC primary/candidate keys
foreign-key-like relations
composite keys
non-character keys
character indexes using expressions
case/collation behavior
field width/code page
memo-based identifiers if present
```

Anonymization success is not proven solely by file reconstruction; validate keys/indexes and application-level smoke tests on an isolated copy.

## 20. Recovery separation

Treat recovery as a separate high-risk capability:

```text
vfp_anonymize          normal privacy operation
vfp_anonymize_verify   normal verification
vfp_recover_data       restricted/high-risk operation
```

The future MCP server should allow administrators to disable `vfp_recover_data` entirely even while anonymization remains enabled.

## 21. Recommended implementation order

### Phase A — architecture extraction

- create transport-neutral Python service package,
- move shared operations out of CLI/OpenCode wrappers,
- implement common result/error/capability schemas,
- retain current behavior.

### Phase B — pure READ

- artifact manifest/hash reader,
- DBF/FPT via dbfbridge,
- direct SCX/VCX/FRX/LBX/MNX/PJX/DBC table readers,
- static parser/indexer,
- no VFP dependency for read APIs.

### Phase C — privacy integration

- vendor/pin DBF_Anonymizer,
- add adapter and typed results,
- add anonymize/self-test tools,
- protect dictionaries/secrets,
- conditional VFP requirement for CDX rebuild.

### Phase D — VFP enhanced backend

- FoxBin2Prg adapter,
- runtime language/index/DBC introspection,
- `SYS(3054)` profiler,
- snippet/compiler validation.

### Phase E — controlled write/build

- workspace safety,
- RefactorPlan,
- form/class/database copy mutation,
- compile/build/round-trip/regression.

### Phase F — MCP adapter

Only after the core service contracts stabilize:

- add MCP server,
- map resources/tools to the same service API,
- add server configuration/security,
- do not duplicate domain logic.

## 22. Definition of architectural success

The architecture is ready for MCP when:

1. all domain operations can be invoked through Python service functions without OpenCode,
2. every operation declares capability/runtime requirements,
3. PURE_READ test suite passes on a machine without VFP,
4. VFP-dependent tests are separately marked/skipped when VFP is absent,
5. output schemas are stable JSON-serializable contracts,
6. source-write safety is enforced below the transport layer,
7. anonymization dictionaries are protected as sensitive artifacts,
8. OpenCode tools are thin adapters,
9. MCP can later be added as another thin adapter.
