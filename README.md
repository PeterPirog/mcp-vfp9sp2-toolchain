# VFP Integration Toolchain for OpenCode

Strict read-only integration between [OpenCode](https://opencode.ai) AI agents and Visual FoxPro 9 projects via [FoxBin2Prg](https://github.com/fdbozzo/foxbin2prg) text conversion.

**No PRG2BIN. No recompilation. No source modification. Ever.**

## Features

- **11 OpenCode custom tools** (`vfp_detect`, `vfp_status`, `vfp_export_file`, `vfp_export_project`, `vfp_export_class`, `vfp_sync`, `vfp_index`, `vfp_find_symbol`, `vfp_find_references`, `vfp_find_table_usage`, `vfp_trace`)
- **`@vfp-analyst` agent** for conversational VFP project analysis
- **Strict read-only**: `tcRecompile=0`, `InhibitInheritance=3`, `cOutputFolder` redirect to cache
- **Symbol indexing**: Extract classes, methods, properties from 600+ VFP objects
- **Inheritance tracing**: Follow class hierarchies across VCX/SCX libraries
- **Table usage scanning**: Find USE/SELECT/INSERT/REPLACE patterns in source

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/yourusername/vfp-integration-toolchain.git
cd vfp-integration-toolchain
py install.py --foxbin2prg-dir "C:\path\to\foxbin2prg"

# 2. Set environment (or let install.py set it for you)
export VFP_TOOLCHAIN_HOME="/path/to/vfp-integration-toolchain"

# 3. Use in any OpenCode session targeting a VFP project
opencode vfp_detect
opencode vfp_sync
opencode vfp_find_symbol --query "MyForm"
opencode vfp_trace --className "f_base1"
```

## Repository Structure

```
vfp-integration-toolchain/
├── README.md              ← This file
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
├── agents/
│   └── vfp-analyst.md     ← @vfp-analyst agent prompt
└── INTERNAL_RAG/          ← Persistent operational memory
```

## Installation

### Prerequisites

- **Windows** with Visual FoxPro 9 installed (`vfp9.exe`)
- **Python 3** (accessible as `py` or `python3`)
- **FoxBin2Prg v1.21+** (download from [GitHub](https://github.com/fdbozzo/foxbin2prg))

### Install Script

```bash
py install.py
```

Options:
- `--toolchain-dir PATH` — Override toolchain root (default: script directory)
- `--opencode-config PATH` — Override OpenCode config dir (default: `~/.config/opencode`)
- `--foxbin2prg-dir PATH` — FoxBin2Prg source directory
- `--no-symlink` — Copy files instead of symlinking (Windows without admin)
- `--no-verify` — Skip post-install verification

The installer:
1. Locates FoxBin2Prg (checks env var, provided path, default locations)
2. Locates VFP9 (checks `VFP9_EXE` env var, default install path)
3. Symlinks `tools/vfp.ts` → `~/.config/opencode/tools/vfp.ts`
4. Symlinks `agents/vfp-analyst.md` → `~/.config/opencode/agents/vfp-analyst.md`
5. Verifies with `vfp_status`

### Manual Installation

```bash
# Set toolchain location
export VFP_TOOLCHAIN_HOME="/path/to/vfp-integration-toolchain"

# Symlink (or copy) to OpenCode config
ln -s $VFP_TOOLCHAIN_HOME/tools/vfp.ts ~/.config/opencode/tools/vfp.ts
ln -s $VFP_TOOLCHAIN_HOME/agents/vfp-analyst.md ~/.config/opencode/agents/vfp-analyst.md
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `VFP_TOOLCHAIN_HOME` | Root directory of this toolchain | `~/.config/opencode/vfp` |
| `VFP_FOXBIN2PRG_DIR` | Directory containing `foxbin2prg.prg` | `tools/foxbin2prg` relative to toolchain |
| `VFP9_EXE` | Path to `vfp9.exe` | `C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe` |

## Usage

### OpenCode Custom Tools

```bash
# Detect VFP project artifacts
opencode vfp_detect --directory /path/to/vfp/project

# Check toolchain status
opencode vfp_status

# Full project sync (convert all binaries + build index)
opencode vfp_sync --directory /path/to/vfp/project --full

# Search symbol index
opencode vfp_find_symbol --query "MyForm" --directory /path/to/vfp/project

# Trace class inheritance
opencode vfp_trace --className "myBaseForm" --directory /path/to/vfp/project

# Find references to a symbol
opencode vfp_find_references --query "myFunction"

# Find table usage patterns
opencode vfp_find_table_usage --tableName "CUSTOMERS"

# Export single class from VCX
opencode vfp_export_class --library "lib.vcx" --className "MyClass"
```

### Via Python Driver Directly

```bash
# Version check
py vfp_driver.py verno --prg "tools/foxbin2prg/foxbin2prg.prg"

# Single file conversion
py vfp_driver.py convert --input "src/forms/myform.scx" --type BIN2PRG \
  --out ".vfp-ai/source" --cfg "FoxBin2Prg-AI.cfg" --prg "tools/foxbin2prg/foxbin2prg.prg"

# Directory sync
py vfp_driver.py convert_dir --project "src" --out ".vfp-ai/source" \
  --cfg "FoxBin2Prg-AI.cfg" --prg "tools/foxbin2prg/foxbin2prg.prg"

# Build symbol index
py vfp_driver.py index --project ".vfp-ai/source" --cache ".vfp-ai" --full
```

### Via @vfp-analyst Agent

```bash
opencode @vfp-analyst "Find all forms that reference the CUSTOMERS table in this VFP project"
```

## Safety Guarantees

| Guarantee | Mechanism |
|---|---|
| No binary regeneration | `tcRecompile='0'` in all execute() calls |
| No source file modification | `cOutputFolder` redirects all output to `.vfp-ai/source/` |
| No config inheritance | `InhibitInheritance: 3` in `FoxBin2Prg-AI.cfg` |
| No PRG2BIN ever | Whitelist gate in `vfp_convert.vbs` rejects any PRG2BIN direction |
| All output goes to cache | `--out` always points to `.vfp-ai/` directory |
| Timestamp-agnostic | `tcNoTimestamps='1'`, `tcClearUniqueID='1'` |

## Configuration

### config.json (schema v2)

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
