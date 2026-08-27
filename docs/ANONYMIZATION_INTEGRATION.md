# DBF anonymization integration for mcp-vfp9sp2-toolchain

Status: architecture contract. **Phase 1 foundation implemented**: the pinned
DBF_Anonymizer 0.3.0 runtime is vendored (`tools/dbf_anonymizer/`), a
`DBFAnonymizerBackend` adapter exists, and a read-only `vfp_anonymization_status`
operation is exposed (CLI + OpenCode). The **controlled mutating tools
(`vfp_anonymize`, `vfp_recover_data`, self-test) are NOT yet exposed** — they
are the next phase, per the security and capability rules below.

Upstream privacy engine:

`https://github.com/PeterPirog/DBF_Anonymizer`

Data layer:

`https://github.com/PeterPirog/dbfbridge`

Target host:

```text
Windows preferred
Python 3.10+
Microsoft Visual FoxPro 9.0 SP2 optional for pure DBF/FPT processing
Microsoft Visual FoxPro 9.0 SP2 required when structural CDX output must be rebuilt/validated
```

## 1. Architectural rule

Do not copy anonymization algorithms into unrelated modules.

Integrate DBF_Anonymizer through a first-party adapter in the toolchain service layer.

Phase 1 implemented this as `src/vfp_toolchain/backends/dbf_anonymizer_backend.py`
(adapting the vendored public API: `anonymize_directory`, `make_dbf_recovery`,
`self_test`) plus the read-only service operation
`VFPToolchainService.anonymization_status()`. A dedicated `privacy/` subpackage
is the intended final home once mutating operations are added.

The future OpenCode and MCP tools call the same privacy service.

## 2. Existing DBF_Anonymizer public API

The upstream package exposes:

```python
anonymize_directory()
make_dbf_recovery()
self_test()
```

The toolchain adapter should use the Python API rather than scrape CLI output.

## 3. Required future service operations

```text
anonymize_data
verify_anonymization
anonymization_self_test
recover_anonymized_data
anonymization_status
```

Suggested public tool names:

```text
vfp_anonymize
vfp_anonymize_verify
vfp_anonymize_self_test
vfp_recover_data
```

`vfp_recover_data` is a restricted/high-risk operation and must be separately configurable.

## 4. Supported privacy semantics inherited from DBF_Anonymizer

Character fields:

- deterministic global mapping,
- same original text maps to the same pseudonym across tables/fields,
- pseudonym keeps the same encoded byte length,
- unique values remain bijective where domain capacity permits,
- NULL/empty values remain unchanged according to upstream behavior.

Memo/General:

- `mask` mode masks values,
- `keep` mode preserves values,
- reversible recovery can use the protected dictionary when masking mode records originals.

Date/DateTime:

- configurable constant date offset,
- DateTime time-of-day preserved by upstream behavior.

Numeric/Float/Logical:

- upstream currently preserves them by identity.

## 5. Referential consistency

The global Character dictionary is intentionally cross-table rather than per-field. This preserves text-key equality relationships such as:

```text
customers.ID = orders.CUSTOMER_ID
```

when both values are Character and carry the same original text.

However, the integration layer must not equate this with full relational correctness. Before declaring anonymized data safe for application testing, inspect:

```text
DBC primary/candidate keys
persistent relations
composite key expressions
CDX expressions
character functions in keys
case/collation behavior
non-character key relations
memo/general identifiers
application-generated keys
```

## 6. VFP-independent anonymization path

If source tables do not require structural CDX rebuilding, the pipeline can operate without Visual FoxPro:

```text
DBF/FPT
  -> dbfbridge export/schema
  -> DBF_Anonymizer transformation
  -> dbfbridge reconstruction
  -> verification
```

Result capability:

```text
requires = [PURE_WRITE_COPY, PRIVACY_SENSITIVE]
```

The original source directory is immutable.

## 7. Structural CDX path

Changing indexed Character values invalidates the source index contents.

For tables whose DBF header declares structural CDX, the validated output path is:

```text
source DBF/FPT/CDX
  -> read/capture index metadata
  -> anonymize/reconstruct DBF/FPT in staging
  -> provide/copy structural CDX definitions as required by upstream workflow
  -> VFP9 SP2 REINDEX in output staging
  -> runtime tag/expression verification
  -> publish only after PASS
```

Requirements:

```text
requires = [PURE_WRITE_COPY, PRIVACY_SENSITIVE, VFP_WRITE_WORKSPACE]
```

If VFP9 SP2 is unavailable:

```text
status = FAIL or PARTIAL according to requested output contract
errorCode = CDX_REBUILD_REQUIRES_VFP9
```

Never publish a stale CDX copied from the source as if it indexed anonymized DBF values.

## 8. IDX handling

Standalone IDX files require separate treatment from structural CDX.

The integration must inventory each IDX and determine whether its definition can be recovered from VFP runtime/project knowledge. If definition cannot be verified:

```text
status = PARTIAL
warning = INDEX_DEFINITION_UNVERIFIED
```

Do not silently copy stale standalone index files after changing indexed values.

## 9. DBC-bound tables

The DBF header can indicate database-container membership. For DBC-bound tables, anonymization must preserve source copies and treat DBC metadata as a separate semantic layer.

Before application-level validation inspect:

```text
primary/candidate keys
field/table rules
triggers
persistent relations
views
stored procedures
```

Anonymization should not automatically rewrite DBC definitions unless an explicit future workspace operation requires it.

## 10. Dictionary security

`dictionary.sqlite3` is highly sensitive because it enables reversal.

Required policy:

- never store it under source project directories,
- never copy it into normal audit output,
- never commit it to Git,
- never include its contents in logs/prompts/model context by default,
- store it only under configured sensitive dictionary roots,
- record path/hash/status, not original values, in normal result objects,
- allow administrators to disable recovery capability,
- recommend filesystem/OS access control and encryption-at-rest for production use.

## 11. Salt/secret policy

Secrets/salts must be supplied through configuration/environment/secret storage, not committed configuration files.

The service response must not echo the salt.

An incompatible salt/dictionary combination must fail closed.

## 12. Logging policy

Normal logs may contain:

```text
file path
field name/type
record count
encoding
status/error code
hashes
phase durations
```

Normal logs must not contain:

```text
original personal values
reversible dictionary rows
secret salt
full memo contents
```

A special diagnostic mode that exposes values must be explicit and disabled by default.

## 13. Staging and atomic publication

Preserve the upstream transactional design:

```text
source immutable
  -> isolated staging
  -> all table conversions
  -> index rebuild where required
  -> verification/self-test
  -> atomic/promoted final directory
```

Failure of one required table blocks publication of a supposedly complete anonymized dataset.

## 14. Required verification

For each table capture:

```text
source schema hash
source DBF/FPT/CDX fingerprints
anonymized schema hash
record count
field type/length invariants
code page
memo status
structural index status
runtime tag verification when VFP is used
warnings/errors
```

Global checks should include:

```text
all required tables present
all source files unchanged
same directory/table topology
Character mapping consistency
expected date offsets
no accidental dictionary exposure
```

## 15. Self-test

Expose the upstream `self_test()` operation as an explicit diagnostic tool.

Use it to validate:

```text
source -> anonymized -> recovered
```

Recovery validation is for controlled diagnostics. It does not justify distributing the recovery dictionary with an anonymized test dataset.

## 16. Performance considerations

For large datasets:

- preserve streaming JSONL paths,
- avoid materializing complete tables in RAM,
- retain bounded batching/multiprocessing behavior,
- use isolated per-table temp directories on Windows,
- measure CPU, disk and CDX rebuild time separately,
- do not expose excessive per-record progress over MCP.

Future MCP should return job/progress summaries rather than one tool event per row.

## 17. Future MCP tool contract

Suggested input:

```json
{
  "source": "D:\\data\\prod-copy",
  "output": "D:\\privacy\\dataset-a",
  "dictionaryRoot": "D:\\privacy-secrets\\dataset-a",
  "memoMode": "mask",
  "dateOffsetDays": 30,
  "workers": 0,
  "rebuildIndexes": true
}
```

Suggested result:

```json
{
  "status": "PASS",
  "operation": "vfp_anonymize",
  "requires": ["PRIVACY_SENSITIVE", "VFP_WRITE_WORKSPACE"],
  "sourceModified": false,
  "tables": 123,
  "indexRebuild": "PASS",
  "dictionary": {
    "created": true,
    "sensitive": true,
    "pathExposedToModel": false
  },
  "warnings": [],
  "errors": []
}
```

## 18. Offline dependency strategy

DBF_Anonymizer currently declares a pinned git dependency on a dbfbridge commit. An offline toolchain must not rely on GitHub during execution.

Therefore the integration repo should vendor or package a pinned DBF_Anonymizer snapshot and ensure it uses the same compatible dbfbridge snapshot as the toolchain.

Avoid two independent copies of incompatible dbfbridge versions in one runtime.

Recommended solution:

```text
third_party/dbfbridge      one pinned shared version
third_party/dbf_anonymizer pinned adapter package configured to use that version
```

Run upstream test suites when updating either snapshot.

## 19. Update policy

A dependency update must record:

```text
old commit
new commit
license
changed public API
changed data semantics
changed code-page behavior
changed reconstruction behavior
changed CDX behavior
all upstream tests
all integration tests
```

Do not auto-track upstream `main` at runtime.

## 20. Definition of done for anonymization integration

The feature is complete only when:

1. pure no-CDX anonymization passes on a machine without VFP,
2. structural-CDX anonymization correctly reports that VFP is required when unavailable,
3. VFP9 staging REINDEX + tag verification passes when VFP is available,
4. source hashes remain unchanged,
5. dictionary never appears in ordinary audit artifacts/logs,
6. self-test/recovery works in a protected fixture,
7. failure is atomic and does not publish partial output,
8. OpenCode/CLI invoke the transport-neutral privacy service,
9. future MCP can expose the same service without reimplementing logic.
