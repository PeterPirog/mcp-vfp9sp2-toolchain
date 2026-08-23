# Usage

Practical, copy-paste examples for the VFP Integration Toolchain.
See `README.md` for the full architecture and `docs/ARTIFACTS.md` for output schemas.

All commands assume the toolchain is installed (`py install.py`) and available as
OpenCode tools. `--source` is your VFP project root; `--out` is where results go.

> **Read-only guarantee:** the toolchain never writes to your VFP project. All
> output goes to the `.vfp-ai/` cache and/or the `--out` directory you choose.

## Quick start (3 commands)

```bash
# 1. Confirm VFP artifacts are present
opencode vfp_detect --directory <project>

# 2. Convert binaries to text + build the symbol index (needs VFP9)
opencode vfp_sync --directory <project>

# 3. One-command audit (self-contained: schema, forms, relationships)
opencode vfp_audit --source <project> --out <audit_output>
```

After step 3, `<audit_output>/` is enough to **rebuild the database and every form**
without FoxPro and without the original `.scx/.vcx/.dbf` files.

## DBF schema and data (no VFP9 required)

```bash
# List all tables
opencode vfp_list_tables --directory <project>

# Export one table's schema
opencode vfp_export_table --input <project>\DANE\user.dbf --out <out>\dbf

# Export one table's data (JSONL, incl. memo/FPT)
opencode vfp_export_table --input <project>\DANE\user.dbf --out <out>\dbf --format jsonl

# Batch-export a whole tree of DBF files (schema + data)
opencode vfp_export_dir --source <project>\DANE --out <out>\dbf --formats jsonl,csv
```

## Code navigation

```bash
# Search the symbol index for a class/method/property
opencode vfp_find_symbol --query "plan4"

# Find references to a symbol in the converted text
opencode vfp_find_references --query "ComAutoData"

# Trace a class's inheritance chain
opencode vfp_trace --className "form1"
```

## CLI (without OpenCode)

Every OpenCode tool maps to a `vfp_driver.py` subcommand:

```bash
py vfp_driver.py --version
py vfp_driver.py verno --prg <foxbin2prg.prg>
py vfp_driver.py convert --input <file> --type BIN2PRG --out .vfp-ai --cfg FoxBin2Prg-AI.cfg --prg <foxbin2prg.prg>
py vfp_driver.py convert_dir --project <root> --out .vfp-ai\source --cfg FoxBin2Prg-AI.cfg --prg <foxbin2prg.prg>
py vfp_driver.py index --project .vfp-ai\source --cache .vfp-ai
py vfp_driver.py dbf_schema --input <table.dbf> --out .vfp-ai\dbf
py vfp_driver.py dbf_data  --input <table.dbf> --out .vfp-ai\dbf --format jsonl
py vfp_driver.py dbf_list  --dir <project>
py vfp_driver.py dbf_dir   --source <dir> --out <out>\dbf --formats jsonl
py vfp_driver.py audit     --source <project> --out <audit_output> [--include-data] [--no-include-forms]
```

## Audit options

| Flag | Default | Meaning |
|---|---|---|
| `--skip-sync` | off | Do not auto-run BIN2PRG sync; use an existing `.vfp-ai` cache |
| `--include-data` | off | Export full DBF record data (slow, disk-heavy) to `<out>/dbf` |
| `--data-formats` | `jsonl` | `jsonl,csv,json,xlsx` (with `--include-data`) |
| `--max-tables` | `0` | Limit `--include-data` to the N largest tables |
| `--dbf-exclude` | `""` | Uppercase substrings to skip (e.g. `ARCH,TMP`) |
| `--no-include-forms` | off | Skip the `forms/` export (on by default) |
| `--no-cache-scan` | off | Do not scan `.vfp-ai/source` for table usage |

## Running the tests

```bash
py -m pytest tests/ -v
# or without pytest:
py tests/test_common.py
py tests/test_audit.py
```
