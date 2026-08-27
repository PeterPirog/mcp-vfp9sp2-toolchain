# DBF_Anonymizer — vendored snapshot provenance

## Upstream

| Field            | Value                                                             |
|------------------|-------------------------------------------------------------------|
| Package          | `dbf_anonymizer` 0.3.0                                            |
| Repository       | https://github.com/PeterPirog/DBF_Anonymizer                      |
| Pinned commit    | `ed7915497862850c3de650f2c50c86569442ff77`                        |
| Pinned version   | `0.3.0` (upstream `pyproject.toml` and `dbf_anonymizer.__version__` agree) |
| License          | **MIT** — declared in upstream `pyproject.toml` (`license = { text = "MIT" }`) |
| Vendored date    | 2026-08-27                                                        |
| Local changes    | NONE                                                              |
| Requires         | `dbfbridge` @ `addbadb9281914661bf742924f45039e46a895cd` (vendored at `tools/dbfbridge`) |

## License note

The upstream repository at the pinned commit **does not contain a LICENSE
file**; the MIT license is declared only in `pyproject.toml`. Because the
vendor declaration is the sole license evidence, this NOTICE (not a copied
LICENSE file) is the canonical license statement for the vendored snapshot in
this repository. The MIT license text applies as declared upstream.

## What was vendored

- `src/dbf_anonymizer/` only (runtime package, 20 modules).
- Excluded: `tests/`, `benchmarks/`, `docs/`, `.github/`, `.env.example`,
  `pyproject.toml`, sensitive dictionaries, generated artifacts.

## Sensitive artifacts — never commit

- `dictionary.sqlite3` and any `*_dict/` directory are SENSITIVE (they can
  map anonymized values back to originals). They must never be committed,
  logged, or copied outside configured sensitive roots. See
  `src/vfp_toolchain/service.py` (`vfp_anonymization_status`) and
  `docs/ANONYMIZATION_INTEGRATION.md`.

## Updating the snapshot

1. `git archive ed7915497862850c3de650f2c50c86569442ff77 src/dbf_anonymizer`
   from a fresh clone of the upstream repo at the desired commit.
2. Replace this directory with the extracted `src/dbf_anonymizer/`.
3. Update `VERSION.txt` and `tools/VENDORED_DEPENDENCIES.json` with the new
   commit + version.
4. Re-run the full upstream test suite against the vendored `tools/dbfbridge`.
