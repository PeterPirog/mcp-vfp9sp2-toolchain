import { tool } from "@opencode-ai/plugin"
import { readFileSync, existsSync, readdirSync, statSync } from "fs"
import { join } from "path"

const py = process.platform === "win32" ? "py" : "python3"

const TOOLCHAIN_HOME = process.env.VFP_TOOLCHAIN_HOME ||
  join(
    process.env.HOME || process.env.USERPROFILE || "",
    ".config", "opencode", "vfp"
  )

const DRIVER = join(TOOLCHAIN_HOME, "vfp_driver.py")
const CONFIG = join(TOOLCHAIN_HOME, "config.json")
const CFG_FILE = join(TOOLCHAIN_HOME, "FoxBin2Prg-AI.cfg")

function loadConfig(): Record<string, any> | null {
  try {
    return JSON.parse(readFileSync(CONFIG, "utf-8"))
  } catch {
    return null
  }
}

// Canonical exclusion list, kept in sync with config.json -> defaultExcludes
// and vfp_common.default_excludes() (Python). Fallback if config is unreadable.
function excludeDirs(cfg: Record<string, any> | null): string[] {
  const raw = (cfg?.defaultExcludes || ["backup", "backups", "archive"]).map((s: string) => String(s).toLowerCase())
  return raw
}

function isExcludedDir(item: string, cfg: Record<string, any> | null): boolean {
  if (item.startsWith(".")) return true
  return excludeDirs(cfg).includes(item.toLowerCase())
}

function foxbin2prgDir(cfg: Record<string, any> | null): string {
  const fb = cfg?.foxbin2prg || {}
  return process.env.VFP_FOXBIN2PRG_DIR ||
    (fb.directoryEnvironmentVariable ? process.env[fb.directoryEnvironmentVariable] : null) ||
    fb.directoryDefault ||
    join(TOOLCHAIN_HOME, "tools", "foxbin2prg")
}

function resolveDriver(cfg: Record<string, any> | null): string {
  const idx = cfg?.indexer || {}
  // Coherent with config.json: honour an explicit script path, then a python
  // interpreter override, else the default vfp_driver.py in the toolchain.
  const script = idx.script || idx.python
  return script ? join(TOOLCHAIN_HOME, String(script)) : DRIVER
}

function vfp9Exe(cfg: Record<string, any> | null): string | null {
  const v = cfg?.vfp || {}
  return process.env.VFP9_EXE || v.exeEnvironmentVariable && process.env[v.exeEnvironmentVariable] || v.exeDefault || null
}

export const vfp_detect = tool({
  description:
    "Detect whether a directory contains Visual FoxPro project artifacts (.scx/.vcx/.frx/.mnx/.lbx/.pjx/.dbc/.dbf, PRG/H, etc.). Returns counts per extension and whether FoxBin2Prg text cache exists.",
  args: {
    directory: tool.schema.string().describe("Project directory to scan. Defaults to current worktree."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    const dir = args.directory || context.worktree || process.cwd()
    const exts = [".scx", ".vcx", ".frx", ".mnx", ".lbx", ".pjx", ".dbc", ".dbf", ".prg", ".h", ".sct", ".vct"]
    const counts: Record<string, number> = {}
    let total = 0
    let cacheExists = false

    async function walk(d: string) {
      try {
        const items = readdirSync(d)
        for (const item of items) {
          const full = join(d, item)
          const stat = statSync(full)
          if (stat.isDirectory()) {
            if (item === ".vfp-ai" && !cacheExists) cacheExists = true
            if (!isExcludedDir(item, cfg)) {
              await walk(full)
            }
          } else {
            if (isExcludedDir(item, cfg)) continue
            const ext = (item.slice(-4).toLowerCase())
            const ext3 = (item.slice(-3).toLowerCase())
            const e = ext.startsWith(".") ? ext : "." + ext3
            if (exts.includes(e)) {
              counts[e] = (counts[e] || 0) + 1
              total++
            }
          }
        }
      } catch {}
    }
    await walk(dir)

    return {
      directory: dir,
      totalVfpFiles: total,
      byExtension: counts,
      cacheExists,
      vfpDetected: total > 0 || cacheExists,
    }
  },
})

export const vfp_status = tool({
  description:
    "Check FoxBin2Prg version and VFP9 availability by running the verno subcommand of vfp_driver.py.",
  args: {},
  async execute(_args, _context) {
    const cfg = loadConfig()
    const prg = cfg?.foxbin2prg?.programFile || "foxbin2prg.prg"
    const prgPath = join(foxbin2prgDir(cfg), prg)
    const p = Bun.spawn([py, DRIVER, "verno", "--prg", prgPath], {
      stdout: "pipe", stderr: "pipe",
    })
    const out = await new Response(p.stdout).text()
    const err = await new Response(p.stderr).text()
    const rc = await p.exited
    if (rc !== 0) throw new Error(err || `exit ${rc}`)
    try {
      return JSON.parse(out.trim())
    } catch {
      return { raw: out.trim() }
    }
  },
})

export const vfp_export_file = tool({
  description:
    "Convert a single VFP binary file (.scx/.vcx/.frx/.mnx/.lbx/.pjx/.dbc/.dbf) to FoxBin2Prg text (.sc2/.vc2). STRICT READ-ONLY — never calls PRG2BIN.",
  args: {
    input: tool.schema.string().describe("Full path to the binary VFP file."),
    ctype: tool.schema.string().optional().describe("Conversion type: BIN2PRG (default), *, or -*-."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)

    const cacheDir = join(context.worktree || process.cwd(), cfg.cacheDirectory || ".vfp-ai")
    const prgPath = join(foxbin2prgDir(cfg), cfg.foxbin2prg?.programFile || "foxbin2prg.prg")
    const cfgPath = join(TOOLCHAIN_HOME, cfg.aiProfile?.file || "FoxBin2Prg-AI.cfg")
    const ctype = args.ctype || "BIN2PRG"

    const p = Bun.spawn(
      [py, DRIVER, "convert", "--input", args.input, "--type", ctype,
       "--out", cacheDir, "--cfg", cfgPath, "--prg", prgPath],
      { stdout: "pipe", stderr: "pipe" }
    )
    const out = await new Response(p.stdout).text()
    const err = await new Response(p.stderr).text()
    const rc = await p.exited
    try {
      const data = JSON.parse(out.trim())
      if (!data.ok) throw new Error(data.stderr || `convert failed rc=${data.rc}`)
      return data
    } catch {
      return { ok: rc === 0, stdout: out, stderr: err }
    }
  },
})

export const vfp_export_project = tool({
  description:
    "Convert all VFP binary files in a directory tree to text. Uses FoxBin2Prg BIN2PRG mode — strictly read-only.",
  args: {
    directory: tool.schema.string().describe("Project root to scan and convert."),
    ctype: tool.schema.string().optional().describe("BIN2PRG (default), *, or -*-."),
  },
  async execute(args, _context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)

    const cacheDir = join(args.directory, cfg.cacheDirectory || ".vfp-ai")
    const prgPath = join(foxbin2prgDir(cfg), cfg.foxbin2prg?.programFile || "foxbin2prg.prg")
    const cfgPath = join(TOOLCHAIN_HOME, cfg.aiProfile?.file || "FoxBin2Prg-AI.cfg")
    const ctype = args.ctype || "BIN2PRG"

    const binExts = cfg.artifacts?.bin2prg || ["pjx", "scx", "vcx", "frx", "lbx", "mnx", "dbc", "dbf"]
    const results: Array<Record<string, any>> = []

    async function walk(d: string) {
      const items = readdirSync(d)
      for (const item of items) {
        if (item.startsWith(".") || cfg.defaultExcludes?.includes(item)) continue
        const full = join(d, item)
        const stat = statSync(full)
        if (stat.isDirectory()) {
          await walk(full)
        } else if (stat.isFile()) {
          const ext = item.slice(-3).toLowerCase()
          if (binExts.map(e => e.toLowerCase()).includes(ext)) {
            const p2 = Bun.spawn(
              [py, DRIVER, "convert", "--input", full, "--type", ctype,
               "--out", cacheDir, "--cfg", cfgPath, "--prg", prgPath],
              { stdout: "pipe", stderr: "pipe" }
            )
            const out = await new Response(p2.stdout).text()
            await p2.exited
            try {
              const data = JSON.parse(out.trim())
              results.push({ file: item, ok: data.ok, rc: data.rc })
            } catch {
              results.push({ file: item, ok: false, raw: out.trim() })
            }
          }
        }
      }
    }
    await walk(args.directory)

    const failures = results.filter((r) => !r.ok)
    return {
      total: results.length,
      succeeded: results.length - failures.length,
      failed: failures.length,
      results,
      cacheDir,
    }
  },
})

export const vfp_export_class = tool({
  description:
    "Extract a single class definition from a VCX/SCX library as text using the lib.vcx::ClassName syntax.",
  args: {
    library: tool.schema.string().describe("Full path to the .vcx or .scx library file."),
    className: tool.schema.string().describe("Class name to extract from the library."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)

    const cacheDir = join(context.worktree || process.cwd(), cfg.cacheDirectory || ".vfp-ai")
    const prgPath = join(foxbin2prgDir(cfg), cfg.foxbin2prg?.programFile || "foxbin2prg.prg")
    const cfgPath = join(TOOLCHAIN_HOME, cfg.aiProfile?.file || "FoxBin2Prg-AI.cfg")

    const inputSpec = args.library + "::" + args.className
    const p = Bun.spawn(
      [py, DRIVER, "convert", "--input", inputSpec, "--type", "BIN2PRG",
       "--out", cacheDir, "--cfg", cfgPath, "--prg", prgPath],
      { stdout: "pipe", stderr: "pipe" }
    )
    const out = await new Response(p.stdout).text()
    try {
      const data = JSON.parse(out.trim())
      if (!data.ok) throw new Error(data.stderr || `convert failed rc=${data.rc}`)
      return data
    } catch {
      return { ok: false, stdout: out, stderr: "" }
    }
  },
})

export const vfp_sync = tool({
  description:
    "Run a full BIN2PRG sync of a project directory to the .vfp-ai cache, then build the symbol index.",
  args: {
    directory: tool.schema.string().describe("Project root to sync."),
    full: tool.schema.boolean().optional().describe("Re-parse all .sc2/.vc2 files for symbols (slower)."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)
    const dir = args.directory || context.worktree || process.cwd()
    const cacheDir = join(dir, cfg.cacheDirectory || ".vfp-ai")

    const prgPath = join(foxbin2prgDir(cfg), cfg.foxbin2prg?.programFile || "foxbin2prg.prg")
    const cfgPath = join(TOOLCHAIN_HOME, cfg.aiProfile?.file || "FoxBin2Prg-AI.cfg")

    const p1 = Bun.spawn(
      [py, DRIVER, "convert_dir", "--project", dir,
       "--out", cacheDir, "--cfg", cfgPath, "--prg", prgPath],
      { stdout: "pipe", stderr: "pipe" }
    )
    const out1 = await new Response(p1.stdout).text()
    const rc1 = await p1.exited

    const p2 = Bun.spawn(
      [py, DRIVER, "index", "--project", join(cacheDir, "source"), "--cache", cacheDir,
       ...(args.full ? ["--full"] : [])],
      { stdout: "pipe", stderr: "pipe" }
    )
    const out2 = await new Response(p2.stdout).text()
    const rc2 = await p2.exited

    return {
      convertRc: rc1,
      indexRc: rc2,
      convertOutput: out1.trim(),
      indexOutput: out2.trim(),
      cacheDir,
    }
  },
})

export const vfp_index = tool({
  description:
    "Build or refresh the symbol index from .sc2/.vc2 text files in a cache directory.",
  args: {
    directory: tool.schema.string().optional().describe("Project root. Defaults to current worktree."),
    cache: tool.schema.string().optional().describe("Cache directory (default: <project>/.vfp-ai)."),
    full: tool.schema.boolean().optional().describe("Parse file contents for classes/methods/properties."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)
    const dir = args.directory || context.worktree || process.cwd()
    const cacheDir = args.cache || join(dir, cfg.cacheDirectory || ".vfp-ai")

    const p = Bun.spawn(
      [py, DRIVER, "index", "--project", join(cacheDir, "source"), "--cache", cacheDir,
       ...(args.full ? ["--full"] : [])],
      { stdout: "pipe", stderr: "pipe" }
    )
    const out = await new Response(p.stdout).text()
    const err = await new Response(p.stderr).text()
    const rc = await p.exited
    if (rc !== 0) throw new Error(err || `exit ${rc}`)
    try {
      return JSON.parse(out.trim())
    } catch {
      return { raw: out.trim() }
    }
  },
})

export const vfp_find_symbol = tool({
  description:
    "Search the symbol index for a class, method, or property name.",
  args: {
    query: tool.schema.string().describe("Symbol name or partial name to search for."),
    directory: tool.schema.string().optional().describe("Project root (default: current worktree)."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)
    const dir = args.directory || context.worktree || process.cwd()
    const cacheDir = join(dir, cfg.cacheDirectory || ".vfp-ai")
    const idxPath = join(cacheDir, "index.json")
    if (!existsSync(idxPath)) throw new Error("Index not found at " + idxPath + ". Run vfp_index first.")

    const idx = JSON.parse(readFileSync(idxPath, "utf-8"))
    const q = args.query.toLowerCase()
    const results: Array<Record<string, any>> = []

    for (const [fn, finfo] of Object.entries(idx["files"] as Record<string, any>)) {
      const syms = finfo["symbols"]
      if (!syms) continue
      for (const cls of syms["classes"] || []) {
        if (cls["name"].toLowerCase().includes(q)) {
          results.push({ file: fn, type: "class", name: cls["name"], baseClass: cls["baseClass"] })
        }
        for (const m of cls["methods"] || []) {
          if (m["name"].toLowerCase().includes(q)) {
            results.push({ file: fn, type: "method", name: m["name"], class: cls["name"] })
          }
        }
        for (const p of cls["properties"] || []) {
          if (p["name"].toLowerCase().includes(q)) {
            results.push({ file: fn, type: "property", name: p["name"], class: cls["name"] })
          }
        }
      }
    }
    return { query: args.query, matches: results.length, results }
  },
})

export const vfp_find_references = tool({
  description:
    "Search within .scn/.vcn text files for references to a class name, property, or method.",
  args: {
    query: tool.schema.string().describe("Symbol name to search for in converted text files."),
    directory: tool.schema.string().optional().describe("Project root (default: current worktree)."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)
    const dir = args.directory || context.worktree || process.cwd()
    const cacheDir = join(dir, cfg.cacheDirectory || ".vfp-ai")
    const q = new RegExp(args.query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi")
    const results: Array<Record<string, any>> = []

    async function walk(d: string) {
      try {
        const items = readdirSync(d)
        for (const item of items) {
          if (item.startsWith(".") || cfg.defaultExcludes?.includes(item)) continue
          const full = join(d, item)
          const stat = statSync(full)
          if (stat.isDirectory()) await walk(full)
          else if (stat.isFile() && (item.endsWith(".sc2") || item.endsWith(".vc2") || item.endsWith(".prg"))) {
            const text = readFileSync(full, "utf-8")
            const lines = text.split("\n")
            for (let i = 0; i < lines.length; i++) {
              if (q.test(lines[i])) {
                results.push({
                  file: item,
                  line: i + 1,
                  content: lines[i].trim().slice(0, 200),
                })
                q.lastIndex = 0
              }
            }
          }
        }
      } catch {}
    }
    await walk(cacheDir)
    return { query: args.query, matches: results.length, results: results.slice(0, 50) }
  },
})

export const vfp_find_table_usage = tool({
  description:
    "Scan PRG and converted text files for table/file usage patterns (USE, ALIAS, TABLE, SELECT, INSERT, REPLACE, etc.).",
  args: {
    tableName: tool.schema.string().optional().describe("Specific table name to search for. If omitted, finds all table references."),
    directory: tool.schema.string().optional().describe("Project root (default: current worktree)."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)
    const dir = args.directory || context.worktree || process.cwd()
    const cacheDir = join(dir, cfg.cacheDirectory || ".vfp-ai")
    const tablePat = args.tableName
      ? new RegExp(args.tableName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi")
      : /(?:USE|ALIAS|TABLE|SELECT|INSERT|REPLACE|APPEND|DELETE|RECALL|DBGET\w*|SEEK|FIND)\s+[`"']?(\w+)/gi

    const results: Array<Record<string, any>> = []
    async function walk(d: string) {
      try {
        const items = readdirSync(d)
        for (const item of items) {
          if (item.startsWith(".")) continue
          const full = join(d, item)
          const stat = statSync(full)
          if (stat.isDirectory()) await walk(full)
          else if (stat.isFile() && (item.endsWith(".prg") || item.endsWith(".sc2") || item.endsWith(".vc2"))) {
            const text = readFileSync(full, "utf-8")
            for (const line of text.split("\n")) {
              const m = tablePat.exec(line)
              if (m) {
                const tbl = args.tableName ? args.tableName : m[1]
                results.push({ file: item, table: tbl, content: line.trim().slice(0, 200) })
              }
            }
          }
        }
      } catch {}
    }
    await walk(cacheDir)
    return { tableName: args.tableName || "(all)", matches: results.length, results: results.slice(0, 50) }
  },
})

export const vfp_trace = tool({
  description:
    "Trace inheritance chain for a VFP class by following base class references across library files.",
  args: {
    className: tool.schema.string().describe("Class name to trace through inheritance."),
    directory: tool.schema.string().optional().describe("Project root (default: current worktree)."),
    maxDepth: tool.schema.number().optional().describe("Maximum depth to follow (default 10)."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)
    const dir = args.directory || context.worktree || process.cwd()
    const cacheDir = join(dir, cfg.cacheDirectory || ".vfp-ai")
    const idxPath = join(cacheDir, "index.json")
    if (!existsSync(idxPath)) throw new Error("Index not found. Run vfp_index first.")

    const idx = JSON.parse(readFileSync(idxPath, "utf-8"))
    const chain: Array<Record<string, any>> = []
    let current = args.className
    const visited = new Set<string>()
    const max = args.maxDepth || 10

    for (let depth = 0; depth < max && !visited.has(current); depth++) {
      visited.add(current)
      let found = false
      for (const cls of idx["classes"] || []) {
        if (cls["name"].toLowerCase() === current.toLowerCase()) {
          chain.push({ name: cls["name"], baseClass: cls["baseClass"], file: cls["file"], depth })
          current = cls["baseClass"]
          found = true
          break
        }
      }
      if (!found) {
        chain.push({ name: current, baseClass: "(not found in index)", file: "", depth })
        break
      }
    }
    return { className: args.className, chain, complete: chain.length > 0 && chain[chain.length - 1]["baseClass"] === "(not found in index)" }
  },
})

export const vfp_export_table = tool({
  description:
    "Export DBF table schema (fields, types, codepage) and optionally data to JSONL/CSV using pure-Python dbfread — NO VFP9 required.",
  args: {
    input: tool.schema.string().describe("Path to the .dbf file."),
    format: tool.schema.string().optional().describe("Optional data export format: 'jsonl' or 'csv'. If omitted, only schema is exported."),
    deleted: tool.schema.string().optional().describe("Deleted record handling: 'skip' (default), 'separate', or 'include'."),
    out: tool.schema.string().optional().describe("Output directory. Defaults to <project>/.vfp-ai/dbf."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)
    const dir = context.worktree || process.cwd()
    const cacheDir = args.out || join(dir, cfg.cacheDirectory || ".vfp-ai", "dbf")

    const p = Bun.spawn(
      [py, DRIVER, "dbf_schema", "--input", args.input, "--out", cacheDir],
      { stdout: "pipe", stderr: "pipe" }
    )
    const out = await new Response(p.stdout).text()
    const err = await new Response(p.stderr).text()
    const rc = await p.exited
    if (rc !== 0) throw new Error(err || `dbf_schema exit ${rc}`)
    const schemaResult = JSON.parse(out.trim())

    if (args.format) {
      const p2 = Bun.spawn(
        [py, DRIVER, "dbf_data", "--input", args.input, "--out", cacheDir,
         "--format", args.format, "--deleted", args.deleted || "skip"],
        { stdout: "pipe", stderr: "pipe" }
      )
      const out2 = await new Response(p2.stdout).text()
      const err2 = await new Response(p2.stderr).text()
      const rc2 = await p2.exited
      if (rc2 !== 0) throw new Error(err2 || `dbf_data exit ${rc2}`)
      const dataResult = JSON.parse(out2.trim())
      return { schema: schemaResult, data: dataResult }
    }

    return { schema: schemaResult }
  },
})

export const vfp_list_tables = tool({
  description:
    "List all DBF tables in a directory tree with field counts, record counts, and memo presence. Pure Python — NO VFP9 required.",
  args: {
    directory: tool.schema.string().optional().describe("Project root to scan. Defaults to current worktree."),
  },
  async execute(args, context) {
    const dir = args.directory || context.worktree || process.cwd()

    const p = Bun.spawn(
      [py, DRIVER, "dbf_list", "--dir", dir],
      { stdout: "pipe", stderr: "pipe" }
    )
    const out = await new Response(p.stdout).text()
    const err = await new Response(p.stderr).text()
    const rc = await p.exited
    if (rc !== 0) throw new Error(err || `dbf_list exit ${rc}`)
    return JSON.parse(out.trim())
  },
})

export const vfp_export_dir = tool({
  description:
    "Batch-export a WHOLE directory tree of DBF tables (schema + data) in one go using the vendored dbfbridge — NO VFP9 required. Output mirrors the source folder structure. Use this to export many tables without running a full audit.",
  args: {
    source: tool.schema.string().describe("Directory containing the .dbf files (project root or a subfolder)."),
    out: tool.schema.string().optional().describe("Output directory. Defaults to <project>/.vfp-ai/dbf."),
    formats: tool.schema.string().optional().describe("Comma-separated formats: 'jsonl', 'csv', 'json', 'xlsx'. Default: 'jsonl'."),
    deleted: tool.schema.string().optional().describe("Deleted record handling: 'skip', 'separate', or 'include'. Default: 'include'."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)
    const dir = args.source || context.worktree || process.cwd()
    const outDir = args.out || join(context.worktree || process.cwd(), cfg.cacheDirectory || ".vfp-ai", "dbf")

    const cmd = [py, DRIVER, "dbf_dir", "--source", dir, "--out", outDir]
    if (args.formats) cmd.push("--formats", args.formats)
    if (args.deleted) cmd.push("--deleted", args.deleted)

    const p = Bun.spawn(cmd, { stdout: "pipe", stderr: "pipe" })
    const out = await new Response(p.stdout).text()
    const err = await new Response(p.stderr).text()
    const rc = await p.exited
    if (rc !== 0) throw new Error(err || `dbf_dir exit ${rc}`)
    return JSON.parse(out.trim())
  },
})

export const vfp_audit = tool({
  description:
    "Run a comprehensive audit of a VFP project: BIN2PRG sync (if VFP9 available) + DBF schema export + table relationship analysis + class hierarchy analysis + CDX/IDX index structure (tags, sort order, expressions) + form/class code. Outputs a consolidated audit report to a target directory. DBF schema + index structure analysis works WITHOUT VFP9. " +
    "includeForms (default true): export the FULL source of every form/class/method (button Click handlers, PROCEDURE/Function bodies) + PRG scripts to <out>/forms — makes the audit self-contained for form reconstruction without FoxPro. " +
    "includeData (default TRUE): reads the FULL contents of every table (incl. memo/FPT) and writes it to <out>/dbf mirroring the project folder structure. A DEFAULT audit captures EVERYTHING (forms + data + indexes + relationships). Set includeData=false for a fast schema-only audit.",
  args: {
    source: tool.schema.string().describe("Source directory of the VFP project to audit."),
    out: tool.schema.string().describe("Target directory where audit output will be written (schema JSON, forms, data, indexes, relationships, Markdown report)."),
    skipSync: tool.schema.boolean().optional().describe("Skip the automatic BIN2PRG sync. By default the audit runs a sync first if the .vfp-ai cache is missing (class/form analysis needs it)."),
    includeForms: tool.schema.boolean().optional().describe(
      "Export the FULL source of every form/class/method (button Click handlers, PROCEDURE/Function bodies) + PRG scripts to <out>/forms. " +
      "ON BY DEFAULT. Set false to skip (faster, smaller audit)."),
    includeData: tool.schema.boolean().optional().describe(
      "Export the FULL contents of every DBF table (incl. memo/FPT) to <out>/dbf, mirroring the project folder structure. " +
      "ON BY DEFAULT (a default audit captures everything). SLOW and disk-heavy on large projects — " +
      "set false for a fast schema-only audit."),
    dataFormats: tool.schema.string().optional().describe("When includeData=true, comma-separated data formats: 'jsonl', 'csv', 'json', 'xlsx'. Default: 'jsonl'."),
    maxTables: tool.schema.number().optional().describe("With includeData=true, limit export to N largest tables (0 = all). Default 0."),
    dbfExclude: tool.schema.string().optional().describe("Comma-separated uppercase substrings to exclude from the DBF scan (e.g. 'ARCH,TMP'). Default empty."),
    onlyTables: tool.schema.string().optional().describe("Only process DBF tables whose path contains one of these uppercase substrings (comma-separated, e.g. 'ARCH,TMP')."),
    noValidate: tool.schema.boolean().optional().describe("Export DBF data with validate=False (skip the validated pass; use when validate=True fails)."),
    noCacheScan: tool.schema.boolean().optional().describe("Do not scan .vfp-ai/source for table usage."),
  },
  async execute(args, context) {
    const cfg = loadConfig()
    if (!cfg) throw new Error("Cannot read config.json at " + CONFIG)

    const cmd = [py, DRIVER, "audit", "--source", args.source, "--out", args.out]
    if (args.skipSync) cmd.push("--skip-sync")
    if (args.includeForms === false) cmd.push("--no-include-forms")
    if (args.includeData === false) cmd.push("--no-include-data")
    if (args.dataFormats) cmd.push("--data-formats", args.dataFormats)
    if (args.maxTables !== undefined && args.maxTables !== null) cmd.push("--max-tables", String(args.maxTables))
    if (args.dbfExclude) cmd.push("--dbf-exclude", args.dbfExclude)
    if (args.onlyTables) cmd.push("--only-tables", args.onlyTables)
    if (args.noValidate) cmd.push("--no-validate")
    if (args.noCacheScan) cmd.push("--no-cache-scan")

    const p = Bun.spawn(cmd, { stdout: "pipe", stderr: "pipe" })
    const out = await new Response(p.stdout).text()
    const err = await new Response(p.stderr).text()
    const rc = await p.exited
    if (rc !== 0) throw new Error(err || `audit exit ${rc}`)
    return JSON.parse(out.trim())
  },
})

export const vfp_analyze_cdx = tool({
  description:
    "Analyze the index structure of a VFP table (.cdx compound or .idx single-tag index): tag names, sort order, index type, and — when VFP9 is available — the index tag EXPRESSIONS. " +
    "Pure structural parsing works WITHOUT VFP9 (any platform). VFP9 is used best-effort only to read the index expressions. Returns a JSON object with the tag list.",
  args: {
    dbf: tool.schema.string().describe("Path to the .dbf file whose index to analyze."),
    cdx: tool.schema.string().optional().describe("Explicit .cdx/.idx path (default: <dbf stem>.cdx beside the table)."),
  },
  async execute(args, _context) {
    const cmd = [py, DRIVER, "cdx_info", "--dbf", args.dbf]
    if (args.cdx) cmd.push("--cdx", args.cdx)
    const p = Bun.spawn(cmd, { stdout: "pipe", stderr: "pipe" })
    const out = await new Response(p.stdout).text()
    const err = await new Response(p.stderr).text()
    const rc = await p.exited
    if (rc !== 0) throw new Error(err || `cdx_info exit ${rc}`)
    return JSON.parse(out.trim())
  },
})

export const vfp_scan_cdx = tool({
  description:
    "Scan a directory tree for .cdx/.idx index files and structurally parse each one (tag names, sort order, type). Works WITHOUT VFP9. Returns a list of parsed index files.",
  args: {
    directory: tool.schema.string().describe("Project root to scan for .cdx/.idx files."),
  },
  async execute(args, _context) {
    const p = Bun.spawn([py, DRIVER, "cdx_scan", "--dir", args.directory], { stdout: "pipe", stderr: "pipe" })
    const out = await new Response(p.stdout).text()
    const err = await new Response(p.stderr).text()
    const rc = await p.exited
    if (rc !== 0) throw new Error(err || `cdx_scan exit ${rc}`)
    return JSON.parse(out.trim())
  },
})
