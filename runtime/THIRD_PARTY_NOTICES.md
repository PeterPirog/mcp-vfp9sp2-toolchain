# Third-Party Notices — offline distributable bundle

This file is part of the distributable offline bundle. It lists the third-party
components that ship with (or are required by) the toolchain runtime, with
their exact version, license, source and purpose. License texts are NOT
reproduced here where they are already present in the shipped material:

- Wheel licenses are extracted into `licenses/py<py>/<package>.license.txt`
  (from each wheel's `METADATA`) at build time.
- The vendored `dbfbridge` snapshot carries its upstream `LICENSE` at
  `app/tools/dbfbridge/LICENSE`.
- The vendored `DBF_Anonymizer` snapshot's license is declared upstream in
  `pyproject.toml` (MIT) and documented in `app/tools/dbf_anonymizer/NOTICE.md`
  (the upstream repo has no LICENSE file at the pinned commit — the NOTICE is
  the canonical statement).

We do not invent or paraphrase license text; we preserve the actual license
material and provenance.

## Runtime (Python) dependencies — pinned & hash-verified

| package | version | license | source | purpose |
|---|---|---|---|---|
| dbfread | 2.0.7 | Apache-2.0 | https://pypi.org/project/dbfread/ | DBF/FPT read (PURE READ, runtime-mandatory) |
| dbf | 0.99.11 | MIT | https://pypi.org/project/dbf/ | DBF reconstruction |
| aenum | 3.1.17 | BSD-2-Clause | https://pypi.org/project/aenum/ | dbf dependency |
| openpyxl | 3.1.5 | MIT | https://pypi.org/project/openpyxl/ | XLSX read |
| et_xmlfile | 2.0.0 | MIT | https://pypi.org/project/et_xmlfile/ | openpyxl dependency |
| xlsxwriter | 3.2.9 | BSD-3-Clause | https://pypi.org/project/xlsxwriter/ | XLSX write |
| orjson | 3.12.0 | Apache-2.0 | https://pypi.org/project/orjson/ | JSON speedup (stdlib fallback) |
| polars | 1.44.1 | MIT | https://pypi.org/project/polars/ | tabular conversion |
| polars_runtime_32 | 1.44.1 | MIT | https://pypi.org/project/polars-runtime-32/ | polars native runtime |

## Test-runner dependencies (test wheelhouse only — NOT runtime)

| package | version | license | source |
|---|---|---|---|
| pytest | 9.1.1 | MIT | https://pypi.org/project/pytest/ |
| pluggy | 1.6.0 | MIT | https://pypi.org/project/pluggy/ |
| iniconfig | 2.3.0 | BSD-2-Clause | https://pypi.org/project/iniconfig/ |
| packaging | 26.3 | BSD-2-Clause / Apache-2.0 | https://pypi.org/project/packaging/ |
| pygments | 2.21.0 | BSD-2-Clause | https://pypi.org/project/pygments/ |
| colorama | 0.4.6 | BSD-3-Clause | https://pypi.org/project/colorama/ |

## Vendored project snapshots (Phase 1, unchanged)

| component | pin | license | source |
|---|---|---|---|
| dbfbridge | `addbadb9281914661bf742924f45039e46a895cd` | MIT (upstream LICENSE in `app/tools/dbfbridge/`) | https://github.com/PeterPirog/dbfbridge |
| DBF_Anonymizer | `ed7915497862850c3de650f2c50c86569442ff77` (v0.3.0) | MIT (upstream pyproject declaration; see `app/tools/dbf_anonymizer/NOTICE.md`) | https://github.com/PeterPirog/DBF_Anonymizer |

## External (NOT shipped)

| component | mode | attribution | source |
|---|---|---|---|
| FoxBin2Prg | `EXTERNAL_CONFIGURED` (BIN2PRG-only) | Reference/attribution only — its runtime source is NOT included in the bundle and requires a separately configured local installation. | https://github.com/fdbozzo/foxbin2prg |

## Notes

- `FoxBin2Prg` is listed for attribution; it is not part of the offline
  runtime closure and must not be assumed present.
- Optional/lazy runtime packages (dbf, openpyxl, xlsxwriter, orjson, polars,
  polars_runtime_32) degrade only the specific operation that requires them if
  absent; they never disable Core Service or PURE READ.
- This is not a legal review; license text in the shipped wheels and the
  vendored snapshots is authoritative.
