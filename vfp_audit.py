#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_audit.py - Comprehensive VFP project audit.

Runs a full analysis of a VFP project directory and consolidates results
into a target output directory. Generates:

  1. project_summary.json  — file inventory, class/method counts, index stats
  2. database_schema.json  — all DBF table schemas with encodings + record counts
  3. table_relationships.json — inferred table usage (USE/SELECT/INSERT/REPLACE)
  4. class_analysis.json  — class hierarchy, method counts, inheritance chains
  5. audit_report.md       — human-readable summary

DBF schema/data analysis uses the vendored dbfbridge (tools/dbfbridge) or
the dbfread fallback — NO VFP9 required.

Usage:
    py vfp_audit.py --source <project_root> --out <audit_output_dir>
                    [--skip-sync] [--include-data]
                    [--data-formats jsonl,csv] [--max-tables 0]
                    [--dbf-exclude pattern1,pattern2]

Output protocol: one JSON object on stdout:
    {"ok": bool, "rc": int|null, "auditDir": str, "summary": {...}, "stderr": str}
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vfp_common

__version__ = "0.2.0"


def _emit(ok, **kw):
    """Emit a single JSON object on stdout and exit (0 ok / 2 not ok)."""
    payload = {
        "ok": bool(ok),
        "rc": None,
        "auditDir": None,
        "summary": {},
        "stderr": "",
    }
    payload.update(kw)
    print(json.dumps(payload, ensure_ascii=True))
    sys.exit(0 if ok else 2)


class VFPProjectAuditor:
    """Orchestrates a full VFP project audit."""

    EXCLUDE_DIRS = tuple(vfp_common.default_excludes())

    def __init__(self, source_dir, out_dir, skip_sync=False,
                 include_data=False, data_formats=("jsonl",),
                 max_tables=0, dbf_exclude=(), scan_cache=True,
                 include_forms=True, no_validate=False, only_tables=()):
        self.source = os.path.abspath(source_dir)
        self.out = os.path.abspath(out_dir)
        self.skip_sync = skip_sync
        self.include_data = include_data
        self.data_formats = data_formats
        self.max_tables = max_tables  # 0 = all tables
        self.dbf_exclude = [p.strip().upper() for p in dbf_exclude if p.strip()]
        self.no_validate = no_validate  # export with validate=False (dbfbridge)
        self.only_tables = [p.strip().upper() for p in only_tables if p.strip()]
        self.scan_cache = scan_cache
        self.include_forms = include_forms
        self.cache_dir = os.path.join(self.source, ".vfp-ai")
        self.dbf_dir = os.path.join(self.out, "dbf")
        # Data export (all table contents) lands in the audit's "dbf" subdirectory,
        # mirroring the original project's folder structure.
        self.data_dir = self.dbf_dir
        # Full form/class source (converted .sc2/.vc2/.fr2 + real .prg/.h) lands
        # in the audit's "forms" subdirectory so the audit is self-contained.
        self.forms_dir = os.path.join(self.out, "forms")
        self.warnings = []
        self.errors = []
        self.data_export = {
            "requested": False,
            "performed": False,
            "targetDir": None,
            "tables": 0,
            "formats": [],
            "note": "",
        }
        self.forms_export = {
            "requested": False,
            "performed": False,
            "targetDir": None,
            "sourceFiles": 0,
            "bytes": 0,
            "byType": {},
            "note": "",
        }

    # ------------------------------------------------------------------ utils

    def _walk_dbf_files(self):
        """List DBF files in the source project (excluding cache dirs)."""
        files = []
        for root, dirs, files_ in os.walk(self.source):
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d.lower() not in self.EXCLUDE_DIRS]
            for fn in files_:
                if os.path.splitext(fn)[1].lower() == ".dbf":
                    fp = os.path.join(root, fn)
                    rel = os.path.relpath(fp, self.source).upper()
                    if any(pat in rel for pat in self.dbf_exclude):
                        continue
                    if self.only_tables:
                        if not any(t in rel for t in self.only_tables):
                            continue
                    files.append(fp)
        return files

    # ------------------------------------------------------- cache (BIN2PRG)

    def _cache_is_usable(self):
        """True if .vfp-ai has a symbol index or converted text sources."""
        if os.path.isfile(os.path.join(self.cache_dir, "index.json")):
            return True
        src = os.path.join(self.cache_dir, "source")
        if os.path.isdir(src):
            for _, _, files in os.walk(src):
                for fn in files:
                    if fn.lower().endswith((".sc2", ".vc2", ".fr2")):
                        return True
        return False

    def _ensure_cache(self):
        """Run a BIN2PRG sync + index if the .vfp-ai cache is missing.

        Delegates to vfp_driver.py (VFP9 COM via cscript). Any failure is
        non-fatal: the audit continues with DBF-only analysis and a warning is
        recorded (class/form analysis will be incomplete).
        """
        if self._cache_is_usable():
            return

        here = os.path.dirname(os.path.abspath(__file__))
        driver = os.path.join(here, "vfp_driver.py")
        if not os.path.isfile(driver):
            self.warnings.append(
                "No .vfp-ai cache and vfp_driver.py not found — "
                "class/form analysis will be unavailable")
            return

        prg = vfp_common.foxbin2prg_program()
        if not os.path.isfile(prg):
            self.warnings.append(
                "BIN2PRG sync skipped: foxbin2prg.prg not found at %s "
                "(set VFP_FOXBIN2PRG_DIR). Class/form analysis will be incomplete." % prg)
            return

        # Report missing companion files up front (real-run report #1/#6:
        # FoxBin2Prg fails with rc=41 + empty stderr when a companion such as
        # .sct/.fpt/.pjt is absent — previously indistinguishable from a
        # missing VFP9 install).
        missing_by_file = {}
        for root, dirs, files_ in os.walk(self.source):
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d.lower() not in self.EXCLUDE_DIRS]
            for fn in files_:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in vfp_common.COMPANIONS:
                    continue
                fp = os.path.join(root, fn)
                miss = vfp_common.missing_companions(fp)
                if miss:
                    missing_by_file[os.path.relpath(fp, self.source)] = miss
        if missing_by_file:
            listing = "; ".join("%s -> missing %s" % (f, ", ".join(os.path.basename(m) for m in ms))
                                for f, ms in list(missing_by_file.items())[:10])
            self.warnings.append(
                "BIN2PRG will report 'Error 41' for these files (missing companion file); "
                "copy the companion (.sct/.fpt/.pjt/.frt/.vct) next to the binary: %s"
                % (listing if len(missing_by_file) <= 10 else listing + " ..."))

        py = sys.executable or "python"
        cmds = [
            [py, driver, "convert_dir", "--project", self.source,
             "--out", os.path.join(self.cache_dir, "source"),
             "--cfg", os.path.join(here, "FoxBin2Prg-AI.cfg"),
             "--prg", prg],
            [py, driver, "index", "--project", os.path.join(self.cache_dir, "source"),
             "--cache", self.cache_dir],
        ]
        for cmd in cmds:
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                outb, errb = p.communicate(timeout=3600)
                rc = p.returncode
            except Exception as e:
                self.warnings.append("BIN2PRG sync failed: %s" % e)
                return
            if rc != 0:
                err = (errb or b"").decode("utf-8", "replace")[:300]
                detail = "see vfp_driver output"
                if cmd[1].endswith("convert_dir"):
                    # vfp_driver emits JSON with per-file rc/stderr — surface the
                    # real causes (rc=41 missing companion, VFP9 COM errors, ...)
                    try:
                        payload = json.loads((outb or b"").decode("utf-8", "replace"))
                        bad = [r for r in payload.get("data", {}).get("results", []) if not r.get("ok")]
                        if bad:
                            detail = "; ".join(
                                "%s rc=%s %s" % (r.get("file"), r.get("rc"), r.get("stderr", "").strip()[:120])
                                for r in bad[:5])
                    except Exception:
                        pass
                hint = "If VFP9 (Visual FoxPro 9) is not installed, install it or use --skip-sync."
                self.warnings.append(
                    "BIN2PRG sync failed (rc=%s): %s. %s" % (rc, detail or err or "unknown error", hint))
                return

    def _disk_table_set(self, dbf_schemas):
        """Set of uppercased table names that exist on disk (basename stem)."""
        names = set()
        for s in dbf_schemas:
            t = (s.get("table") or "").upper()
            if t:
                names.add(t)
            src = os.path.basename(s.get("sourceFile") or "")
            if src:
                names.add(os.path.splitext(src)[0].upper())
        return names

    # Path fragments that strongly suggest an archive / temporary / backup copy
    ARCHIVE_HINTS = (
        "ARCH", "AR_", "TMP", "BAK", "BACKUP", "KOPIA", "_SIM", "DANE_SIM",
        "BAZA_TMP", "EKS_", "OLD", "_KOPYA", "KOP",
    )

    def _path_is_archive_like(self, rel_path):
        """True if a relative path looks like an archive/temp/backup copy."""
        """True if a relative path looks like an archive/temp/backup copy."""
        up = (rel_path or "").upper()
        return any(h in up for h in self.ARCHIVE_HINTS)

    def _detect_duplicate_copies(self, dbf_schemas):
        """Find DBF tables that exist as multiple files (same name, different dirs).

        These are almost always user backups / temp copies. We flag them so the
        data can be de-duplicated before reconstruction. Returns a dict:
            {
              totalDbfFiles, uniqueNames, duplicateNameCount, redundantCopies,
              duplicates: [ {table, copies, primary,
                             suspectedBackups:[{file, records, sizeMB, archiveLike}]} ]
            }
        """
        by_name = {}
        for s in dbf_schemas:
            key = os.path.splitext(os.path.basename(s.get("sourceFile") or ""))[0].upper()
            if not key:
                continue
            rel = s.get("sourceFile") or ""
            fp = os.path.join(self.source, rel) if rel else None
            size_mb = self._table_size_mb(fp) if fp else 0
            by_name.setdefault(key, []).append({
                "file": rel,
                "records": s.get("recordCount", 0),
                "sizeMB": round(size_mb, 2),
                "archiveLike": self._path_is_archive_like(rel),
            })

        duplicates = []
        redundant = 0
        for name in sorted(by_name):
            files = by_name[name]
            if len(files) < 2:
                continue
            # Primary = an archive-like-free copy if one exists, else the largest.
            non_arch = [f for f in files if not f["archiveLike"]]
            pool = non_arch or files
            pool.sort(key=lambda f: (-(f["records"] or 0), -(f["sizeMB"] or 0)))
            primary = pool[0]["file"]
            copies = [f for f in sorted(files, key=lambda f: f["file"]) if f["file"] != primary]
            redundant += len(copies)
            duplicates.append({
                "table": name,
                "copies": len(files),
                "primary": primary,
                "suspectedBackups": copies,
            })

        return {
            "totalDbfFiles": len(dbf_schemas),
            "uniqueNames": len(by_name),
            "duplicateNameCount": len(duplicates),
            "redundantCopies": redundant,
            "duplicates": duplicates,
        }

    def _table_size_mb(self, dbf_path):
        """Approximate on-disk size (MB) of a table incl. its .fpt memo file."""
        """Approximate on-disk size (MB) of a table incl. its .fpt memo file."""
        size = 0
        try:
            size += os.path.getsize(dbf_path)
            fpt = dbf_path[:-4] + ".fpt"
            if os.path.isfile(fpt):
                size += os.path.getsize(fpt)
        except OSError:
            pass
        return size / (1024.0 * 1024.0)

    # ------------------------------------------------------------------- run

    def run(self):
        """Run the full audit and generate all output files."""
        os.makedirs(self.out, exist_ok=True)
        os.makedirs(self.dbf_dir, exist_ok=True)

        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import vfp_dbf_export as dbf_exp

        # 0. Ensure the BIN2PRG text cache exists (class/form analysis + form
        #    code export depend on it). Skipped with --skip-sync, or when a
        #    usable cache already exists.
        if not self.skip_sync:
            self._ensure_cache()

        dbf_files = self._walk_dbf_files()

        # 1. DBF schema export (batch via dbfbridge when available)
        dbf_schemas = self._export_dbf_schemas(dbf_exp, dbf_files)

        # 2. DBF data export (OPTIONAL — reads ALL table contents; can be large/slow)
        if self.include_data:
            self._export_dbf_data(dbf_exp, dbf_files)
            self.data_export["note"] = (
                "FULL DBF DATA EXPORT — every table's contents (incl. memo/FPT) read "
                "and written to the dbf subdirectory. This was the most time-consuming step."
            )

        # 3. Project summary from index.json + file inventory
        project_summary = self._build_project_summary()

        # 4. Class analysis from index.json
        class_analysis = self._build_class_analysis()

        # 5. Table relationships (USE/SELECT/INSERT/REPLACE in code)
        disk_tables = self._disk_table_set(dbf_schemas)
        table_relationships = self._find_table_relationships(disk_tables)

        # 6. Cross-reference: tables in DBF vs tables referenced in code
        cross_ref = self._cross_reference(dbf_schemas, table_relationships)

        # 6a. Detect redundant DBF copies (same table name in multiple folders —
        #     almost always user backups / temp copies) so the data can be
        #     de-duplicated before reconstruction.
        duplicate_tables = self._detect_duplicate_copies(dbf_schemas)

        # 6b. Optional: full form/class/method source export (self-contained)
        if self.include_forms:
            self._export_forms()

        # 7. Generate database schema document
        database_schema = self._build_database_schema(dbf_schemas)

        # 8. Write audit report + JSON artifacts
        self._write_outputs(project_summary, database_schema,
                            table_relationships, class_analysis, cross_ref,
                            duplicate_tables)

        return {
            "ok": True,
            "auditDir": self.out,
            "dataExport": self.data_export,
            "formsExport": self.forms_export,
            "summary": {
                "projectSummary": {
                    "tables": database_schema["tableCount"],
                    "classes": class_analysis.get("totalClasses", 0),
                    "methods": class_analysis.get("totalMethods", 0),
                    "codeTables": table_relationships.get("tableCount", 0),
                    "unresolvedTables": len(cross_ref.get("inCodeNotOnDisk", [])),
                    "duplicateTableNames": duplicate_tables.get("duplicateNameCount", 0),
                    "redundantDbfCopies": duplicate_tables.get("redundantCopies", 0),
                    "dataExportRequested": self.data_export["requested"],
                    "dataExportPerfomed": self.data_export["performed"],
                    "dataExportTables": self.data_export["tables"],
                    "dataExportDir": self.data_export["targetDir"],
                    "formsExportRequested": self.forms_export["requested"],
                    "formsExportPerfomed": self.forms_export["performed"],
                    "formsExportFiles": self.forms_export["sourceFiles"],
                    "formsExportDir": self.forms_export["targetDir"],
                    "warnings": len(self.warnings),
                },
                "warnings": self.warnings,
                "errors": self.errors,
            },
        }

    # ------------------------------------------------------------- DBF schema

    def _export_dbf_schemas(self, dbf_exp, dbf_files):
        """Extract schemas for all DBF files (metadata-only, no data dump).

        Uses dbf_exp.scan_dbf (header + field descriptors only) which is fast
        and does NOT write record data — appropriate for a project with many
        large tables.
        """
        if not dbf_files:
            return []

        schemas = []
        for dbf in dbf_files:
            try:
                schema = dbf_exp.scan_dbf(dbf)
            except Exception as e:
                self.warnings.append("schema failed for %s: %s" % (os.path.basename(dbf), e))
                continue
            if not schema or "error" in schema:
                self.warnings.append("schema failed for %s: %s"
                                    % (os.path.basename(dbf), schema.get("error") if schema else "no reader"))
                continue
            fields = schema.get("fields", [])
            schemas.append({
                "table": schema.get("table"),
                "sourceFile": os.path.relpath(dbf, self.source),
                "recordCount": schema.get("recordCount", 0),
                "fieldCount": schema.get("fieldCount", 0),
                "hasMemo": schema.get("hasMemo", False),
                "memoFields": schema.get("memoFields"),
                "codePage": schema.get("codePage"),
                "reader": schema.get("reader", "fallback"),
                "fields": [
                    {
                        "name": f.get("name"),
                        "type": f.get("type"),
                        "typeName": f.get("typeName"),
                        "length": f.get("length"),
                        "decimal": f.get("decimal", 0) or 0,
                        "position": f.get("position"),
                        "isMemo": bool(f.get("isMemo")),
                    }
                    for f in fields
                ],
            })

        return sorted(schemas, key=lambda x: (x.get("table") or "", x.get("sourceFile") or ""))

    # ------------------------------------------------------------- DBF data

    def _data_export_complete(self, dbf_files, fmts):
        """True if every table already has a non-empty data file in the audit dir.

        Real-run report #4: a second audit re-exported ALL tables (incl. a 2.7M-row,
        1.6GB table) even though a previous run had already produced them. Checking
        for existing output first makes the data export idempotent/resumable.
        """
        for dbf in dbf_files:
            rel = os.path.relpath(os.path.dirname(dbf), self.source)
            base = os.path.splitext(os.path.basename(dbf))[0]
            relseg = [] if rel in (".", "") else [rel]
            for fmt in fmts:
                # per-table layout: <data>/<fmt>/<rel>/<base>.<fmt>
                # full-tree dbfbridge layout: <data>/<rel>/<base>.<fmt>
                candidates = [
                    os.path.join(self.data_dir, fmt, *relseg, base + "." + fmt),
                    os.path.join(self.data_dir, *relseg, base + "." + fmt),
                ]
                if not any(os.path.isfile(c) and os.path.getsize(c) > 0 for c in candidates):
                    return False
        return True

    def _export_dbf_data(self, dbf_exp, dbf_files):
        """Export DBF data (bounded by --max-tables: largest tables first).

        Output goes to <audit>/dbf, mirroring the original project's
        folder structure (each table keeps its subdirectory, plus its
        _schema.json and memo content).
        """
        if not dbf_files:
            return

        self.data_export["requested"] = True
        self.data_export["targetDir"] = self.data_dir

        valid = [f for f in self.data_formats if f in ("jsonl", "csv", "json", "xlsx")] or ["jsonl"]
        self.data_export["formats"] = valid
        os.makedirs(self.data_dir, exist_ok=True)

        # Idempotency (real-run report #4): if all tables already have complete
        # data output from a previous run, skip the (expensive) re-export.
        if self._data_export_complete(dbf_files, valid):
            self.data_export["tables"] = len(dbf_files)
            self.data_export["performed"] = True
            self.data_export["skipped"] = "data files already present (idempotent skip)"
            self.warnings.append("data export skipped: %d tables already fully exported" % len(dbf_files))
            return

        has_bridge = dbf_exp._has_dbfbridge()

        if has_bridge and self.max_tables <= 0:
            # Full tree export — dbfbridge preserves the source folder structure,
            # so all JSONL (+ schema) files land under <audit>/dbf/<same tree>.
            self.data_export["tables"] = len(dbf_files)
            try:
                run, warnings = dbf_exp._dbfbridge_export_dir(
                    self.source, self.data_dir, tuple(valid), "include",
                    validate=not self.no_validate)
                for w in warnings:
                    self.warnings.append(w)
                failed = [t for t in run.results if getattr(t, "status", "") == "FAILED"]
                if failed:
                    self.warnings.append("%d table/format output(s) failed data export" % len(failed))
                self.data_export["performed"] = not failed
                return
            except Exception as e:
                self.warnings.append("dbfbridge data export failed: %s" % e)

        # Per-table export: used when limiting tables (--max-tables) or as fallback.
        # Output mirrors the original project folder structure under <audit>/dbf.
        if self.max_tables > 0:
            sized = sorted(dbf_files, key=self._table_size_mb, reverse=True)
            dbf_files = sized[:self.max_tables]
            self.warnings.append("data export limited to %d largest tables (by size)" % self.max_tables)
        self.data_export["tables"] = len(dbf_files)

        exported = 0
        for fmt in valid:
            fmt_dir = os.path.join(self.data_dir, fmt)
            os.makedirs(fmt_dir, exist_ok=True)
            for dbf in dbf_files:
                rel = os.path.relpath(os.path.dirname(dbf), self.source)
                tdir = os.path.join(fmt_dir, rel) if rel not in (".", "") else fmt_dir
                os.makedirs(tdir, exist_ok=True)
                try:
                    count, data_file, warnings = dbf_exp.export_data(dbf, tdir, fmt, "include",
                                                                     validate=not self.no_validate)
                    if data_file:
                        exported += 1
                    if warnings:
                        self.warnings.append("data %s: %s" % (os.path.basename(dbf), warnings))
                except Exception as e:
                    self.warnings.append("data failed for %s: %s" % (os.path.basename(dbf), e))
        self.data_export["performed"] = exported > 0

    # ------------------------------------------------------- forms / class code

    # Converted (BIN2PRG) text sources that hold the full form/class/method code.
    FORM_SOURCE_EXTS = (".sc2", ".vc2", ".fr2", ".pj2", ".mn2", ".lb2")
    # Real script sources in the project root that are already plain text.
    SCRIPT_EXTS = (".prg", ".h")

    def _export_forms(self):
        """Copy the full form/class/method source into <audit>/forms.

        Two source pools are merged (deduplicated by relative path):
          * .vfp-ai/source  — BIN2PRG-converted .sc2/.vc2/.fr2/.pj2 … (the real
            bodies of every form, class and method — including button `Click=`
            handlers and PROCEDURE/Function bodies).
          * the project root — genuine .prg/.h scripts (already plain text).

        The result is a self-contained snapshot so that form/class behaviour can
        be reconstructed WITHOUT the original binary .scx/.vcx/.frx files and
        without FoxBin2Prg or VFP9.
        """
        self.forms_export["requested"] = True
        self.forms_export["targetDir"] = self.forms_dir
        os.makedirs(self.forms_dir, exist_ok=True)

        seen = set()
        copied = 0
        total_bytes = 0
        by_type = {}

        def _copy_one(abs_src, rel, ext):
            """Copy one source file into the forms dir, tracking stats."""
            nonlocal copied, total_bytes
            dest = os.path.join(self.forms_dir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if not os.path.isfile(dest):
                shutil.copyfile(abs_src, dest)
            copied += 1
            total_bytes += os.path.getsize(abs_src)
            by_type[ext] = by_type.get(ext, 0) + 1

        # Pool 1: converted BIN2PRG sources from the cache (primary, most complete)
        cache_source = os.path.join(self.cache_dir, "source")
        if os.path.isdir(cache_source):
            for root, dirs, files in os.walk(cache_source):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for fn in files:
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in self.FORM_SOURCE_EXTS:
                        abs_src = os.path.join(root, fn)
                        rel = os.path.relpath(abs_src, cache_source)
                        key = rel.lower()
                        if key in seen:
                            continue
                        seen.add(key)
                        try:
                            _copy_one(abs_src, rel, ext)
                        except Exception as e:
                            self.warnings.append("forms copy failed %s: %s" % (rel, e))
        else:
            self.warnings.append("No .vfp-ai/source — run BIN2PRG sync first for full form code")

        # Pool 2: genuine .prg/.h scripts in the project (skip any already covered)
        for root, dirs, files in os.walk(self.source):
            dirs[:] = [d for d in dirs
                       if not d.startswith(".") and d.lower() not in self.EXCLUDE_DIRS]
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in self.SCRIPT_EXTS:
                    continue
                abs_src = os.path.join(root, fn)
                rel = os.path.relpath(abs_src, self.source)
                key = rel.lower()
                if key in seen:
                    continue
                seen.add(key)
                try:
                    _copy_one(abs_src, rel, ext)
                except Exception as e:
                    self.warnings.append("forms copy failed %s: %s" % (rel, e))

        self.forms_export["sourceFiles"] = copied
        self.forms_export["bytes"] = total_bytes
        self.forms_export["byType"] = dict(sorted(by_type.items()))
        self.forms_export["performed"] = copied > 0
        if copied == 0:
            self.forms_export["note"] = (
                "No form/class source found. Run a BIN2PRG sync (vfp sync) first so the "
                "converted .sc2/.vc2/.fr2 files exist in .vfp-ai/source.")
        else:
            self.forms_export["note"] = (
                "FULL FORM/CLASS SOURCE EXPORT — every form, class and method body "
                "(incl. button Click handlers and PROCEDURE/Function code) copied from the "
                "BIN2PRG-converted .sc2/.vc2/.fr2 text and the project's .prg/.h scripts. "
                "This snapshot is self-contained: no .scx/.vcx/.frx or FoxPro needed to read it.")
        return self.forms_export

    # ------------------------------------------------------- project summary

    def _build_project_summary(self):
        """Build summary from index.json and file inventory."""
        summary = {
            "projectRoot": self.source,
            "auditDate": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "fileInventory": self._build_file_inventory(),
        }

        idx_path = os.path.join(self.cache_dir, "index.json")
        if os.path.isfile(idx_path):
            try:
                with open(idx_path, "r", encoding="utf-8") as f:
                    idx = json.load(f)
                summary["index"] = {
                    "scannedAt": idx.get("scannedAt"),
                    "fileCount": len(idx.get("files", [])),
                    "classCount": len(idx.get("classes", [])),
                    "methodCount": len(idx.get("methods", [])),
                    "symbolCount": len(idx.get("symbols", [])),
                }
            except Exception as e:
                self.warnings.append("Could not read index.json: %s" % e)
        else:
            self.warnings.append("No .vfp-ai/index.json — run BIN2PRG sync first for full class analysis")

        return summary

    def _build_file_inventory(self):
        """Walk the project and inventory VFP files."""
        exts = [".scx", ".vcx", ".frx", ".mnx", ".lbx", ".pjx", ".dbc",
                ".dbf", ".fpt", ".cdx", ".prg", ".h", ".pjt",
                ".sct", ".vct", ".frt", ".mnt", ".lb2", ".dct", ".dcx",
                ".qpx", ".fll", ".app", ".ico", ".bmp"]
        counts = {}
        for root, dirs, files in os.walk(self.source):
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d.lower() not in self.EXCLUDE_DIRS]
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext in exts:
                    counts[ext] = counts.get(ext, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    # --------------------------------------------------------- class analysis

    def _build_class_analysis(self):
        """Build class analysis from index.json."""
        idx_path = os.path.join(self.cache_dir, "index.json")
        if not os.path.isfile(idx_path):
            return {"error": "index.json not found — run BIN2PRG sync first"}

        with open(idx_path, "r", encoding="utf-8") as f:
            idx = json.load(f)

        classes = idx.get("classes", [])
        methods = idx.get("methods", [])
        files = idx.get("files", {})

        # Per-class method counts. The flat index["methods"] may carry an empty
        # "class" (older indexers), so we rebuild the mapping from each file's
        # embedded class symbols when available.
        methods_by_class = {}
        flat_has_class = any((m.get("class") or "").strip() for m in methods[:50])
        if flat_has_class:
            for m in methods:
                cn = (m.get("class") or "").upper()
                if cn:
                    methods_by_class.setdefault(cn, []).append(m)
        else:
            for entry in files.values():
                syms = entry.get("symbols") or {}
                for cls in syms.get("classes", []):
                    cn = (cls.get("name") or "").upper()
                    if cn:
                        methods_by_class.setdefault(cn, []).extend(cls.get("methods", []))

        class_map = {}
        for c in classes:
            class_map.setdefault(c["name"].upper(), c)

        # Complexity: classes ranked by method count
        class_complexity = []
        for cu, c in class_map.items():
            mn = len(methods_by_class.get(cu, []))
            class_complexity.append({
                "name": c["name"],
                "baseClass": c.get("baseClass"),
                "file": c.get("file"),
                "methodCount": mn,
            })
        class_complexity.sort(key=lambda x: -x["methodCount"])

        # Inheritance chains
        inheritance_chains = {}
        for cu, c in class_map.items():
            chain = [c["name"]]
            visited = {cu}
            base = (c.get("baseClass") or "").upper()
            while base and base not in visited and len(chain) < 25:
                chain.append(base)
                visited.add(base)
                nxt = class_map.get(base)
                base = (nxt.get("baseClass") or "").upper() if nxt else ""
            inheritance_chains[c["name"]] = {
                "chain": chain,
                "depth": len(chain) - 1,
                "root": chain[-1],
            }

        # Classes with no methods (likely base/interface)
        no_methods = [x["name"] for x in class_complexity if x["methodCount"] == 0]

        return {
            "totalClasses": len(classes),
            "totalMethods": len(methods),
            "classesWithMethods": sum(1 for x in class_complexity if x["methodCount"] > 0),
            "classesWithoutMethods": len(no_methods),
            "topComplexClasses": class_complexity[:30],
            "largestInheritance": sorted(
                inheritance_chains.items(), key=lambda kv: -kv[1]["depth"])[:20],
            "classNames": sorted(c["name"] for c in classes),
        }

    # ---------------------------------------------------- table relationships

    def _find_table_relationships(self, disk_tables=None):
        """Find USE/SELECT/INSERT/REPLACE patterns in code.

        Scans the .vfp-ai/source cache (SC2/VC2/FR2/PJ2/DC2) and the source
        project's .prg/.h files.

        disk_tables: optional set of table names that exist on disk. When
        provided, binding-style references (DBF_REF, ALIAS, RECORDSOURCE) are
        only counted when they match a real table — otherwise many false
        positives (local cursors, variable names, etc.) accumulate.
        """
        disk_tables = disk_tables or set()

        relationships = {
            "uses": {},
            "sqlStatements": [],
            "tableReferences": {},
            "potentialJoins": [],
        }

        scan_dirs = []
        cache_source = os.path.join(self.cache_dir, "source")
        if self.scan_cache and os.path.isdir(cache_source):
            scan_dirs.append(cache_source)
        scan_dirs.append(self.source)

        use_re = re.compile(r'\bUSE\s+["\']?([A-Za-z_]\w*)["\']?', re.IGNORECASE)
        select_re = re.compile(
            r'\bSELECT\s+(?:[\w\*\.\, \[\]\(\)"\']+\s+FROM\s+)?["\']?([A-Za-z_]\w*)["\']?\s+FROM\s+(["\']?)(\w+)(\3)',
            re.IGNORECASE)
        select_multi_re = re.compile(
            r'\bSELECT\s+[\w\.\*\, \[\]\(\)"\']+\s+FROM\s+(["\']?)([A-Za-z_]\w*)(\1)', re.IGNORECASE)
        select_all_re = re.compile(r'\bSELECT\s+\*\s+FROM\s+(["\']?)(\w+)(\2)', re.IGNORECASE)
        select_join_re = re.compile(
            r'\bFROM\s+((?:["\']?[A-Za-z_]\w*["\']?(?:\s+\w+)?(?:\s*,\s*["\']?\w+["\']?(?:\s+\w+)?)+))',
            re.IGNORECASE)
        replace_re = re.compile(r'\bREPLACE\s+(\*|[A-Za-z_]\w+)\s+(?:\sin\b|\sIN\b|WITH\s+IIF)', re.IGNORECASE)
        insert_re = re.compile(r'\bINSERT\s+INTO\s+([A-Za-z_]\w*)', re.IGNORECASE)
        cursor_re = re.compile(r'\bCURSORGETITEM\s*\(\s*\d+\s*,\s*["\']?(\w+)["\']?', re.IGNORECASE)
        # Form / cursor bindings (in .sct/.vct/.frt text forms and .sc2/.vc2)
        dbf_ref_re = re.compile(r'["\']?([\w][\w\.\\/-]*)\.dbf["\']?', re.IGNORECASE)
        alias_re = re.compile(r'\bAlias\s*=\s*["\']?(\w+)["\']?', re.IGNORECASE)
        recordsrc_re = re.compile(r'\bRecordSource\s*=\s*["\'](\w+)["\']', re.IGNORECASE)

        KEYWORDS = {
            "SELECT", "FROM", "WHERE", "INTO", "AS", "ON", "ALL", "DISTINCT",
            "TOP", "AND", "OR", "NOT", "NULL", "IN", "LIKE", "IS", "BETWEEN",
            "ORDER", "GROUP", "BY", "HAVING", "WITH", "VALUES", "SET",
            "IF", "THEN", "ELSE", "ENDIF", "DO", "LOOP", "WHILE", "CASE",
            "WHEN", "CONTINUE", "EXIT", "BREAK", "LOCAL", "GLOBAL", "SKIP",
            "PROCEDURE", "FUNCTION", "RETURN", "DEFINE", "CLASS", "PUBLIC",
            "PROTECTED", "PRIVATE", "PARAMETERS", "LOCALS", "METHOD", "EVENT",
            "ENDDEFINE", "ENDPROC", "ENDFUNC", "THIS", "THISFORM", "OBJECT",
            "CURSOR", "TABLE", "INDEX", "FIELD", "TYPE", "STRUCTURE", "EXTEND",
            "STORE", "READ", "CLEAR", "CREATE", "DROP", "ONLY", "CLOSE",
            "END", "WAIT", "INPUT", "DEFAULT", "ASC", "DESC", "UNION",
            "EXISTS", "CAST", "CONVERT", "SUBSTR", "LEFT", "RIGHT", "LEN",
            "RECORD", "ALIAS", "BLANK", "DELETED", "APPEND", "DELETE",
        }

        all_tables = set()
        files_scanned = 0

        def _add_table(tbl, where_file, line_no, kind, file_tables):
            """Register a table reference (dedup, filter SQL keywords)."""
            tbl = (tbl or "").strip().upper()
            if not tbl or tbl in KEYWORDS or len(tbl) < 2:
                return
            # Binding-style references (DBF path, Alias, RecordSource) are noisy
            # (local cursors, variables, field names) — validate them against the
            # real on-disk table set when available. Explicit SQL (USE/SELECT/
            # INSERT) is kept unvalidated.
            bind_kinds = {"DBF_REF", "ALIAS", "RECORDSOURCE"}
            if kind in bind_kinds and disk_tables and tbl not in disk_tables:
                return
            all_tables.add(tbl)
            file_tables.add(tbl)
            relationships["tableReferences"].setdefault(tbl, []).append({
                "file": where_file, "line": line_no, "type": kind,
            })

        for base in scan_dirs:
            for root, dirs, files in os.walk(base):
                dirs[:] = [d for d in dirs if not d.startswith(".")
                           and d.lower() not in self.EXCLUDE_DIRS
                           and d.lower() != "dbf"]
                for fn in files:
                    ext = os.path.splitext(fn)[1].lower()
                    if ext not in (".sc2", ".vc2", ".fr2", ".prg", ".h",
                                  ".pj2", ".dc2", ".mn2", ".lb2",
                                  ".sct", ".vct", ".frt"):
                        continue
                    fp = os.path.join(root, fn)
                    try:
                        with open(fp, "r", encoding="cp1252", errors="replace") as f:
                            content = f.read()
                    except OSError:
                        continue
                    files_scanned += 1

                    rel_path = os.path.relpath(fp, base)
                    tables_in_file = set()

                    # Form / cursor bindings: any <table>.dbf path reference
                    for m in dbf_ref_re.finditer(content):
                        tbl = m.group(1)
                        name = tbl.replace("\\", "/").split("/")[-1]
                        if name and name.upper() not in KEYWORDS and "." not in name:
                            _add_table(name, rel_path, None, "DBF_REF", tables_in_file)

                    for m in alias_re.finditer(content):
                        if (m.group(1) or "").upper() not in KEYWORDS:
                            _add_table(m.group(1), rel_path, None, "ALIAS", tables_in_file)

                    for m in recordsrc_re.finditer(content):
                        _add_table(m.group(1), rel_path, None, "RECORDSOURCE", tables_in_file)

                    for m in use_re.finditer(content):
                        if (m.group(1) or "").upper() not in KEYWORDS:
                            _add_table(m.group(1), rel_path, None, "USE", tables_in_file)

                    for line_no, line in enumerate(content.splitlines(), 1):
                        m = select_re.search(line) or select_all_re.search(line) \
                            or select_multi_re.search(line)
                        if m:
                            groups = m.groups()
                            tbl = groups[2] if m.re is select_re else groups[1]
                            _add_table(tbl, rel_path, line_no, "SELECT", tables_in_file)
                            relationships["sqlStatements"].append({
                                "file": rel_path, "line": line_no, "type": "SELECT",
                                "table": (tbl or "").upper(), "raw": line.strip()[:200],
                            })

                        for jm in select_join_re.finditer(line):
                            for part in jm.group(1).split(","):
                                pm = re.match(r'\s*["\']?(\w+)', part)
                                if pm:
                                    _add_table(pm.group(1), rel_path, line_no, "FROM", tables_in_file)

                        m = insert_re.search(line)
                        if m:
                            _add_table(m.group(1), rel_path, line_no, "INSERT", tables_in_file)

                        # REPLACE <field> WITH ... IN <table>
                        m = replace_re.search(line)
                        if m and m.group(1) != "*":
                            # Only the IN clause names a table; the field name is not a table
                            inm = re.search(r'\bIN\s+["\']?([A-Za-z_]\w*)["\']?', line, re.IGNORECASE)
                            if inm:
                                _add_table(inm.group(1), rel_path, line_no, "REPLACE", tables_in_file)

                        for m in cursor_re.finditer(line):
                            _add_table(m.group(1), rel_path, line_no, "CURSOR", tables_in_file)

                    if len(tables_in_file) > 1:
                        ts = sorted(tables_in_file)
                        for i, t1 in enumerate(ts):
                            for t2 in ts[i + 1:]:
                                relationships["potentialJoins"].append({
                                    "table1": t1, "table2": t2,
                                    "file": rel_path, "type": "co-occur",
                                })

        # Deduplicate potential joins (same pair+file from cache and source)
        seen = set()
        dedup = []
        for j in relationships["potentialJoins"]:
            key = (j["table1"], j["table2"], j["file"])
            if key in seen:
                continue
            seen.add(key)
            dedup.append(j)
        relationships["potentialJoins"] = dedup

        # Rank joins by frequency across files
        join_rank = {}
        for j in dedup:
            k = (j["table1"], j["table2"])
            join_rank[k] = join_rank.get(k, 0) + 1
        top_joins = sorted(join_rank.items(), key=lambda kv: -kv[1])[:50]

        relationships["allTables"] = sorted(all_tables)
        relationships["tableCount"] = len(all_tables)
        relationships["filesScanned"] = files_scanned
        relationships["potentialJoinCount"] = len(dedup)
        relationships["topJoins"] = [
            {"table1": k[0], "table2": k[1], "fileCount": v} for k, v in top_joins
        ]
        relationships["filesWithTableUsage"] = sorted(set(
            r["file"] for refs in relationships["tableReferences"].values() for r in refs
        ))[:500]

        return relationships

    # ---------------------------------------------------------- cross reference

    def _cross_reference(self, dbf_schemas, table_relationships):
        """Match tables referenced in code against tables on disk."""
        disk_tables = set()
        for s in dbf_schemas:
            disk_tables.add((s.get("table") or "").upper())
            # Also match by basename without extension
            src = os.path.splitext(os.path.basename(s.get("sourceFile") or ""))[0].upper()
            if src:
                disk_tables.add(src)

        code_tables = set((t or "").upper() for t in table_relationships.get("allTables", []))

        in_code_not_on_disk = sorted(code_tables - disk_tables)
        on_disk_not_in_code = sorted(disk_tables - code_tables)

        return {
            "inCode": len(code_tables),
            "onDisk": len(disk_tables),
            "matched": len(code_tables & disk_tables),
            "inCodeNotOnDisk": in_code_not_on_disk,
            "onDiskNotInCode": on_disk_not_in_code,
        }

    # ------------------------------------------------------ database schema doc

    def _build_database_schema(self, dbf_schemas):
        """Build a consolidated database schema from DBF schemas."""
        tables = {}
        encodings = {}

        def _tkey(name):
            return (name or "").upper()

        for s in dbf_schemas:
            table_name = s["table"]
            fields = s.get("fields") or []
            schema_file = s.get("schemaFile")
            if not fields and schema_file and os.path.isfile(schema_file):
                try:
                    with open(schema_file, "r", encoding="utf-8") as f:
                        schema_data = json.load(f)
                    raw_fields = schema_data.get("fields", [])
                    fields = [
                        {
                            "name": f.get("name"),
                            "type": f.get("dbf_type") or f.get("type"),
                            "typeName": f.get("dbf_type_name") or f.get("typeName"),
                            "length": f.get("length"),
                            "decimal": f.get("decimal_count", 0) or 0,
                            "position": f.get("ordinal") or f.get("position"),
                            "isMemo": bool(f.get("is_memo") or f.get("isMemo")),
                        }
                        for f in raw_fields
                    ]
                except Exception:
                    pass

            entry = {
                "name": table_name,
                "file": s["sourceFile"],
                "recordCount": s["recordCount"],
                "fieldCount": s["fieldCount"],
                "hasMemo": s["hasMemo"],
                "memoFields": s.get("memoFields"),
                "codePage": s.get("codePage"),
                "reader": s["reader"],
                "fields": fields,
            }
            key = _tkey(table_name)
            if key not in tables:
                tables[key] = entry

            cp = s.get("codePage")
            if cp:
                encodings[cp] = encodings.get(cp, 0) + 1

        # Rank tables by record count for quick overview
        ranked = sorted(tables.values(), key=lambda t: -(t.get("recordCount") or 0))

        return {
            "schemaDate": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "tableCount": len(tables),
            "tables": sorted(tables.keys()),
            "encodings": encodings,
            "topByRecords": [
                {"table": t["name"], "file": t["file"], "records": t["recordCount"]}
                for t in ranked[:20]
            ],
            "tablesDetail": tables,
        }

    # ----------------------------------------------------------------- output

    def _write_outputs(self, project_summary, database_schema,
                       table_relationships, class_analysis, cross_ref,
                       duplicate_tables=None):
        """Write the Markdown report and all JSON artifacts to the output dir."""
        report_path = os.path.join(self.out, "audit_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# VFP Project Audit Report\n\n")
            f.write("**Tool version**: %s  \n" % __version__)
            f.write("**Date**: %s  \n" % time.strftime("%Y-%m-%d %H:%M:%S"))
            f.write("**Source**: %s  \n" % self.source)
            f.write("**Output**: %s  \n\n" % self.out)

            f.write("---\n\n## File Inventory\n\n")
            f.write("| Extension | Count |\n|---|---|\n")
            for ext, cnt in project_summary["fileInventory"].items():
                f.write("| `%s` | %d |\n" % (ext, cnt))
            f.write("\n")

            if "index" in project_summary:
                ix = project_summary["index"]
                f.write("## Code Index (.vfp-ai)\n\n")
                f.write("- Scanned: %s  \n" % (ix.get("scannedAt") or "unknown"))
                f.write("- Files: %d, Classes: %d, Methods: %d, Symbols: %d\n\n"
                        % (ix.get("fileCount", 0), ix.get("classCount", 0),
                           ix.get("methodCount", 0), ix.get("symbolCount", 0)))

            f.write("## Database Schema\n\n")
            f.write("- **Tables**: %d\n" % database_schema["tableCount"])
            f.write("- **Encodings**: %s\n\n" % json.dumps(database_schema["encodings"]))

            if self.data_export["requested"]:
                f.write("## DBF Data Export\n\n")
                f.write("> **NOTE**: This audit was run with the optional **full data export**. "
                        "Every table's contents (including memo/FPT) were read and written. "
                        "This is the most time-consuming part of an audit and can produce large files.\n\n")
                f.write("- **Data directory**: `%s`\n" % self.data_export["targetDir"])
                f.write("- **Tables exported**: %d\n" % self.data_export["tables"])
                f.write("- **Formats**: %s\n" % ", ".join("`%s`" % x for x in self.data_export["formats"]))
                f.write("- **Performed**: %s\n\n"
                        % ("yes" if self.data_export["performed"] else "PARTIAL/FAILED — see warnings"))

            if self.forms_export["requested"]:
                f.write("## Form / Class Code Export\n\n")
                f.write("> **NOTE**: This audit was run with **--include-forms**. The full "
                        "source of every form, class and method (button `Click` handlers, "
                        "PROCEDURE/Function bodies, grid bindings) was copied from the "
                        "BIN2PRG-converted text into the `forms/` subdirectory. This snapshot "
                        "is self-contained: form behaviour can be read/reconstructed **without** "
                        "the original .scx/.vcx/.frx and without FoxPro.\n\n")
                f.write("- **Forms directory**: `%s`\n" % self.forms_export["targetDir"])
                f.write("- **Source files copied**: %d\n" % self.forms_export["sourceFiles"])
                f.write("- **Size**: %.2f MB\n" % (self.forms_export["bytes"] / 1048576))
                if self.forms_export["byType"]:
                    f.write("- **By type**: %s\n"
                            % ", ".join("`%s`×%d" % (k, v)
                                        for k, v in self.forms_export["byType"].items()))
                f.write("- **Performed**: %s\n\n"
                        % ("yes" if self.forms_export["performed"] else "PARTIAL/FAILED — see warnings"))

            if database_schema["tables"]:
                f.write("### Top 20 Tables by Record Count\n\n")
                f.write("| Table | Records | Fields | Memo | Reader |\n|---|---|---|---|---|\n")
                for t in database_schema["topByRecords"]:
                    det = database_schema["tablesDetail"].get(t["table"], {})
                    memo = ", ".join(det.get("memoFields") or []) or "-"
                    f.write("| `%s` | %d | %d | %s | %s |\n" % (
                        t["table"], t["records"], det.get("fieldCount", 0),
                        memo, det.get("reader", "")))
                f.write("\n")

            f.write("## Class Analysis\n\n")
            f.write("- **Total classes**: %s\n" % class_analysis.get("totalClasses", "N/A"))
            f.write("- **Total methods**: %s\n" % class_analysis.get("totalMethods", "N/A"))
            f.write("- **Classes with methods**: %s\n" % class_analysis.get("classesWithMethods", "N/A"))
            if class_analysis.get("topComplexClasses"):
                f.write("\n### Top 20 Most Complex Classes\n\n")
                f.write("| Class | Base | Methods | File |\n|---|---|---|---|\n")
                for c in class_analysis["topComplexClasses"][:20]:
                    f.write("| `%s` | `%s` | %d | %s |\n" % (
                        c["name"], c.get("baseClass", ""), c["methodCount"], c.get("file", "")))
            if class_analysis.get("largestInheritance"):
                f.write("\n### Deepest Inheritance Chains\n\n")
                for name, info in class_analysis["largestInheritance"][:10]:
                    f.write("- `%s` (depth %d): %s\n" % (
                        name, info["depth"], " → ".join(info["chain"])))
            f.write("\n")

            f.write("## Table Relationships\n\n")
            f.write("- **Tables referenced in code**: %d\n" % table_relationships.get("tableCount", 0))
            f.write("- **SQL statements (SELECT)**: %d\n" % len(table_relationships.get("sqlStatements", [])))
            f.write("- **Potential table joins**: %d\n" % table_relationships.get("potentialJoinCount", 0))
            f.write("- **Files scanned**: %d\n\n" % table_relationships.get("filesScanned", 0))

            if cross_ref:
                f.write("## Cross-Reference: Code vs Disk\n\n")
                f.write("- Tables in code: %d\n" % cross_ref["inCode"])
                f.write("- Tables on disk: %d\n" % cross_ref["onDisk"])
                f.write("- Matched: %d\n\n" % cross_ref["matched"])
                if cross_ref["inCodeNotOnDisk"]:
                    f.write("**Referenced in code but NOT a physical DBF on disk** (%d).\n\n"
                            % len(cross_ref["inCodeNotOnDisk"]))
                    f.write("> Typically **temporary/work cursors** created at runtime\n"
                            "> (`SELECT ... INTO CURSOR`, `CREATE TABLE`, `USE ... NEW`) or dynamic\n"
                            "> table names — expected in VFP, not necessarily a problem.\n\n")
                    for t in cross_ref["inCodeNotOnDisk"][:80]:
                        f.write("- `%s`\n" % t)
                    f.write("\n")
                if cross_ref["onDiskNotInCode"]:
                    f.write("**Physical DBF on disk but NOT directly referenced in scanned code** (%d).\n\n"
                            % len(cross_ref["onDiskNotInCode"]))
                    f.write("> Possibly accessed via dynamic SQL, another project, or archive/leftover data.\n\n")
                    for t in cross_ref["onDiskNotInCode"][:80]:
                        f.write("- `%s`\n" % t)
                    f.write("\n")

            if duplicate_tables and duplicate_tables.get("duplicates"):
                f.write("## Redundant DBF Copies (duplicate table names)\n\n")
                f.write("- **Total DBF files**: %d  \n" % duplicate_tables.get("totalDbfFiles", 0))
                f.write("- **Unique table names**: %d  \n" % duplicate_tables.get("uniqueNames", 0))
                f.write("- **Names with >1 copy**: %d  \n" % duplicate_tables.get("duplicateNameCount", 0))
                f.write("- **Redundant (non-primary) copies**: %d\n\n"
                        % duplicate_tables.get("redundantCopies", 0))
                f.write("> These are almost always user **backups / temporary copies** of the same table.\n"
                        "> For reconstruction, keep only the **primary** copy (the one NOT in an\n"
                        "> archive/temp path and with the most records) and discard the rest.\n\n")
                f.write("| Table | Copies | Primary | Suspected backup copies |\n|---|---|---|---|\n")
                for d in duplicate_tables["duplicates"][:80]:
                    backs = ", ".join("`%s`" % b["file"] for b in d.get("suspectedBackups", [])) or "-"
                    f.write("| `%s` | %d | `%s` | %s |\n"
                            % (d["table"], d["copies"], d["primary"], backs))
                f.write("\n")

            if table_relationships.get("topJoins"):
                f.write("### Top Table Joins (by co-occurrence)\n\n")
                f.write("| Table 1 | Table 2 | Files |\n|---|---|---|\n")
                for j in table_relationships["topJoins"][:20]:
                    f.write("| `%s` | `%s` | %d |\n" % (j["table1"], j["table2"], j["fileCount"]))
                f.write("\n")

            if table_relationships.get("sqlStatements"):
                f.write("### Sample SQL Statements\n\n")
                for stmt in table_relationships["sqlStatements"][:30]:
                    f.write("- `%s:%s` — `%s`\n" % (stmt["file"], stmt.get("line", ""), stmt.get("raw", "")))
                f.write("\n")

            if self.warnings:
                f.write("## Warnings\n\n")
                for w in self.warnings:
                    f.write("- %s\n" % w)
                f.write("\n")
            if self.errors:
                f.write("## Errors\n\n")
                for e in self.errors:
                    f.write("- %s\n" % e)
                f.write("\n")

        # Write JSON artifacts
        with open(os.path.join(self.out, "data_export.json"), "w", encoding="utf-8") as f:
            json.dump(self.data_export, f, indent=2, ensure_ascii=False)
        with open(os.path.join(self.out, "project_summary.json"), "w", encoding="utf-8") as f:
            json.dump(project_summary, f, indent=2, ensure_ascii=False)
        with open(os.path.join(self.out, "database_schema.json"), "w", encoding="utf-8") as f:
            json.dump(database_schema, f, indent=2, ensure_ascii=False)
        with open(os.path.join(self.out, "table_relationships.json"), "w", encoding="utf-8") as f:
            json.dump(table_relationships, f, indent=2, ensure_ascii=False)
        with open(os.path.join(self.out, "class_analysis.json"), "w", encoding="utf-8") as f:
            json.dump(class_analysis, f, indent=2, ensure_ascii=False)
        with open(os.path.join(self.out, "cross_reference.json"), "w", encoding="utf-8") as f:
            json.dump(cross_ref, f, indent=2, ensure_ascii=False)
        if duplicate_tables is not None:
            with open(os.path.join(self.out, "duplicate_tables.json"), "w", encoding="utf-8") as f:
                json.dump(duplicate_tables, f, indent=2, ensure_ascii=False)
        with open(os.path.join(self.out, "forms_export.json"), "w", encoding="utf-8") as f:
            json.dump(self.forms_export, f, indent=2, ensure_ascii=False)

        return report_path


def main():
    """argparse entrypoint for the audit CLI."""
    ap = argparse.ArgumentParser(prog="vfp_audit")
    ap.add_argument("--version", action="version", version="vfp_audit " + __version__)
    ap.add_argument("--source", required=True, help="VFP project root directory")
    ap.add_argument("--out", required=True, help="Output directory for audit report")
    ap.add_argument("--skip-sync", action="store_true",
                    help="Skip automatic BIN2PRG sync (use an existing .vfp-ai cache). "
                         "By default the audit syncs first if the cache is missing.")
    ap.add_argument("--include-data", action="store_true",
                    help="OPTIONAL / SLOW: also export ALL DBF record data (incl. memo/FPT) "
                         "to <audit>/dbf, mirroring the project's folder structure. "
                         "This reads every table and can take a long time and fill disk.")
    ap.add_argument("--include-forms", action="store_true", default=True,
                    help="Export the FULL source of every form, class and method "
                         "(button Click handlers, PROCEDURE/Function bodies) from the "
                         "BIN2PRG-converted .sc2/.vc2/.fr2 text + project .prg/.h into "
                         "<audit>/forms. ON BY DEFAULT — makes the audit self-contained "
                         "for form reconstruction without FoxPro or the original "
                         ".scx/.vcx/.frx. Disable with --no-include-forms.")
    ap.add_argument("--no-include-forms", dest="include_forms",
                    action="store_false",
                    help="Skip the form/class code export (faster, smaller audit).")
    ap.add_argument("--data-formats", default="jsonl",
                    help="Data export formats: jsonl,csv,json,xlsx (used with --include-data)")
    ap.add_argument("--max-tables", type=int, default=0,
                    help="With --include-data: limit to N largest tables (0 = all)")
    ap.add_argument("--dbf-exclude", default="",
                    help="Comma-separated uppercase substrings to exclude from DBF scan (e.g. ARCH,TMP)")
    ap.add_argument("--only-tables", default="",
                    help="Only process DBF tables whose path contains one of these uppercase "
                         "substrings (comma-separated, e.g. ARCH,TMP). Overrides the full scan.")
    ap.add_argument("--no-validate", action="store_true",
                    help="Export DBF data with dbfbridge validate=False (use when validate=True "
                         "fails on a table, e.g. OSError 22). The tool already auto-retries "
                         "without validation; this flag skips the validated pass entirely.")
    ap.add_argument("--no-cache-scan", action="store_true",
                    help="Do not scan .vfp-ai/source for table usage (slower but avoids double-scan)")
    a = ap.parse_args()

    if not os.path.isdir(a.source):
        sys.exit(2)

    formats = tuple(f.strip() for f in a.data_formats.split(",") if f.strip())
    excludes = tuple(a.dbf_exclude.split(","))

    auditor = VFPProjectAuditor(
        source_dir=a.source,
        out_dir=a.out,
        skip_sync=a.skip_sync,
        include_data=a.include_data,
        data_formats=formats,
        max_tables=a.max_tables,
        dbf_exclude=excludes,
        scan_cache=not a.no_cache_scan,
        include_forms=a.include_forms,
    )

    try:
        result = auditor.run()
        _emit(True, rc=0, auditDir=result["auditDir"], summary=result["summary"])
    except Exception as e:
        _emit(False, stderr="audit failed: %s" % e)


if __name__ == "__main__":
    main()
