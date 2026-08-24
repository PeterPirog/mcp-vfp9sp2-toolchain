# Audit Artifacts

A full `vfp_audit` run writes the following files into the `--out` directory.
All JSON is UTF-8, `ensure_ascii=False`. The Markdown report is the human-facing
summary; the JSON files are the machine-readable detail.

## File inventory

| File | Purpose |
|---|---|
| `audit_report.md` | Human-readable summary (versions, inventory, top classes, joins, duplicates, **indexes**, warnings) |
| `project_summary.json` | File inventory by extension + index stats |
| `database_schema.json` | All DBF table schemas, encodings, top tables by records **+ index tags per table** |
| `indexes.json` | CDX/IDX index structure per table: tags, sort order, type, expressions (when VFP9 available) |
| `table_relationships.json` | Table usage patterns, SQL statements, inferred joins |
| `class_analysis.json` | Class hierarchy, inheritance depth, complexity ranking |
| `cross_reference.json` | Tables referenced in code vs. tables on disk |
| `duplicate_tables.json` | Tables existing as multiple files (backups/temp copies) |
| `forms_export.json` | What the `forms/` export produced (files, bytes, by type) |
| `data_export.json` | What the `--include-data` export produced |
| `forms/` | Full form/class/method source + PRG scripts (on by default) |
| `dbf/` | Per-table `<table>_schema.json`; with `--include-data` (**default on**), full record JSONL |

## Schemas

### `database_schema.json`
```jsonc
{
  "schemaDate": "YYYY-MM-DD HH:MM:SS",
  "tableCount": 223,                 // unique table names
  "tables": ["BOK", "..."],          // sorted names
  "encodings": { "cp1250": 210, "..." : 13 },
  "topByRecords": [ { "table": "...", "recordCount": 12345 } ],
  "tablesDetail": [
    {
      "table": "BOK",
      "sourceFile": "DANE\\bok.dbf", // relative to project root
      "recordCount": 0,
      "fieldCount": 12,
      "codePage": "cp1250",
      "hasMemo": true,
      "memoFields": ["UWAGI"],
      "fields": [
        { "name": "BOK_ID", "type": "N", "width": 10, "decimals": 0, "null": false }
      ]
    }
  ]
}
```

### `class_analysis.json`
```jsonc
{
  "totalClasses": 599,
  "totalMethods": 8168,
  "classesWithMethods": 94,
  "topComplexClasses": [
    { "name": "form1", "baseClass": "form", "methodCount": 4510, "file": "..." }
  ],
  "largestInheritance": [
    ["form1", { "depth": 3, "chain": ["form1", "form", "base"] }]
  ]
}
```

### `table_relationships.json`
```jsonc
{
  "tableCount": 242,                 // tables referenced in code
  "uses": [ { "table": "...", "file": "...", "op": "USE" } ],
  "sqlStatements": [ { "file": "...", "line": 12, "raw": "SELECT ..." } ],
  "potentialJoins": [ { "left": "...", "right": "...", "count": 7 } ],
  "potentialJoinCount": 61731,
  "topJoins": [ { "left": "...", "right": "...", "count": 7 } ],
  "filesScanned": 940
}
```

### `cross_reference.json`
```jsonc
{
  "inCode": 242,        // tables referenced in code
  "onDisk": 261,        // physical DBF files
  "matched": 196,       // both
  "inCodeNotOnDisk": ["CURSOR1", "..."],  // runtime cursors / temp tables
  "onDiskNotInCode": ["bok_arch", "..."]  // archives / leftovers
}
```

### `duplicate_tables.json`
```jsonc
{
  "totalDbfFiles": 261,
  "uniqueNames": 223,
  "duplicateNameCount": 36,   // names with >1 physical copy
  "redundantCopies": 38,     // non-primary copies
  "duplicates": [
    {
      "table": "FOXUSER",
      "copies": 4,
      "primary": "DANE\\FOXUSER.dbf",
      "suspectedBackups": [
        { "file": "DANE_SIM\\FOXUSER.dbf", "records": 1, "sizeMB": 0.02, "archiveLike": false },
        { "file": "BAZA_TMP\\FOXUSER.dbf", "records": 0, "sizeMB": 0.0,  "archiveLike": true }
      ]
    }
  ]
}
```

> **Rule of thumb:** keep only `primary`; the `suspectedBackups` are almost
> always user backups/temporary copies.

### `forms_export.json`
```jsonc
{
  "requested": true,
  "performed": true,
  "targetDir": "<out>\\forms",
  "sourceFiles": 969,
  "bytes": 21048960,
  "byType": { ".sc2": 840, ".fr2": 65, ".vc2": 41, ".prg": 15, ".pj2": 8 },
  "note": "FULL FORM/CLASS SOURCE EXPORT — ..."
}
```

### `data_export.json`
```jsonc
{
  "requested": true,
  "performed": true,
  "targetDir": "<out>\\dbf",
  "tables": 261,
  "formats": ["jsonl"],
  "note": "FULL DBF DATA EXPORT — ..."
}
```

### `dbf/` layout
```
dbf/
├── DANE/
│   ├── bok_schema.json      # always present
│   ├── bok.jsonl            # only with --include-data
│   └── bok.fpt->(inlined into JSONL "memo" fields)
├── BAZA_MW/
│   └── ...
└── migration_report.jsonl   # dbfbridge per-table status
```
