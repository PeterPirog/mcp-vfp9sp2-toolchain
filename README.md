# VFP Integration Toolchain for OpenCode

Strict read-only integration between [OpenCode](https://opencode.ai) AI agents and Visual FoxPro 9 projects via [FoxBin2Prg](https://github.com/fdbozzo/foxbin2prg) text conversion.

**No PRG2BIN. No recompilation. No source modification. Ever.**

> **⚠️ VFP 9 is REQUIRED** for file conversion. The tool auto-detects it via COM. You do NOT need to manually specify the path. See [VFP9 Detection](#v9-detection-how-it-works) below.

> **Credits**: This toolchain depends on [FoxBin2Prg](https://github.com/fdbozzo/foxbin2prg) by Fabio Zadro ([fdbozzo](https://github.com/fdbozzo)). FoxBin2Prg is a free, open-source utility that converts between VFP binary files (.scx/.vcx/.frx/etc.) and text. This toolchain wraps it in a strict read-only shell. See [THANKS.md](THANKS.md) for details.

---

## ⚠️ VFP9 Detection — How It Works

**VFP 9 musi być zainstalowane na komputerze** — to wymóg Windows COM. Narzędzie **automatycznie wykrywa** VFP9, nie musisz ręcznie podawać ścieżki.

### Jak to działa?

1. **Auto-detekcja via COM** — nasze VBS skrypty używają `CreateObject("VisualFoxPro.Application.9")` — Windows automatycznie znajduje zarejestrowaną instancję VFP9
2. **Nie musisz nic konfigurować** — jeśli VFP9 jest zainstalowany, COM registry jest automatycznie ustawiony
3. **Opcjonalny env var** — możesz ustawić `VFP9_EXE` jeśli masz nie-standardową instalację:

```powershell
# Windows PowerShell
$env:VFP9_EXE = "D:\Apps\VFP9\vfp9.exe"

# Linux/macOS (wine)
export VFP9_EXE="/path/to/vfp9.exe"
```

4. **Sprawdź w install.py** — instalator automatycznie wykrywa VFP9 i pokaże status

### Co potrzebujesz do instalacji?

| Component | Gdzie wziąć | Czy narzędzie auto-wykryje? |
|---|---|---|
| **VFP 9** (vfp9.exe) | Microsoft / Visual Studio subscription | ✅ Tak — via COM |
| **FoxBin2Prg** (foxbin2prg.prg) | [GitHub: fdbozzo/foxbin2prg](https://github.com/fdbozzo/foxbin2prg) | ✅ Tak — `install.py` szuka w domyślnych lokalizacjach lub `VFP_FOXBIN2PRG_DIR` |
| **Python 3** | [python.org](https://python.org) | ✅ Tak — `py` albo `python3` w PATH |

### Co się stanie jeśli VFP9 nie jest zainstalowane?

- `vfp_detect` → **działa** (tylko skanuje pliki)
- `vfp_status` → **pokaże błąd** "VFP9 not found"
- `vfp_sync` / `vfp_export_*` → **pokaże błąd** "COM object creation failed"
- `vfp_index` / `vfp_find_symbol` / `vfp_trace` → **działają** ale tylko na istniejących plikach `.sc2`/`.vc2` (bez sync nie ma plików do analizy)
- `vfp_export_table` / `vfp_list_tables` → **działają** bez VFP9! Czytaszą pliki DBF bezpośrednio w Pythonie

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

An **agent** is a pre-configured persona. Place `.md` files in `~/.config/opencode/agents/`. Each file becomes an agent you can invoke with `@agent-name`. The `@vfp-analyst` agent knows about VFP project structure, FoxBin2Prg output format, and the 13 tools this repo provides. It acts as an expert VFP developer assistant inside OpenCode.

### 14 Tools This Repo Provides

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
| `vfp_audit` | Comprehensive audit: sync + DBF schema + table relationships + class analysis → target directory | ⚠️ Partial |

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/PeterPirog/vfp-integration-toolchain.git
cd vfp-integration-toolchain

# 2. Run the installer (needs FoxBin2Prg directory)
py install.py --foxbin2prg-dir "C:\path\to\foxbin2prg"

# 3. Set environment variable (install.py prints the command)
# Windows PowerShell:
$env:VFP_TOOLCHAIN_HOME = "C:\path\to\vfp-integration-toolchain"
# Linux/macOS:
export VFP_TOOLCHAIN_HOME="/path/to/vfp-integration-toolchain"

# 4. Use in ANY OpenCode session targeting a VFP project
opencode vfp_detect
opencode vfp_sync --full
opencode vfp_find_symbol --query "MyForm"
```

---

## Installation

### Prerequisites

| Requirement | Details |
|---|---|
| **VFP 9** | Installed at default path (`C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe`) or set `VFP9_EXE` env var. **Not needed** for DBF export tools (see below) |
| **Python 3** | Accessible as `py` (Windows) or `python3` (Linux/macOS) |
| **FoxBin2Prg** | [Download from GitHub](https://github.com/fdbozzo/foxbin2prg) — place `foxbin2prg.prg` somewhere on disk. **Not needed** for DBF schema/data export |
| **dbfread** (optional) | `pip install dbfread` — provides better DBF field type parsing. If not installed, a built-in minimal DBF reader is used as fallback |

### One-Step Install

```bash
git clone https://github.com/PeterPirog/vfp-integration-toolchain.git
cd vfp-integration-toolchain

# Optional: install dbfread for better DBF field type parsing
pip install dbfread  # or: py -m pip install dbfread

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

### Warp AI vs OpenCode AI

- **Warp AI** (Ctrl+L): General terminal AI, runs commands for you
- **OpenCode** (Ctrl+O): Project-aware agent, understands codebase context

For VFP work, use **OpenCode** — the `@vfp-analyst` agent has domain-specific knowledge about VFP projects, FoxBin2Prg output format, and the 13 tools in this repo.

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
├── THANKS.md              ← Attributions (Fabio Zadro / FoxBin2Prg, dbfbridge / dbfread)
├── install.py             ← One-step installer (symlinks + verify)
├── requirements.txt       ← Optional Python dependencies (dbfread)
├── .gitignore
├── config.json            ← Portable VFP/FoxBin2Prg config (schema v2)
├── FoxBin2Prg-AI.cfg      ← Strict read-only AI profile
├── vfp_driver.py          ← Python orchestrator (all subcommands)
├── vfp_dbf_export.py      ← Pure-Python DBF schema + data export (no VFP9)
├── vfp_audit.py           ← Comprehensive project auditor
├── vfp_convert.vbs        ← VBS driver for BIN2PRG (17-param execute())
├── vfp_indexer.py         ← SC2/VC2 parser → JSON symbol index
├── vfp_verno.vbs          ← VBS driver for version check
├── tools/
│   └── vfp.ts             ← 14 OpenCode custom tools (TypeScript)
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
opencode vfp_audit --source "D:\Logis_projekt\logis_bok_4" --out "D:\Logis_audit"

# Audit without VFP9 (schema + relationships only, uses existing cache)
opencode vfp_audit --source "D:\Logis_projekt\logis_bok_4" --out "D:\Logis_audit" --skip-sync

# Comprehensive audit with data export (JSONL + CSV)
opencode vfp_audit --source "D:\Logis_projekt\logis_bok_4" --out "D:\Logis_audit" --include-data --data-formats jsonl,csv
```

**What gets generated in the output directory:**
- `audit_report.md` — Human-readable Markdown summary
- `project_summary.json` — File inventory, class/method counts
- `database_schema.json` — All DBF table schemas with encodings, fields, types
- `table_relationships.json` — Table usage patterns, SQL SELECT/INSERT/REPLACE, inferred joins
- `class_analysis.json` — Class hierarchy, inheritance depth, complexity ranking
- `dbf/` — Individual `<table>_schema.json` files for each DBF

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
│    └── dbf_list   → vfp_dbf_export.py → dbfread (no VFP9)    │
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
  "classPerFile": 2
}
```

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

**Partially yes** — for the **code/logic layer**. **No** for the **data layer** (table records).

### What IS captured (sufficient for code rewrite)

| Component | Source Files | What's captured |
|---|---|---|
| **Form classes** | `.scx` → `.sc2` (840 files) | ✅ Full class definition, all 6,233 methods with code, 6,262 properties with values, all controls (ADD OBJECT trees) |
| **Class libraries** | `.vcx` → `.vc2` (41 files) | ✅ Full class hierarchy, 530 methods with code, all properties |
| **Reports** | `.frx` → `.fr2` (65 files) | ✅ Report structure, fields, groups |
| **Projects** | `.pjx` → `.pj2` (8 files) | ✅ Project file lists, main program, file types (K=Form, P=PRG, D=DBF) |
| **Table structure** | `.dbf` → schema via `vfp_export_table` (pure Python, no VFP9) | ✅ Field names, types, lengths, decimals, codepage, record count, memo presence |
| **Table data** | `.dbf` data via `vfp_export_table --format jsonl` | ✅ Full record data export to JSONL/CSV (pure Python, no VFP9) |
| **PRG files** | `.prg` (14 files in PJX) | ⚠️ Referenced in PJ2 but NOT converted to cache (they're already text) |

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
| **PRG source files** | Not copied to `.vfp-ai/source/` cache | Copy manually or enhance sync |

### For a complete application rewrite, you need:

1. **This toolchain's output** (`vfp_sync`) → provides all class/method/property code ✅
2. **This toolchain's DBF export** (`vfp_export_table`) → table schemas + data ✅ (no longer needs external tools)
3. **DBC schema export** → table relationships and constraints
4. **PRG file analysis** → copy PRG files to cache or search source project

### One-Command Audit

Use `vfp_audit` to generate a complete project audit in any target directory:

```bash
opencode vfp_audit --source "/path/to/vfp/project" --out "/path/to/audit/output"
```

This generates:
- **`audit_report.md`** — human-readable audit summary
- **`project_summary.json`** — file inventory, class/method counts
- **`database_schema.json`** — all DBF table schemas with encodings
- **`table_relationships.json`** — table usage patterns, inferred SQL joins
- **`class_analysis.json`** — class hierarchy, inheritance depth, complexity ranking

The `@vfp-analyst` agent can then read these files and answer questions like:
- "Which tables have the most records?"
- "What are the inheritance chains for each form?"
- "Are there inefficient table joins in the code?"
- "What DBF encodings are used in this project?"

### Recommendation

Use this toolchain to reverse-engineer the **application logic** (forms, classes, methods). Then use `vfp_export_table` for the **data layer** (table schemas + data). The DBF export works with pure Python (`dbfread` library) — **no VFP9 required**.

---

## Tested

Verified on `D:\Logis_projekt\logis_bok_4` (1,218 binary files):
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
7. **DBF memo content**: Fallback reader (without `dbfread`/`FoxBin2Prg`) can detect memo fields but cannot read FPT content. Install `dbfread` for full memo support: `pip install dbfread`.

## Credits

- **FoxBin2Prg** by [Fabio Zadro (fdbozzo)](https://github.com/fdbozzo) — https://github.com/fdbozzo/foxbin2prg
  - This entire toolchain depends on FoxBin2Prg's `c_foxbin2prg` COM class
  - All BIN2PRG/PRG2BIN logic is Fabio's work; this repo only wraps it in a read-only shell
  - Licensed under FoxBin2Prg's own license (MIT-like)
