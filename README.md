# VFP Integration Toolchain for OpenCode

Strict read-only integration between [OpenCode](https://opencode.ai) AI agents and Visual FoxPro 9 projects via [FoxBin2Prg](https://github.com/fdbozzo/foxbin2prg) text conversion.

**No PRG2BIN. No recompilation. No source modification. Ever.**

> **⚠️ VFP 9 is REQUIRED** for file conversion. The tool auto-detects it via COM. You do NOT need to manually specify the path. See [VFP9 Detection](#v9-detection-how-it-works) below.

> **Credits**: This toolchain depends on [FoxBin2Prg](https://github.com/fdbozzo/foxbin2prg) by Fabio Zadro ([fdbozzo](https://github.com/fdbozzo)). FoxBin2Prg is a free, open-source utility that converts between VFP binary files (.scx/.vcx/.frx/etc.) and text. This toolchain wraps it in a strict read-only shell. See [THANKS.md](THANKS.md) for details.

## Quick Start

```bash
# 1. Install (symlinks the tools into ~/.config/opencode)
git clone https://github.com/PeterPirog/vfp-integration-toolchain.git
cd vfp-integration-toolchain
py -m pip install dbfread orjson xlsxwriter openpyxl dbf   # optional: polars
py install.py --foxbin2prg-dir "C:\path\to\foxbin2prg"

# 2. In any VFP project (OpenCode):
opencode vfp_detect   --directory .
opencode vfp_sync     --directory .          # needs VFP9; builds .vfp-ai cache
opencode vfp_audit    --source . --out AUDIT # self-contained: schema + forms + data

# 3. Or without OpenCode, straight from the CLI:
py vfp_driver.py --version
py vfp_driver.py audit --source . --out AUDIT
```

Result: an `AUDIT/` directory that is enough to **rebuild the database and every form**
without FoxPro and without the original `.scx/.vcx/.dbf` files. See
[docs/USAGE.md](docs/USAGE.md) for more and [docs/ARTIFACTS.md](docs/ARTIFACTS.md) for output schemas.

---

## ⚠️ VFP9 Detection — How It Works

**VFP 9 must be installed on the machine** — this is a Windows COM requirement. The toolchain **auto-detects** VFP9, you do NOT need to specify the path manually.

### How it works

1. **Auto-detection via COM** — our VBS scripts use `CreateObject("VisualFoxPro.Application.9")` — Windows automatically finds the registered VFP9 instance
2. **No configuration needed** — if VFP9 is installed, the COM registry entry is already in place
3. **Optional env var** — set `VFP9_EXE` if you have a non-standard install:

```powershell
# Windows PowerShell
$env:VFP9_EXE = "D:\Apps\VFP9\vfp9.exe"

# Linux/macOS (wine)
export VFP9_EXE="/path/to/vfp9.exe"
```

4. **`install.py` checks for you** — the installer auto-detects VFP9 and prints its status

### What you need to install

| Component | Where to get it | Does the toolchain auto-detect? |
|---|---|---|
| **VFP 9** (vfp9.exe) | Microsoft / Visual Studio subscription | ✅ Yes — via COM |
| **FoxBin2Prg** (foxbin2prg.prg) | [GitHub: fdbozzo/foxbin2prg](https://github.com/fdbozzo/foxbin2prg) | ✅ Yes — `install.py` searches default locations or `VFP_FOXBIN2PRG_DIR` |
| **Python 3** | [python.org](https://python.org) | ✅ Yes — `py` or `python3` in PATH |

### What happens if VFP9 is NOT installed?

- `vfp_detect` → **works** (only scans files)
- `vfp_status` → **shows an error** "VFP9 not found"
- `vfp_sync` / `vfp_export_*` → **shows an error** "COM object creation failed"
- `vfp_index` / `vfp_find_symbol` / `vfp_trace` → **work** but only on existing `.sc2`/`.vc2` files (without sync there is nothing to index)
- `vfp_export_table` / `vfp_list_tables` / `vfp_export_dir` → **work without VFP9!** They read DBF files directly in Python

---

## 📖 For OpenCode Beginners

This repository adds **custom tools** and an **agent** to OpenCode. If you've never used custom tools or agents before:

### What are "custom tools"?

OpenCode scans `~/.config/opencode/tools/` for `.ts` files. Each exported function becomes an AI-callable tool. When you open OpenCode in any project directory, you can type:

```
@vfp-analyst  "find all forms referencing CUSTOMERS table"
```

or use individual tools:
```
opencode vfp_detect          # "Are there VFP files here?"
opencode vfp_sync            # "Convert all VFP binaries to text and build a search index"
opencode vfp_find_symbol     # "Find class 'myBaseForm'"
```

### What is "@vfp-analyst"?

An **agent** is a pre-configured persona. Place `.md` files in `~/.config/opencode/agents/`. Each file becomes an agent you can invoke with `@agent-name`. The `@vfp-analyst` agent knows about VFP project structure, FoxBin2Prg output format, and the 15 tools this repo provides. It acts as an expert VFP developer assistant inside OpenCode.

### 15 Tools This Repo Provides

| Tool | What it does | VFP9 required? |
|---|---|---|
| `vfp_detect` | Scans a directory — tells you if VFP files exist and what types | ❌ No |
| `vfp_status` | Checks that VFP9.exe and FoxBin2Prg are installed and working | ✅ Yes |
| `vfp_export_file` | Converts one binary file (.scx/.vcx/.frx) to text (.sc2/.vc2) | ✅ Yes |
| `vfp_export_project` | Converts all binary files in a directory tree | ✅ Yes |
| `vfp_export_class` | Extracts one class from a library: `vfp_export_class --library lib.vcx --className MyClass` | ✅ Yes |
| `vfp_sync` | Does `vfp_export_project` + builds search index (one command) | ✅ Yes |
| `vfp_index` | Builds/refreshes the JSON symbol index from cached text files | ❌ No |
| `vfp_find_symbol` | Searches the index for class/method/property names | ❌ No |
| `vfp_find_references` | Searches converted text files for references to a symbol | ❌ No |
| `vfp_find_table_usage` | Finds USE/SELECT/INSERT/REPLACE patterns in source | ❌ No |
| `vfp_trace` | Follows a class's inheritance chain (MyClass → Form → Container → Object) | ❌ No |
| `vfp_export_table` | Export DBF schema to JSON + optional data to JSONL/CSV (pure Python, no VFP9) | ❌ No |
| `vfp_list_tables` | Lists all DBF tables in a directory tree with field/record counts | ❌ No |
| `vfp_export_dir` | Batch-export a whole directory tree of DBF tables (schema + data, memo/FPT) — no VFP9 | ❌ No |
| `vfp_audit` | Comprehensive audit: sync + DBF schema + table relationships + class analysis → target directory | ⚠️ Partial |

---

## Full Walkthrough

> Install, every tool, audit options and the CLI reference live in
> **[docs/USAGE.md](docs/USAGE.md)**. The 3-step version is in the
> [Quick Start](#quick-start) section above.

---

## Installation

### Prerequisites

| Requirement | Details |
|---|---|
| **VFP 9** | Installed at default path (`C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe`) or set `VFP9_EXE` env var. **Not needed** for DBF export tools (see below) |
| **Python 3** | Accessible as `py` (Windows) or `python3` (Linux/macOS) |
| **FoxBin2Prg** | [Download from GitHub](https://github.com/fdbozzo/foxbin2prg) — place `foxbin2prg.prg` somewhere on disk. **Not needed** for DBF schema/data export |
| **dbfbridge** (bundled) | **Vendored in this repo** at `tools/dbfbridge/` (upstream: [dbfbridge](https://github.com/PeterPirog/dbfbridge), pinned commit in `tools/dbfbridge/VERSION.txt`). Full DBF/FPT support: inline memo (FPT), batch export, JSONL/CSV/JSON/XLSX, validation, Polish cp1250/cp852/Mazovia encoding fallback. Loaded from the repo — **no pip install needed** |
| **dbfread** (runtime dep) | `pip install dbfread` — streaming DBF/FPT reader used by dbfbridge and by the fallback path. Installed as a pip dependency |
| *(neither)* | A built-in minimal DBF reader is used as a last resort (schema + non-memo data, no FPT) |

> The vendored copy is a frozen snapshot so this toolchain is **not affected** if the upstream
> `dbfbridge` repo evolves or changes API. To refresh it, re-copy from a fresh upstream clone
> and update `tools/dbfbridge/VERSION.txt` (commit + sha256 manifest).

### One-Step Install

```bash
git clone https://github.com/PeterPirog/vfp-integration-toolchain.git
cd vfp-integration-toolchain

# Install dbfbridge's runtime dependencies (dbfbridge itself is bundled, not pip-installed)
# `polars` is OPTIONAL (fast CSV path only) — omit it to keep installs light
py -m pip install dbfread orjson xlsxwriter openpyxl dbf
# Optional (only speeds up CSV export): py -m pip install polars

# Run the installer (needs FoxBin2Prg directory for BIN2PRG tools)
py install.py --foxbin2prg-dir "C:\path\to\foxbin2prg"
```

Options:
| Flag | Description |
|---|---|
| `--toolchain-dir PATH` | Override toolchain root (default: this script's directory) |
| `--opencode-config PATH` | Override OpenCode config dir (default: `~/.config/opencode`) |
| `--foxbin2prg-dir PATH` | Directory containing `foxbin2prg.prg` |
| `--no-symlink` | Copy files instead of symlinking (Windows without admin) |
| `--no-verify` | Skip post-install verification |

The installer:
1. **Locates FoxBin2Prg** — checks `VFP_FOXBIN2PRG_DIR` env var, provided path, default locations
2. **Locates VFP9** — checks `VFP9_EXE` env var, then default install path
3. **Symlinks** `tools/vfp.ts` → `~/.config/opencode/tools/vfp.ts`
4. **Symlinks** `agents/vfp-analyst.md` → `~/.config/opencode/agents/vfp-analyst.md`
5. **Verifies** with `vfp_status`

### Manual Installation

```bash
# 1. Set toolchain location
export VFP_TOOLCHAIN_HOME="/path/to/vfp-integration-toolchain"  # Windows: $env:VFP_TOOLCHAIN_HOME = "..."

# 2. Symlink (or copy) to OpenCode config dirs
ln -s $VFP_TOOLCHAIN_HOME/tools/vfp.ts ~/.config/opencode/tools/vfp.ts
ln -s $VFP_TOOLCHAIN_HOME/agents/vfp-analyst.md ~/.config/opencode/agents/vfp-analyst.md

# 3. Set FoxBin2Prg location
export VFP_FOXBIN2PRG_DIR="/path/to/foxbin2prg"
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `VFP_TOOLCHAIN_HOME` | Root directory of this toolchain | `~/.config/opencode/vfp` or repo root |
| `VFP_FOXBIN2PRG_DIR` | Directory containing `foxbin2prg.prg` | `tools/foxbin2prg` relative to toolchain |
| `VFP9_EXE` | Path to `vfp9.exe` | Standard install path |

**Note**: DBF export tools (`vfp_export_table`, `vfp_list_tables`) work **without** VFP9 and without FoxBin2Prg. They only need Python 3 and optionally `dbfread` (`pip install dbfread`).

---

## 🚀 For Warp Terminal Users

[Warp](https://warp.dev) is a modern terminal emulator with AI assistance. This toolchain works seamlessly inside Warp.

### Setting Environment Variables in Warp

#### Windows (PowerShell)

Create or edit `C:\Users\<you>\.env` (Warp reads this automatically):

```powershell
VFP_TOOLCHAIN_HOME=C:\path\to\vfp-integration-toolchain
VFP_FOXBIN2PRG_DIR=C:\path\to\foxbin2prg
VFP9_EXE=C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe
```

Or via PowerShell profile (`$PROFILE`):
```powershell
$env:VFP_TOOLCHAIN_HOME = "C:\path\to\vfp-integration-toolchain"
$env:VFP_FOXBIN2PRG_DIR = "C:\path\to\foxbin2prg"
```

#### macOS

Add to `~/.zshrc` or `~/.env.local`:
```bash
export VFP_TOOLCHAIN_HOME="/path/to/vfp-integration-toolchain"
export VFP_FOXBIN2PRG_DIR="/path/to/foxbin2prg"
export VFP9_EXE="/path/to/vfp9.exe"
```

### Running OpenCode in Warp

```bash
# Navigate to your VFP project directory
cd D:\Projects\MyVfpProject

# Start OpenCode (Ctrl+O or just type 'opencode')
opencode

# Inside OpenCode, use the tools:
opencode vfp_status
opencode vfp_sync --full
opencode vfp_find_symbol --query "MyForm"

# Or use the agent:
opencode @vfp-analyst "analyze this project"
```

### Warp Workflows (Optional)

Save common commands as Warp Workflows (Ctrl+Shift+W):

| Workflow Name | Command |
|---|---|
| `VFP Sync` | `py vfp_driver.py convert_dir --project %DIR% --out .vfp-ai --cfg FoxBin2Prg-AI.cfg --prg tools/foxbin2prg/foxbin2prg.prg` |
| `VFP Index` | `py vfp_driver.py index --project .vfp-ai/source --cache .vfp-ai --full` |
| `VFP Status` | `py vfp_driver.py verno --prg tools/foxbin2prg/foxbin2prg.prg` |
| `VFP DBF Schema` | `py vfp_driver.py dbf_schema --input %DBF_FILE% --out .vfp-ai/dbf` |
| `VFP DBF Data` | `py vfp_driver.py dbf_data --input %DBF_FILE% --out .vfp-ai/dbf --format jsonl --deleted include` |
| `VFP List Tables` | `py vfp_driver.py dbf_list --dir %DIR%` |
| `VFP DBF Batch` | `py vfp_driver.py dbf_dir --source %DIR% --out .vfp-ai\dbf --formats jsonl` |

### Warp AI vs OpenCode AI

- **Warp AI** (Ctrl+L): General terminal AI, runs commands for you
- **OpenCode** (Ctrl+O): Project-aware agent, understands codebase context

For VFP work, use **OpenCode** — the `@vfp-analyst` agent has domain-specific knowledge about VFP projects, FoxBin2Prg output format, and the 15 tools in this repo.

### Windows + Warp Specific Note

VFP9 is **Windows-only**. If you're on macOS with Warp:
- You need a Windows VM or VM-based VFP9 installation for BIN2PRG conversion
- The indexing/search tools (`vfp_find_symbol`, `vfp_trace`) **do NOT need VFP9** — they work on cached `.sc2`/`.vc2` text files
- The DBF export tools (`vfp_export_table`, `vfp_list_tables`) **do NOT need VFP9** — they work on any platform with Python 3 (install `dbfread`: `pip install dbfread` for best results)

---

## Repository Structure

```
vfp-integration-toolchain/
├── README.md              ← This file
├── LICENSE                ← MIT license
├── THANKS.md              ← Attributions (FoxBin2Prg, dbfbridge, dbfread)
├── install.py             ← One-step installer (symlinks + verify)
├── requirements.txt       ← Python dependencies (dbfread, etc.)
├── .gitignore
├── config.json            ← Portable VFP/FoxBin2Prg config (schema v2)
├── FoxBin2Prg-AI.cfg      ← Strict read-only AI profile
├── vfp_driver.py          ← Python orchestrator (all subcommands)
├── vfp_dbf_export.py      ← Pure-Python DBF schema + data export (no VFP9)
├── vfp_audit.py           ← Comprehensive project auditor
├── vfp_convert.vbs        ← VBS driver for BIN2PRG (17-param execute())
├── vfp_common.py          ← Shared constants (canonical exclusion list)
├── vfp_indexer.py         ← SC2/VC2 parser → JSON symbol index
├── vfp_verno.vbs          ← VBS driver for version check
├── tools/
│   ├── vfp.ts             ← 15 OpenCode custom tools (TypeScript)
│   └── dbfbridge/         ← Vendored DBF backend (frozen snapshot, see VERSION.txt)
├── docs/
│   ├── USAGE.md           ← Practical usage, CLI reference, audit options
│   └── ARTIFACTS.md       ← Schema of every audit output file
├── tests/
│   ├── test_common.py     ← Unit tests (vfp_common)
│   └── test_audit.py      ← Unit tests (VFPProjectAuditor helpers)
├── .github/
│   ├── ISSUE_TEMPLATE/    ← Bug report + feature request templates
│   └── pull_request_template.md
└── agents/
    └── vfp-analyst.md     ← @vfp-analyst agent
```

---

## Usage

### In OpenCode (Recommended)

```bash
# Detect VFP project artifacts
opencode vfp_detect --directory /path/to/vfp/project

# Check toolchain is working
opencode vfp_status

# Full sync: convert all binaries + build symbol index
opencode vfp_sync --directory /path/to/vfp/project --full

# Search for a class, method, or property
opencode vfp_find_symbol --query "MyForm" --directory /path/to/vfp/project

# Trace class inheritance chain
opencode vfp_trace --className "myBaseForm" --directory /path/to/vfp/project

# Find all references to a symbol
opencode vfp_find_references --query "myFunction"

# Find table usage patterns
opencode vfp_find_table_usage --tableName "CUSTOMERS" --directory /path/to/vfp/project

# Extract a single class from a library
opencode vfp_export_class --library "lib.vcx" --className "MyClass"

# Run a comprehensive audit of the project
opencode vfp_audit --source /path/to/vfp/project --out /path/to/audit/output

# List all DBF tables in project (no VFP9 needed!)
opencode vfp_list_tables --directory /path/to/vfp/project

# Export DBF table schema (no VFP9 needed!)
opencode vfp_export_table --input "data/customers.dbf"

# Export DBF table data to JSONL (no VFP9 needed!)
opencode vfp_export_table --input "data/customers.dbf" --format jsonl --deleted include

# List all DBF tables in project (no VFP9 needed!)
opencode vfp_list_tables --directory /path/to/vfp/project
```

### Comprehensive Audit (One Command)

The `vfp_audit` tool consolidates everything into a single output directory:

```bash
# Full audit (needs VFP9 for BIN2PRG, DBF schema export works without)
opencode vfp_audit --source <project> --out <audit_output>

# Audit without VFP9 (schema + relationships only, uses existing cache)
opencode vfp_audit --source <project> --out <audit_output> --skip-sync

# OPTIONAL / SLOW: audit + FULL DBF DATA export (reads every table's contents incl. memo/FPT)
# Data lands in <audit_output>/dbf, mirroring the project's folder structure.
# This is the most time-consuming / disk-heavy mode — only use when you need the data itself.
opencode vfp_audit --source <project> --out <audit_output> --include-data --data-formats jsonl,csv

# Limit the data export to the N largest tables (0 = all)
opencode vfp_audit --source <project> --out <audit_output> --include-data --max-tables 20

# Full audit including form/class code (DEFAULT ON, no extra flag needed;
# use --no-include-forms to skip)
opencode vfp_audit --source <project> --out <audit_output>
```

**What gets generated in the output directory:**
- `audit_report.md` — Human-readable Markdown summary
- `data_export.json` — What the optional data export did (dir, tables, formats)
- `project_summary.json` — File inventory, class/method counts
- `database_schema.json` — All DBF table schemas with encodings, fields, types
- `table_relationships.json` — Table usage patterns, SQL SELECT/INSERT/REPLACE, inferred joins
- `class_analysis.json` — Class hierarchy, inheritance depth, complexity ranking
- `forms/` — full source of every form/class/method + PRG scripts (ON by default; `--no-include-forms` to skip)
- `dbf/` — individual `<table>_schema.json` files for each DBF; **with `--include-data`** also the full JSONL table contents (incl. memo), mirroring the project tree

### Via @vfp-analyst Agent

```bash
opencode @vfp-analyst "Find all forms that reference the CUSTOMERS table"
opencode @vfp-analyst "Trace the inheritance chain for the 'form_archdoplan' class"
opencode @vfp-analyst "Show me all methods named 'Click' in this project"
opencode @vfp-analyst "Run a full audit of this project and save to D:/audit_output"
```

### Via Python Driver Directly

```bash
# Version check
py vfp_driver.py verno --prg "tools/foxbin2prg/foxbin2prg.prg"

# Single file conversion
py vfp_driver.py convert --input "src/forms/myform.scx" --type BIN2PRG \
  --out ".vfp-ai/source" --cfg "FoxBin2Prg-AI.cfg" --prg "tools/foxbin2prg/foxbin2prg.prg"

# Full directory sync
py vfp_driver.py convert_dir --project "src" --out ".vfp-ai/source" \
  --cfg "FoxBin2Prg-AI.cfg" --prg "tools/foxbin2prg/foxbin2prg.prg"

# Build symbol index
py vfp_driver.py index --project ".vfp-ai/source" --cache ".vfp-ai" --full
```

---

## Safety Guarantees

| Guarantee | Mechanism |
|---|---|
| No binary regeneration | `tcRecompile='0'` in all execute() calls |
| No source file modification | `cOutputFolder` redirects all output to `.vfp-ai/source/` |
| No config inheritance | `InhibitInheritance: 3` in `FoxBin2Prg-AI.cfg` |
| No PRG2BIN ever | Whitelist gate in `vfp_convert.vbs` rejects any PRG2BIN direction |
| All output goes to cache | `--out` always points to `.vfp-ai/` directory |
| Timestamp-agnostic | `tcNoTimestamps='1'`, `tcClearUniqueID='1'` |

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  OpenCode Session (in any VFP project directory)              │
├─────────────────────────────────────────────────────────────┤
│  vfp.ts (custom tools)  →  calls  →  vfp_driver.py           │
│  @vfp-analyst (agent)   →  calls  →  vfp.ts tools           │
├─────────────────────────────────────────────────────────────┤
│  vfp_driver.py (Python orchestrator)                         │
│    ├── verno  →  vfp_verno.vbs  →  VFP9 COM → FoxBin2Prg     │
│    ├── convert → vfp_convert.vbs →  VFP9 COM → execute() 17  │
│    ├── index  →  vfp_indexer.py →  parse .sc2/.vc2 → index   │
│    ├── dbf_schema → vfp_dbf_export.py → dbfread (no VFP9)    │
│    ├── dbf_data   → vfp_dbf_export.py → dbfread (no VFP9)    │
│    ├── dbf_list   → vfp_dbf_export.py → dbfread (no VFP9)    │
│    └── dbf_dir    → vfp_dbf_export.py → dbfbridge batch      │
├─────────────────────────────────────────────────────────────┤
│  vfp_convert.vbs (VBS)                                       │
│    1. Create VisualFoxPro.Application.9 COM object          │
│    2. SET PROCEDURE TO foxbin2prg.prg                       │
│    3. Set cOutputFolder = .vfp-ai/source/                   │
│    4. Call oFb.execute(inputFile, 'BIN2PRG', ..., cfg)     │
│    5. Print RC=<n>, quit VFP9                               │
├─────────────────────────────────────────────────────────────┤
│  FoxBin2Prg (by Fabio Zadro)                                 │
│    Converts .scx/.vcx/.fox/.dbc/.dbf → .sc2/.vc2/.fx2/.db2   │
│    STRICTLY BINARY→TEXT (BIN2PRG). Never PRG2BIN.           │
├─────────────────────────────────────────────────────────────┤
│ OUTPUT (strictly in .vfp-ai/source/)                          │
│   ├── *.sc2    (forms, extracted as text)                    │
│   ├── *.vc2    (class libraries, extracted as text)          │
│   ├── *.fr2    (reports)                                     │
│   ├── *.mn2    (menus)                                       │
│   └── *.db2    (table structures)                            │
│                                                             │
│  index.json (954 files, 599 classes, 8168 methods)          │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### config.json (schema v2)

All paths are environment-variable driven — no hardcoded user paths:

```json
{
  "schemaVersion": 2,
  "version": "0.2.0",
  "readOnly": true,
  "vfp": {
    "exeEnvironmentVariable": "VFP9_EXE",
    "exeDefault": "C:\\Program Files (x86)\\Microsoft Visual FoxPro 9\\vfp9.exe"
  },
  "foxbin2prg": {
    "programFile": "foxbin2prg.prg",
    "directoryEnvironmentVariable": "VFP_FOXBIN2PRG_DIR",
    "directoryDefault": "tools/foxbin2prg",
    "upstream": "https://github.com/fdbozzo/foxbin2prg",
    "timeoutMs": 600000
  },
  "aiProfile": {
    "file": "FoxBin2Prg-AI.cfg",
    "inhibitInheritance": 3
  },
  "cacheDirectory": ".vfp-ai",
  "defaultExcludes": [".git", ".vfp-ai", "backup", "backups", "archive", "tmp", "node_modules", "__pycache__"]
}
```

> `defaultExcludes` is the **single source of truth** for directory exclusion
> during sync and audit. `vfp_common.default_excludes()` (Python) and
> `excludeDirs()` in `tools/vfp.ts` both read it, so all walks stay consistent.

### FoxBin2Prg-AI.cfg

Key settings:
- `InhibitInheritance = 3` — No project config file inheritance
- `DBF_Conversion_Support = 1` — Generate DBF structure to text only
- `SC2_Conversion_Support = 1` — Generate SCX form code to text only
- `VC2_Conversion_Support = 1` — Generate VCX class library to text only

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `vfp_status` fails with "COM object creation error" | VFP9 not installed or `VFP9_EXE` env var needs to point to `vfp9.exe` |
| `vfp_sync` shows "FoxBin2Prg NOT found" | Install [FoxBin2Prg](https://github.com/fdbozzo/foxbin2prg) and set `VFP_FOXBIN2PRG_DIR` |
| Tools not appearing in OpenCode | Restart OpenCode after running `install.py` |
| "Index not found" when searching | Run `opencode vfp_sync --full` first |
| DBF conversion fails (rc=1707) | Missing `.cdx` file — not a safety issue, the DBF itself is not modified |

---

## Complete Rewrite Feasibility

**Can you rewrite the entire application from this toolchain's output?**

**Yes — for both the code/logic layer AND the data layer.**

- **Code/logic** (forms, classes, methods, button handlers): captured by `vfp_sync` (converted `.sc2`/`.vc2`/`.fr2` text) and, with `--include-forms` (default on), shipped self-contained in `<audit_output>/forms/`.
- **Data** (table schemas + full record contents incl. memo/FPT): captured by `vfp_export_table` and, with `--include-data`, shipped in `<audit_output>/dbf/`.

Run `vfp_audit --include-data --include-forms` once and the resulting directory is enough to **rebuild the database and every form** without FoxPro and without the original binaries.

### What IS captured (sufficient for code rewrite)

| Component | Source Files | What's captured |
|---|---|---|
| **Form classes** | `.scx` → `.sc2` (840 files) | ✅ Full class definition, all 6,233 methods with code, 6,262 properties with values, all controls (ADD OBJECT trees) |
| **Class libraries** | `.vcx` → `.vc2` (41 files) | ✅ Full class hierarchy, 530 methods with code, all properties |
| **Reports** | `.frx` → `.fr2` (65 files) | ✅ Report structure, fields, groups |
| **Projects** | `.pjx` → `.pj2` (8 files) | ✅ Project file lists, main program, file types (K=Form, P=PRG, D=DBF) |
| **Table structure** | `.dbf` → schema via `vfp_export_table` (pure Python, no VFP9) | ✅ Field names, types, lengths, decimals, codepage, record count, memo presence |
| **Table data** | `.dbf` data via `vfp_export_table --format jsonl` | ✅ Full record data export to JSONL/CSV (pure Python, no VFP9) |
| **Form/class code** | `.sc2`/`.vc2`/`.fr2` + `.prg` → `<audit>/forms/` via `--include-forms` (default on) | ✅ Self-contained full source of every form, class, method and button handler |
| **PRG files** | `.prg` (copied into `<audit>/forms/` by `--include-forms`) | ✅ Copied to the audit (already text) |

**Total captured for code rewrite:**
- 599 classes with full inheritance chains
- 8,168 methods with **complete implementations** (PROCEDURE...ENDPROC code)
- 6,262 properties with all default values
- Full form layouts (control positions, bindings, event handlers)
- Table references (USE/SELECT statements in code)
- Project structure (what files belong to what project, main entry point)
- DBF table schemas (fields, types, codepage) via `vfp_export_table`
- DBF table data records via `vfp_export_table --format jsonl|csv`

### What is NOT captured (additional work needed)

| Missing | Why | For rewrite: |
|---|---|---|
| **CDX index structure** | Binary index files, not converted | Recreate index strategy manually |
| **DBC database containers** | Not fully parsed (constraints, relationships) | Extract separately with DBC tools |

### For a complete application rewrite, you need:

1. **This toolchain's output** (`vfp_sync` / `--include-forms`) → all class/method/property code + form source ✅
2. **This toolchain's DBF export** (`vfp_export_table` / `--include-data`) → table schemas + data ✅ (no external tools)
3. **DBC schema export** → table relationships and constraints (optional)

### One-Command Audit

Use `vfp_audit` to generate a complete, self-contained project audit in any target directory:

```bash
# Self-contained: data + form code (the two heavy options below are optional)
opencode vfp_audit --source <project> --out <audit_output>

# Fully reconstructable: add full DBF data (slow) — form code is included by default
opencode vfp_audit --source <project> --out <audit_output> --include-data
```

This generates:
- **`audit_report.md`** — human-readable audit summary
- **`project_summary.json`** — file inventory, class/method counts
- **`database_schema.json`** — all DBF table schemas with encodings
- **`table_relationships.json`** — table usage patterns, inferred SQL joins
- **`class_analysis.json`** — class hierarchy, inheritance depth, complexity ranking
- **`forms/`** — full source of every form/class/method + PRG scripts (default on; disable with `--no-include-forms`)
- **`dbf/`** — per-table schema JSON (+ with `--include-data`, full record JSONL incl. memo/FPT), mirroring the project tree

The `@vfp-analyst` agent can then read these files and answer questions like:
- "Which tables have the most records?"
- "What are the inheritance chains for each form?"
- "Are there inefficient table joins in the code?"
- "What DBF encodings are used in this project?"

### Recommendation

Use this toolchain to reverse-engineer the **application logic** (forms, classes, methods). Then use `vfp_export_table` for the **data layer** (table schemas + data). The DBF export works with pure Python (`dbfread` library) — **no VFP9 required**.

---

## Tested

Verified on a real VFP project (`<project>`, ~1,218 binary files):
- 631/633 files converted successfully (2 failures: missing .CDX files)
- 946 text files generated in `.vfp-ai/source/` (840 SC2, 65 FR2, 41 VC2, 8 PJ2)
- 0 source files modified (SHA256/size/mtime verified unchanged)
- Index: 599 classes, 8,168 methods with full code, 6,262 properties
- `cOutputFolder` correctly redirects SC2/VC2/FR2 output to cache
- DBF schema export tested with `vfp_export_table` (pure Python, no VFP9)
- DBF data export to JSONL tested (pure Python, no VFP9)

Note: DBF→DB2 conversion via FoxBin2Prg returns `RC=0` but does NOT create `.db2` in cache (`cOutputFolder` does not redirect DBF output in FoxBin2Prg). Use `vfp_export_table` instead — it exports DBF schema directly to `.vfp-ai/dbf/` cache without needing VFP9 or FoxBin2Prg.

## Limitations

1. **Windows-only**: VFP9 COM host is Windows-specific. DBF export tools work on any platform.
2. **Requires VFP9 installed** for BIN2PRG conversion: No standalone FoxBin2Prg.exe exists; the VFP9 COM automation host is required. DBF schema/data export works **without** VFP9.
3. **DBF without CDX**: Files missing structural CDX will fail FoxBin2Prg conversion (rc != 0). DBF schema/export via `vfp_export_table` does NOT need CDX.
4. **Large projects**: Full sync of 600+ files takes ~5 minutes (VFP9 COM startup per file). DBF export is fast (no COM overhead).
5. **DB2 cache issue**: DBF→DB2 conversion via FoxBin2Prg returns `RC=0` but does not create `.db2` in cache (`cOutputFolder` does not redirect DBF output). Use `vfp_export_table` instead for DBF schema — it exports directly to `.vfp-ai/dbf/` cache.
6. **PRG files**: Not automatically copied to `.vfp-ai/source/`. Only referenced in PJ2 project files. To search PRG code, either copy them to the cache or use `vfp_find_references` on the source project directory directly.
7. **DBF memo content**: `dbfbridge` (preferred) reads FPT memo fields inline. `dbfread` (fallback) and the built-in reader detect memo fields but the built-in reader cannot read FPT content. Install `dbfbridge` for full memo support.

## Credits

- **FoxBin2Prg** by [Fabio Zadro (fdbozzo)](https://github.com/fdbozzo) — https://github.com/fdbozzo/foxbin2prg
  - This entire toolchain depends on FoxBin2Prg's `c_foxbin2prg` COM class
  - All BIN2PRG/PRG2BIN logic is Fabio's work; this repo only wraps it in a read-only shell
  - Licensed under FoxBin2Prg's own license (MIT-like)
