# Credits & Attributions

## FoxBin2Prg — Fabio Zadro (fdbozzo)

**Repository**: https://github.com/fdbozzo/foxbin2prg  
**Author**: [Fabio Zadro](https://github.com/fdbozzo)  
**License**: MIT-like (see FoxBin2Prg source for details)

### Why this matters

This entire VFP integration toolchain depends on FoxBin2Prg's `c_foxbin2prg` COM class. FoxBin2Prg is a free, open-source utility that:

- Converts VFP binary files (`.scx`, `.vcx`, `.frx`, `.mnx`, `.lbx`, `.pjx`, `.dbc`, `.dbf`) to text (`.sc2`, `.vc2`, `.fr2`, `.mn2`, `.lb2`, `.db2`, etc.)
- Converts text back to binary (`PRG2BIN`) — **this toolchain explicitly does NOT use this direction**
- Runs inside the VFP9 COM automation host (`VisualFoxPro.Application.9`)

### What we took vs. what's ours

| Component | Source |
|---|---|
| `c_foxbin2prg` object, `execute()` method, all BIN2PRG/PRG2BIN logic | **Fabio Zadro / FoxBin2Prg** |
| `foxbin2prg.prg` script (the runtime) | **Fabio Zadro / FoxBin2Prg** |
| `FoxBin2Prg-AI.cfg` configuration (adapted for read-only use) | **Based on FoxBin2Prg examples** |
| `vfp_convert.vbs` (VBS driver host) | **This repo** (inspired by upstream `Convert_VFP9_BIN_2_PRG.vbs`) |
| `vfp_driver.py` (Python orchestrator) | **This repo** |
| `vfp_indexer.py` (SC2/VC2 parser) | **This repo** |
| `vfp_dbf_export.py` (DBF schema/data export) | **This repo** (architecture inspired by dbfbridge) |
| `tools/vfp.ts` (OpenCode custom tools) | **This repo** |
| `agents/vfp-analyst.md` (OpenCode agent) | **This repo** |
| `install.py` (one-step installer) | **This repo** |

### Safety design

This toolchain wraps FoxBin2Prg with strict read-only constraints:

1. **`tcRecompile = 0`** — FoxBin2Prg parameter #12 prevents recompilation of source PRG files
2. **`cOutputFolder`** — Redirects all output to `.vfp-ai/source/` cache, never to source directories
3. **`InhibitInheritance = 3`** — Prevents loading of project-level FoxBin2Prg config files
4. **Whitelist gate** — `vfp_convert.vbs` only allows `BIN2PRG`, `*`, `*-*` as type. Any `PRG2BIN` direction is rejected with exit code 1.
5. **No config file import** — The AI profile (`FoxBin2Prg-AI.cfg`) explicitly sets all conversion support flags to text-only (`= 1`)

### FoxBin2Prg original files used

- `foxbin2prg.prg` — Main script (1.3+ MB, the COM class definition)
- `foxbin2prg.fxo` — Compiled form (if present in your FoxBin2Prg download)

These files are NOT included in this repository. You must download them separately from:

**https://github.com/fdbozzo/foxbin2prg**

### Thank you

Thank you, Fabio — for creating and maintaining FoxBin2Prg, without which this integration would not be possible.

---

## DBF support: dbfread (khicaey/ExcelPython) and dbfbridge

**dbfread**: https://github.com/elixir-dbf/dbfread  
**dbfbridge**: https://github.com/PeterPirog/dbfbridge  

The DBF schema and data export tooling (`vfp_dbf_export.py`, `vfp_export_table`, `vfp_list_tables`) is inspired by the `dbfbridge` project by Peter Pirog. This toolchain does **NOT** depend on the `dbfbridge` package as an external dependency — instead, it uses the same underlying `dbfread` library directly, with a built-in minimal DBF reader as a fallback when `dbfread` is not installed.

- `dbfread` provides streaming DBF/FPT reading (field descriptors, records, memo data)
- `dbfbridge` provides the architectural pattern (schema JSON + data JSONL export)
- This repo re-implements the pattern independently — no `dbfbridge` import required

**Install**: `pip install dbfread` (optional — built-in reader used as fallback)

Thank you to both projects for their excellent work on VFP DBF handling.
