# Credits & Attributions

## Licensing

This project (the toolchain wrapper: `vfp_driver.py`, `vfp_audit.py`,
`vfp_dbf_export.py`, `vfp_indexer.py`, `vfp_convert.vbs`, `vfp_verno.vbs`,
`tools/vfp.ts`, `agents/vfp-analyst.md`, `install.py`) is released under the
**MIT License** — see [LICENSE](LICENSE).

Third-party components retain their own licenses:
- **FoxBin2Prg** (runtime, not vendored) — see below.
- **dbfbridge** (vendored under `tools/dbfbridge/`) — MIT, see `tools/dbfbridge/LICENSE`.
- **dbfread** (pip dependency) — see below.

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

## DBF support

This repo ships its own DBF backend and relies on one third-party library:

- **`dbfbridge`** — the DBF export/import engine, **bundled** in this repo under
  `tools/dbfbridge/` (MIT, frozen snapshot — see `tools/dbfbridge/VERSION.txt`).
  Provides memo/FPT-aware export, batch export, JSONL/CSV/XLSX, and
  reconstruction/round-trip validation. Loaded from the repo, so it does **not**
  need to be pip-installed.
- **`dbfread`** — https://github.com/elixir-dbf/dbfread — streaming DBF/FPT reader
  (field descriptors, records, memo data). This is the only runtime pip dependency.

When neither is available, `vfp_dbf_export.py` falls back to a built-in minimal DBF
reader (schema + non-memo data, no FPT).

**Install**: `pip install dbfread` (the only runtime dependency).

### DBF_Anonymizer (pinned, vendored)

- **`DBF_Anonymizer`** — https://github.com/PeterPirog/DBF_Anonymizer — v0.3.0,
  vendored frozen snapshot under `tools/dbf_anonymizer/` (see
  `tools/dbf_anonymizer/VERSION.txt`). MIT per the upstream `pyproject.toml` at the
  pinned commit (`ed7915497862850c3de650f2c50c86569442ff77`). Loaded from the repo;
  not pip-installed, never downloaded at runtime.
- Depends on `dbfbridge` pinned to `addbadb9281914661bf742924f45039e46a895cd` —
  the same vendored snapshot this toolchain already ships, so there is a single
  shared dbfbridge. See `tools/VENDORED_DEPENDENCIES.json`.

### Thank you

Thank you to the **dbfread** project (elixir-dbf) for the streaming DBF/FPT reader that
underpins the data export.
