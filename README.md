# VFP Integration Toolchain for OpenCode

Strict read-only integration between [OpenCode](https://opencode.ai) AI agents and Visual FoxPro 9 projects via [FoxBin2Prg](https://github.com/fdbozzo/foxbin2prg) text conversion.

**No PRG2BIN. No recompilation. No source modification. Ever.**

> **Credits**: This toolchain depends on [FoxBin2Prg](https://github.com/fdbozzo/foxbin2prg) by Fabio Zadro ([fdbozzo](https://github.com/fdbozzo)). FoxBin2Prg is a free, open-source utility that converts between VFP binary files (.scx/.vcx/.frx/etc.) and text. This toolchain wraps it in a strict read-only shell. See [THANKS.md](THANKS.md) for details.

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

An **agent** is a pre-configured persona. Place `.md` files in `~/.config/opencode/agents/`. Each file becomes an agent you can invoke with `@agent-name`. The `@vfp-analyst` agent knows about VFP project structure, FoxBin2Prg output format, and the 11 tools this repo provides. It acts as an expert VFP developer assistant inside OpenCode.

### 11 Tools This Repo Provides

| Tool | What it does |
|---|---|
| `vfp_detect` | Scans a directory — tells you if VFP files exist and what types |
| `vfp_status` | Checks that VFP9.exe and FoxBin2Prg are installed and working |
| `vfp_export_file` | Converts one binary file (.scx/.vcx/.frx) to text (.sc2/.vc2) |
| `vfp_export_project` | Converts all binary files in a directory tree |
| `vfp_export_class` | Extracts one class from a library: `vfp_export_class --library lib.vcx --className MyClass` |
| `vfp_sync` | Does `vfp_export_project` + builds search index (one command) |
| `vfp_index` | Builds/refreshes the JSON symbol index from cached text files |
| `vfp_find_symbol` | Searches the index for class/method/property names |
| `vfp_find_references` | Searches converted text files for references to a symbol |
| `vfp_find_table_usage` | Finds USE/SELECT/INSERT/REPLACE patterns in source |
| `vfp_trace` | Follows a class's inheritance chain (MyClass → Form → Container → Object) |

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
| **VFP 9** | Installed at default path (`C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe`) or set `VFP9_EXE` env var |
| **Python 3** | Accessible as `py` (Windows) or `python3` (Linux/macOS) |
| **FoxBin2Prg** | [Download from GitHub](https://github.com/fdbozzo/foxbin2prg) — place `foxbin2prg.prg` somewhere on disk |

### One-Step Install

```bash
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

---

## Repository Structure

```
vfp-integration-toolchain/
├── README.md              ← This file
├── THANKS.md              ← Attributions (Fabio Zadro / FoxBin2Prg)
├── install.py             ← One-step installer (symlinks + verify)
├── .gitignore
├── config.json            ← Portable VFP/FoxBin2Prg config (schema v2)
├── FoxBin2Prg-AI.cfg      ← Strict read-only AI profile
├── vfp_driver.py          ← Python orchestrator (verno/convert/index)
├── vfp_convert.vbs        ← VBS driver for BIN2PRG (17-param execute())
├── vfp_indexer.py         ← SC2/VC2 parser → JSON symbol index
├── vfp_verno.vbs          ← VBS driver for version check
├── tools/
│   └── vfp.ts             ← 11 OpenCode custom tools (TypeScript)
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
```

### Via @vfp-analyst Agent

```bash
opencode @vfp-analyst "Find all forms that reference the CUSTOMERS table"
opencode @vfp-analyst "Trace the inheritance chain for the 'form_archdoplan' class"
opencode @vfp-analyst "Show me all methods named 'Click' in this project"
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
│    └── index  →  vfp_indexer.py →  parse .sc2/.vc2 → index   │
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

## Tested

Verified on `D:\Logis_projekt\logis_bok_4` (1,218 binary files):
- 631/633 files converted successfully (2 failures: missing .CDX files)
- 946 text files generated in `.vfp-ai/source/`
- 0 source files modified (SHA256/size/mtime verified unchanged)
- Index: 599 classes, 8,168 methods across 954 text files
- `cOutputFolder` correctly redirects all output to cache

## Limitations

1. **Windows-only**: VFP9 COM host is Windows-specific
2. **Requires VFP9 installed**: No standalone FoxBin2Prg.exe exists; the VFP9 COM automation host is required
3. **DBF without CDX**: Files missing structural CDX will fail conversion (rc != 0)
4. **Large projects**: Full sync of 600+ files takes ~5 minutes (VFP9 COM startup per file)

## Credits

- **FoxBin2Prg** by [Fabio Zadro (fdbozzo)](https://github.com/fdbozzo) — https://github.com/fdbozzo/foxbin2prg
  - This entire toolchain depends on FoxBin2Prg's `c_foxbin2prg` COM class
  - All BIN2PRG/PRG2BIN logic is Fabio's work; this repo only wraps it in a read-only shell
  - Licensed under FoxBin2Prg's own license (MIT-like)
