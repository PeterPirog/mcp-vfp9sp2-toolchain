#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
vfp_audit.py - Comprehensive VFP project audit.

Runs a full analysis of a VFP project directory and consolidates results
into a target output directory. Generates:

  1. project_summary.json  — file inventory, class/method counts
  2. database_schema.json  — all DBF table schemas with encodings
  3. table_relationships.json — inferred table usage + SQL join analysis
  4. class_analysis.json  — class hierarchy, method counts, complexity
  5. audit_report.md       — human-readable summary

Partially uses FoxBin2Prg (needs VFP9) for SC2/VC2 conversion.
DBF schema/data analysis uses pure Python (dbfread or built-in fallback).

Usage:
    py vfp_audit.py --source <project_root> --out <audit_output_dir>
                    [--skip-sync] [--include-data] [--formats jsonl,csv]

Output protocol: one JSON object on stdout:
    {"ok": bool, "rc": int|null, "auditDir": str, "summary": {...}, "stderr": str}
"""

import argparse
import json
import os
import re
import sys
import time


def _emit(ok, **kw):
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


def _run_python(cmd, env=None, timeout=300):
    """Run a python subcommand and return parsed JSON output."""
    import subprocess
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           env=env, timeout=timeout)
        out = p.stdout.strip()
        if not out:
            return {"ok": False, "rc": p.returncode, "stderr": p.stderr.strip()}
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return {"ok": False, "rc": p.returncode, "stdout": out, "stderr": p.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"ok": False, "rc": -1, "stderr": "timeout"}


def _import_local(name, toolchain_home):
    """Import a module from the toolchain directory."""
    if toolchain_home not in sys.path:
        sys.path.insert(0, toolchain_home)
    return __import__(name)


class VFPProjectAuditor:
    """Orchestrates a full VFP project audit."""

    def __init__(self, source_dir, out_dir, skip_sync=False,
                 include_data=False, data_formats=("jsonl",)):
        self.source = os.path.abspath(source_dir)
        self.out = os.path.abspath(out_dir)
        self.skip_sync = skip_sync
        self.include_data = include_data
        self.data_formats = data_formats
        self.cache_dir = os.path.join(self.source, ".vfp-ai")
        self.dbf_dir = os.path.join(self.out, "dbf")
        self.warnings = []

    def run(self):
        """Run the full audit and generate all output files."""
        os.makedirs(self.out, exist_ok=True)
        os.makedirs(self.dbf_dir, exist_ok=True)

        py = "py" if os.name == "nt" else "python3"
        here = os.environ.get("VFP_TOOLCHAIN_HOME", "")

        # 1. Sync (BIN2PRG conversion + index)
        if not self.skip_sync:
            self._sync_project(py, here)

        # 2. DBF schema export
        dbf_schemas = self._export_dbf_schemas(py, here)

        # 3. DBF data export (optional)
        if self.include_data:
            self._export_dbf_data(py, here)

        # 4. Parse index for project summary
        project_summary = self._build_project_summary()

        # 5. Parse class analysis
        class_analysis = self._build_class_analysis()

        # 6. Find table relationships / SQL joins
        table_relationships = self._find_table_relationships(py, here)

        # 7. Generate database schema document
        database_schema = self._build_database_schema(dbf_schemas)

        # 8. Write audit report
        self._write_audit_report(project_summary, database_schema,
                                 table_relationships, class_analysis)

        return {
            "ok": True,
            "auditDir": self.out,
            "summary": {
                "projectSummary": project_summary,
                "databaseSchema": database_schema,
                "tableRelationships": table_relationships,
                "classAnalysis": class_analysis,
                "warnings": self.warnings,
            },
        }

    def _sync_project(self, py, here):
        """Run vfp_sync to convert binaries and build index."""
        driver = os.path.join(here, "vfp_driver.py") if here else "vfp_driver.py"
        # Check if cache already exists
        idx_path = os.path.join(self.cache_dir, "index.json")
        if os.path.isfile(idx_path):
            self.warnings.append("Using existing index.json — run with --skip-sync=false to re-convert")
            return

        result = _run_python([
            py, driver, "convert_dir",
            "--project", self.source,
            "--out", self.cache_dir,
            "--cfg", os.path.join(here, "FoxBin2Prg-AI.cfg"),
            "--prg", os.path.join(here or "", "tools", "foxbin2prg", "foxbin2prg.prg"),
            "--timeout", "600",
        ], timeout=600)

        if not result.get("ok"):
            self.warnings.append("BIN2PRG sync failed: %s" % result.get("stderr", "unknown error"))
            return

        # Build index
        result2 = _run_python([
            py, driver, "index",
            "--project", os.path.join(self.cache_dir, "source"),
            "--cache", self.cache_dir,
            "--full",
        ], timeout=300)

        if not result2.get("ok"):
            self.warnings.append("Index build failed: %s" % result2.get("stderr", "unknown error"))

    def _export_dbf_schemas(self, py, here):
        """Export schemas for all DBF files in the project."""
        driver = os.path.join(here, "vfp_driver.py") if here else "vfp_driver.py"
        dbf_files = []
        for root, dirs, files in os.walk(self.source):
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d.lower() not in ("backup", "backups", "archive", "node_modules")]
            for fn in files:
                if os.path.splitext(fn)[1].lower() == ".dbf":
                    dbf_files.append(os.path.join(root, fn))

        schemas = []
        for dbf in dbf_files:
            result = _run_python([
                py, driver, "dbf_schema",
                "--input", dbf,
                "--out", self.dbf_dir,
            ], timeout=30)
            if result.get("ok") and result.get("data", {}).get("schemaFile"):
                schemas.append({
                    "table": result.get("table"),
                    "sourceFile": os.path.relpath(dbf, self.source),
                    "recordCount": result.get("recordCount", 0),
                    "fieldCount": result.get("fieldCount", 0),
                    "hasMemo": result.get("hasMemo", False),
                    "codePage": result.get("codePage"),
                    "reader": result.get("reader", "dbfread"),
                    "schemaFile": result["data"]["schemaFile"],
                })
            else:
                self.warnings.append("DBF schema export failed for %s: %s" % (dbf, result.get("stderr", "unknown")))

        return sorted(schemas, key=lambda x: x.get("table") or "")

    def _export_dbf_data(self, py, here):
        """Export DBF data to JSONL/CSV."""
        driver = os.path.join(here, "vfp_driver.py") if here else "vfp_driver.py"
        dbf_files = []
        for root, dirs, files in os.walk(self.source):
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d.lower() not in ("backup", "backups", "archive")]
            for fn in files:
                if os.path.splitext(fn)[1].lower() == ".dbf":
                    dbf_files.append(os.path.join(root, fn))

        for fmt in self.data_formats:
            fmt_dir = os.path.join(self.dbf_dir, fmt)
            os.makedirs(fmt_dir, exist_ok=True)
            for dbf in dbf_files:
                _run_python([
                    py, driver, "dbf_data",
                    "--input", dbf,
                    "--out", fmt_dir,
                    "--format", fmt,
                    "--deleted", "include",
                ], timeout=120)

    def _build_project_summary(self):
        """Build summary from index.json and file inventory."""
        idx_path = os.path.join(self.cache_dir, "index.json")

        summary = {
            "projectRoot": self.source,
            "auditDate": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "fileInventory": self._build_file_inventory(),
            "indexAvailable": os.path.isfile(idx_path),
        }

        if os.path.isfile(idx_path):
            try:
                with open(idx_path, "r", encoding="utf-8") as f:
                    idx = json.load(f)
                summary["index"] = {
                    "fileCount": idx.get("fileCount", 0),
                    "classCount": idx.get("classCount", 0),
                    "methodCount": idx.get("methodCount", 0),
                    "scannedAt": idx.get("scannedAt"),
                }
            except Exception as e:
                self.warnings.append("Could not read index.json: %s" % e)

        return summary

    def _build_file_inventory(self):
        """Walk the project and inventory VFP files."""
        exts = [".scx", ".vcx", ".frx", ".mnx", ".lbx", ".pjx", ".dbc",
                ".dbf", ".fpt", ".cdx", ".prg", ".h", ".pjt",
                ".sct", ".vct", ".frt", ".mnt", ".lb2", ".dct", ".dcx"]
        counts = {}
        for root, dirs, files in os.walk(self.source):
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d.lower() not in ("backup", "backups", "archive",
                                             "node_modules", ".vfp-ai")]
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext in exts:
                    counts[ext] = counts.get(ext, 0) + 1
        return counts

    def _build_class_analysis(self):
        """Build class analysis from index.json."""
        idx_path = os.path.join(self.cache_dir, "index.json")
        if not os.path.isfile(idx_path):
            return {"error": "index.json not found — run vfp_sync first"}

        with open(idx_path, "r", encoding="utf-8") as f:
            idx = json.load(f)

        classes = idx.get("classes", [])
        methods = idx.get("methods", [])

        # Group methods by class
        by_class = {}
        for cls in classes:
            name = cls["name"]
            by_class.setdefault(name, []).append(cls)

        # Find classes with most methods (complexity)
        class_complexity = []
        for cls_info in classes:
            cls_name = cls_info["name"]
            method_count = sum(1 for m in methods if m.get("class", "") == cls_name)
            class_complexity.append({
                "name": cls_name,
                "baseClass": cls_info.get("baseClass"),
                "file": cls_info.get("file"),
                "methodCount": method_count,
            })
        class_complexity.sort(key=lambda x: x["methodCount"], reverse=True)

        # Find inheritance depth
        inheritance_chains = {}
        for cls_info in classes:
            cls_name = cls_info["name"]
            base = cls_info.get("baseClass", "")
            chain = [cls_name]
            visited = {cls_name}
            depth = 0
            while base and base not in visited and depth < 20:
                chain.append(base)
                visited.add(base)
                # Find the base class in our index
                found_base = None
                for c in classes:
                    if c["name"].lower() == base.lower():
                        found_base = c
                        break
                if found_base:
                    base = found_base.get("baseClass", "")
                    depth += 1
                else:
                    break
            inheritance_chains[cls_name] = {
                "chain": chain,
                "depth": depth,
            }

        return {
            "totalClasses": len(classes),
            "totalMethods": len(methods),
            "topComplexClasses": class_complexity[:20],
            "inheritanceChains": inheritance_chains,
            "classNames": sorted(set(c["name"] for c in classes)),
        }

    def _find_table_relationships(self, py, here):
        """Find USE/SELECT patterns in code and infer table relationships."""
        relationships = {
            "uses": {},
            "sqlStatements": [],
            "tableReferences": {},
            "potentialJoins": [],
        }

        # Scan .sc2/.vc2/.prg files in cache for USE/SELECT patterns
        cache_source = os.path.join(self.cache_dir, "source")
        if not os.path.isdir(cache_source):
            self.warnings.append("No .vfp-ai/source cache found — table usage analysis limited")
            return relationships

        use_re = re.compile(r'\bUSE\s+["\']?(\w+)["\']?\s*(?:\s+IN\s+["\']?(\w+)["\']?)?', re.IGNORECASE)
        select_re = re.compile(r'\bSELECT\s+(\w+)(?:\s*,\s*(\w+))?\s+FROM\s+(["\']?)(\w+)(\3)', re.IGNORECASE)
        select_all_re = re.compile(r'\bSELECT\s+(\*)\s+FROM\s+(["\']?)(\w+)(\2)', re.IGNORECASE)
        replace_re = re.compile(r'\bREPLACE\s+(\*|\w+)\s+(?:\sin\b|\sIN\b|WITH\s+IIF)', re.IGNORECASE)
        insert_re = re.compile(r'\bINSERT\s+INTO\s+(\w+)', re.IGNORECASE)

        all_tables = set()

        for root, dirs, files in os.walk(cache_source):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in (".sc2", ".vc2", ".prg", ".pj2", ".dc2", ".db2"):
                    continue
                fp = os.path.join(root, fn)
                try:
                    with open(fp, "r", encoding="cp1252", errors="replace") as f:
                        content = f.read()
                except OSError:
                    continue

                rel_path = os.path.relpath(fp, cache_source)
                tables_in_file = set()

                for m in use_re.finditer(content):
                    tbl = m.group(1).upper()
                    all_tables.add(tbl)
                    tables_in_file.add(tbl)
                    relationships["uses"].setdefault(tbl, []).append({
                        "file": rel_path,
                        "alias": m.group(2).upper() if m.group(2) else None,
                    })

                for line_no, line in enumerate(content.splitlines(), 1):
                    # SQL SELECT ... FROM
                    m = select_re.search(line) or select_all_re.search(line)
                    if m:
                        tbl = m.group(3).upper() if select_re.match(line) else m.group(2).upper()
                        all_tables.add(tbl)
                        tables_in_file.add(tbl)
                        relationships["sqlStatements"].append({
                            "file": rel_path,
                            "line": line_no,
                            "type": "SELECT",
                            "table": tbl,
                            "raw": line.strip()[:200],
                        })
                        relationships["tableReferences"].setdefault(tbl, []).append({
                            "file": rel_path,
                            "line": line_no,
                            "type": "SELECT",
                        })

                    # INSERT INTO
                    m = insert_re.search(line)
                    if m:
                        tbl = m.group(1).upper()
                        all_tables.add(tbl)
                        tables_in_file.add(tbl)
                        relationships["tableReferences"].setdefault(tbl, []).append({
                            "file": rel_path,
                            "line": line_no,
                            "type": "INSERT",
                        })

                    # REPLACE
                    m = replace_re.search(line)
                    if m:
                        tbl = m.group(1).upper() if m.group(1) != "*" else None
                        if tbl:
                            all_tables.add(tbl)
                            tables_in_file.add(tbl)
                            relationships["tableReferences"].setdefault(tbl, []).append({
                                "file": rel_path,
                                "line": line_no,
                                "type": "REPLACE",
                            })

                # Track which tables are used together (potential joins)
                if len(tables_in_file) > 1:
                    for t1 in tables_in_file:
                        for t2 in tables_in_file:
                            if t1 < t2:
                                key = "%s <-> %s" % (t1, t2)
                                relationships["potentialJoins"].append({
                                    "table1": t1,
                                    "table2": t2,
                                    "file": rel_path,
                                    "type": "co-occur in USE/SELECT",
                                })

        relationships["allTables"] = sorted(all_tables)
        relationships["tableCount"] = len(all_tables)
        relationships["filesWithTableUsage"] = sorted(set(
            r["file"] for refs in relationships["tableReferences"].values()
            for r in refs
        ))
        relationships["potentialJoinCount"] = len(relationships["potentialJoins"])

        return relationships

    def _build_database_schema(self, dbf_schemas):
        """Build a consolidated database schema from DBF schemas."""
        tables = {}
        encodings = {}

        for s in dbf_schemas:
            table_name = s["table"]
            schema_file = s.get("schemaFile")
            fields = []
            if schema_file and os.path.isfile(schema_file):
                try:
                    with open(schema_file, "r", encoding="utf-8") as f:
                        schema_data = json.load(f)
                    fields = schema_data.get("fields", [])
                except Exception:
                    pass

            tables[table_name] = {
                "file": s["sourceFile"],
                "recordCount": s["recordCount"],
                "fieldCount": s["fieldCount"],
                "hasMemo": s["hasMemo"],
                "fields": fields,
                "reader": s["reader"],
            }

            cp = s.get("codePage")
            if cp:
                encodings[cp] = encodings.get(cp, 0) + 1

        return {
            "schemaDate": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "tableCount": len(tables),
            "tables": sorted(tables.keys()),
            "encodings": encodings,
            "tablesDetail": tables,
        }

    def _write_audit_report(self, project_summary, database_schema,
                            table_relationships, class_analysis):
        """Write a human-readable Markdown audit report."""
        report_path = os.path.join(self.out, "audit_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# VFP Project Audit Report\n\n")
            f.write("**Date**: %s  \n" % time.strftime("%Y-%m-%d %H:%M:%S"))
            f.write("**Source**: %s  \n" % self.source)
            f.write("**Output**: %s  \n\n" % self.out)

            f.write("---\n\n")
            f.write("## File Inventory\n\n")
            f.write("| Extension | Count |\n|---|---|\n")
            for ext in sorted(project_summary["fileInventory"].keys()):
                f.write("| `%s` | %d |\n" % (ext, project_summary["fileInventory"][ext]))
            f.write("\n")

            f.write("## Database Schema\n\n")
            f.write("- **Tables**: %d\n" % database_schema["tableCount"])
            f.write("- **Encodings**: %s\n" % json.dumps(database_schema["encodings"], indent=0))
            if database_schema["tables"]:
                f.write("\n| Table | Records | Fields | Memo | CodePage | Source |\n")
                f.write("|---|---|---|---|---|---|\n")
                for tname in database_schema["tables"]:
                    t = database_schema["tablesDetail"].get(tname, {})
                    f.write("| `%s` | %d | %d | %s | %s | %s |\n" % (
                        tname,
                        t.get("recordCount", 0),
                        t.get("fieldCount", 0),
                        "Yes" if t.get("hasMemo") else "No",
                        t.get("reader", "unknown"),
                        t.get("file", ""),
                    ))
            f.write("\n")

            f.write("## Class Analysis\n\n")
            f.write("- **Total classes**: %s\n" % class_analysis.get("totalClasses", "N/A"))
            f.write("- **Total methods**: %s\n" % class_analysis.get("totalMethods", "N/A"))
            if class_analysis.get("topComplexClasses"):
                f.write("\n### Top 10 Most Complex Classes\n\n")
                f.write("| Class | Base | Methods | File |\n|---|---|---|---|\n")
                for c in class_analysis["topComplexClasses"][:10]:
                    f.write("| `%s` | `%s` | %d | %s |\n" % (
                        c["name"], c.get("baseClass", ""), c["methodCount"], c.get("file", "")))
            f.write("\n")

            f.write("## Table Relationships\n\n")
            f.write("- **Tables referenced in code**: %d\n" % table_relationships.get("tableCount", 0))
            f.write("- **SQL statements (SELECT)**: %d\n" % len(table_relationships.get("sqlStatements", [])))
            f.write("- **Potential table joins**: %d\n" % table_relationships.get("potentialJoinCount", 0))
            if table_relationships.get("allTables"):
                f.write("\n**Tables used in code**: %s\n\n" % ", ".join(table_relationships["allTables"]))
            if table_relationships.get("sqlStatements"):
                f.write("\n### SQL Statements Found\n\n")
                for stmt in table_relationships["sqlStatements"][:20]:
                    f.write("- `%s:%d` — `%s`\n" % (stmt["file"], stmt["line"], stmt.get("raw", "")))
            if self.warnings:
                f.write("\n## Warnings\n\n")
                for w in self.warnings:
                    f.write("- %s\n" % w)

        # Write JSON artifacts
        with open(os.path.join(self.out, "project_summary.json"), "w") as f:
            json.dump(project_summary, f, indent=2, ensure_ascii=False)
        with open(os.path.join(self.out, "database_schema.json"), "w") as f:
            json.dump(database_schema, f, indent=2, ensure_ascii=False)
        with open(os.path.join(self.out, "table_relationships.json"), "w") as f:
            json.dump(table_relationships, f, indent=2, ensure_ascii=False)
        with open(os.path.join(self.out, "class_analysis.json"), "w") as f:
            json.dump(class_analysis, f, indent=2, ensure_ascii=False)

        return report_path


def main():
    ap = argparse.ArgumentParser(prog="vfp_audit")
    ap.add_argument("--source", required=True, help="VFP project root directory")
    ap.add_argument("--out", required=True, help="Output directory for audit report")
    ap.add_argument("--skip-sync", action="store_true",
                    help="Skip BIN2PRG conversion (use existing .vfp-ai cache)")
    ap.add_argument("--include-data", action="store_true",
                    help="Also export DBF record data (JSONL/CSV)")
    ap.add_argument("--data-formats", default="jsonl",
                    help="Comma-separated data export formats: jsonl,csv")
    a = ap.parse_args()

    if not os.path.isdir(a.source):
        sys.exit(2)

    formats = tuple(f.strip() for f in a.data_formats.split(","))

    auditor = VFPProjectAuditor(
        source_dir=a.source,
        out_dir=a.out,
        skip_sync=a.skip_sync,
        include_data=a.include_data,
        data_formats=formats,
    )

    try:
        result = auditor.run()
        _emit(True, rc=0, auditDir=result["auditDir"], summary=result["summary"])
    except Exception as e:
        _emit(False, stderr="audit failed: %s" % e)


if __name__ == "__main__":
    main()
