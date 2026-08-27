# PROMPT DLA OPENCODE — ULEPSZENIE mcp-vfp9sp2-toolchain

## Kontekst

Repozytorium: `D:\Opencode projects\Project VFP\mcp-vfp9sp2-toolchain` (branch: `main`)
Dokument rekomendacji: `docs/TOOLCHAIN_IMPROVEMENTS.md` (już utworzony)

## Instrukcja dla OpenCode

```
Pracujesz w repozytorium mcp-vfp9sp2-toolchain na branchu głównym.

UTWÓRZ NOWY BRANCH: `feature/performance-audit-tools`

Następnie zaimplementuj poniższe ulepszenia w podanej kolejności.
Po każdej implementacji uruchom testy i zrób commit.

Wszystkie nowe subcommands w vfp_driver.py muszą:
1. Być zgodne z protokołem JSON output (jak istniejące subcommands)
2. Mieć wpis w argparse w main()
3. Mieć dokumentację w README.md
4. Mieć wpis w agents/vfp-analyst.md (jeśli dotyczy agenta)

---

## ZADANIE 1: vfp_run_prg — uruchamianie PRG w VFP9

Dodaj subcommand `run_prg` do vfp_driver.py:

```python
def run_run_prg(prg_path, workdir=None, timeout=120):
    """Run a .prg file in VFP9 via command line.
    
    Uses: vfp9.exe -c <prg_path> with cwd=workdir.
    Captures stdout/stderr and any .ERR file content.
    Returns JSON: {ok, rc, stdout, stderr, errFile, durationMs}
    """
```

Argparse:
```python
prp = sub.add_parser("run_prg", help="Run a .prg script in VFP9")
prp.add_argument("--prg", required=True, help="Path to .prg file")
prp.add_argument("--workdir", default=None, help="Working directory (default: prg dir)")
prp.add_argument("--timeout", type=int, default=120)
```

Implementacja:
- Znajdź VFP9: `C:\Program Files (x86)\Microsoft Visual FoxPro 9\vfp9.exe` (sprawdź też `Program Files`)
- Uruchom: `Start-Process vfp9.exe -ArgumentList @("-c", prg_name) -WorkingDirectory workdir`
- Po zakończeniu sprawdź czy istnieje `.ERR` plik (o tej samej nazwie co .prg)
- Zwróć JSON z ok/rc/stdout/stderr/errFile/durationMs

Test: uruchom prosty `? "Hello"` prg i sprawdź ok=true.

---

## ZADANIE 2: vfp_benchmark — pomiar operacji DBF

Dodaj subcommand `benchmark` do vfp_driver.py:

```python
def run_benchmark(project, table, operation, iterations, out_file=None, timeout=300):
    """Benchmark a DBF operation in VFP9.
    
    Generates a temporary .prg that:
    1. Opens the table(s) from <project>/Dane/
    2. Runs the operation N times with SECONDS() timing
    3. Checks SYS(3054) for Rushmore status
    4. Writes results to a text file
    
    Operations: calculate_max, calculate_for, seek, scan, count_for, sum, set_filter_goto
    """
```

Argparse:
```python
pb = sub.add_parser("benchmark", help="Benchmark DBF operations in VFP9")
pb.add_argument("--project", required=True, help="VFP project root (contains Dane/)")
pb.add_argument("--table", required=True, help="Table alias to benchmark")
pb.add_argument("--operation", required=True, 
                choices=["calculate_max", "calculate_for", "seek", "scan", 
                         "count_for", "sum", "set_filter_goto"])
pb.add_argument("--expression", default="", help="FOR expression or SEEK key")
pb.add_argument("--field", default="", help="Field name for CALCULATE/SUM")
pb.add_argument("--tag", default="", help="TAG name for SEEK")
pb.add_argument("--iterations", type=int, default=10)
pb.add_argument("--out", default=None, help="Output file for results")
pb.add_argument("--timeout", type=int, default=300)
```

Implementacja:
1. Wygeneruj `benchmark_temp.prg` w katalogu output (lub temp):
   - `SET DEFAULT TO <project>/Dane/`
   - `USE <table> IN 0 SHARED`
   - `SET OPTIMIZE ON`
   - Pętla FOR i=1 TO iterations z `lnStart = SECONDS()` ... `lnEnd = SECONDS()`
   - `SYS(3054, 1, "<expression>")` — zapisz wynik
   - Zapisz wyniki do `benchmark_results.txt` (SECONDS timing + SYS3054)
   - `QUIT`
2. Uruchom przez `run_prg` (ZADANIE 1)
3. Parsuj `benchmark_results.txt`
4. Zwróć JSON: {ok, operation, table, iterations, coldMs, warmMs, avgMs, minMs, maxMs, rushmore, sys3054}

---

## ZADANIE 3: vfp_form_perf — mapa wydajności formularza

Dodaj subcommand `form_perf` do vfp_driver.py:

```python
def run_form_perf(form_sc2, tables_dir, out_file=None):
    """Build a performance access map for a form.
    
    Parses the .sc2 file and for each PROCEDURE finds:
    - SEEK, SCAN FOR, CALCULATE FOR, COUNT FOR, SUM FOR, LOCATE FOR
    - SET FILTER TO, DELETE ALL FOR, REPLACE FOR
    - Identifies the table from context (SELECT alias)
    - Cross-references with CDX tags (vfp_cdx.parse_cdx)
    - Marks Rushmore status: FULL/PARTIAL/NONE
    - Suggests missing indexes
    """
```

Argparse:
```python
pfp = sub.add_parser("form_perf", help="Build performance access map for a form")
pfp.add_argument("--form", required=True, help="Path to .sc2 file")
pfp.add_argument("--tables-dir", required=True, help="Directory with .dbf/.cdx files")
pfp.add_argument("--out", default=None, help="Output JSON file")
```

Implementacja:
1. Parsuj `.sc2` (użyj regexów z vfp_indexer.py):
   - Znajdź wszystkie `PROCEDURE <name>`
   - Wewnątrz procedury szukaj: `SELECT <alias>`, `SEEK <expr>`, `SCAN FOR <expr>`, 
     `CALCULATE ... FOR <expr>`, `COUNT FOR <expr>`, `SUM ... FOR <expr>`,
     `LOCATE FOR <expr>`, `SET FILTER TO <expr>`, `DELETE ALL FOR <expr>`
   - Dla każdej operacji FOR:
     a. Identyfikuj tabelę z ostatniego `SELECT <alias>` przed operacją
     b. Wczytaj CDX tabeli: `vfp_cdx.parse_cdx(<tables_dir>/<alias>.cdx)`
     c. Sprawdź czy wyrażenie FOR pasuje do któregoś TAG:
        - Ekstraktuj nazwy pól z FOR (np. `LEFT(k_pr_sp_nr,10)` -> pole `k_pr_sp_nr`)
        - Porównaj z wyrażeniami TAG (np. TAG `K_PR_SP_NR` = `K_PR_SP_NR`)
        - Sprawdź czy FOR używa funkcji blokujących: `LEFT()`, `RIGHT()`, `ALLTRIM()`, `UPPER()`, `SUBSTR()`, `TRANSFORM()`
     d. Oznacz: FULL (exact TAG match), PARTIAL (field match but function blocks), NONE (no TAG)
     e. Jeżeli PARTIAL/NONE — sugeruj indeks
2. Zwróć JSON z accessMap

---

## ZADANIE 4: vfp_count_patterns — statystyki wzorców

Dodaj subcommand `count_patterns` do vfp_driver.py:

```python
def run_count_patterns(project, patterns_str, out_file=None):
    """Count pattern occurrences across all .sc2 files in project cache.
    
    Patterns: comma-separated regex patterns
    Scans .vfp-ai cache or Audit_output/forms for .sc2 files.
    Returns per-form counts + totals + top forms.
    """
```

Argparse:
```python
pcp = sub.add_parser("count_patterns", help="Count pattern occurrences across forms")
pcp.add_argument("--project", required=True, help="Project root (with .vfp-ai cache)")
pcp.add_argument("--patterns", required=True, 
                 help="Comma-separated patterns: RLOCK,UNLOCK ALL,SET OPTIMIZE,...")
pcp.add_argument("--out", default=None)
```

Implementacja:
1. Znajdź wszystkie `.sc2` pliki w `<project>/.vfp-ai/` lub `<project>/Audit_output/forms/`
2. Dla każdego pliku zlicz wystąpienia każdego wzorca (regex case-insensitive)
3. Agreguj: total per pattern + top 5 forms per pattern
4. Zwróć JSON

---

## ZADANIE 5: vfp_find_duplicates — detekcja duplikatów kodu

Dodaj subcommand `find_duplicates` do vfp_driver.py:

```python
def run_find_duplicates(form_sc2, min_lines=10, out_file=None):
    """Find duplicate code blocks in a form.
    
    Parses PROCEDURE...ENDPROC blocks, normalizes (removes comments/whitespace),
    hashes them, and finds blocks with identical or similar content.
    """
```

Argparse:
```python
pfd = sub.add_parser("find_duplicates", help="Find duplicate code blocks in a form")
pfd.add_argument("--form", required=True, help="Path to .sc2 file")
pfd.add_argument("--min-lines", type=int, default=10, help="Minimum block size")
pfd.add_argument("--out", default=None)
```

Implementacja:
1. Parsuj `.sc2` — znajdź bloki `PROCEDURE ... ENDPROC`
2. Normalizuj: usuń komentarze (`*`, `&&`, `NOTE`), usuń whitespace, usuń nazwy zmiennych (zastąp `VAR`)
3. Dla bloków >= min_lines: oblicz hash (SHA256 normalized text)
4. Znajdź pary z identycznym hashem (100% similarity)
5. Dla podobnych (nie identycznych): użyj difflib.SequenceMatcher (similarity >= 80%)
6. Zwróć JSON: list of duplicate pairs with procedure names, line ranges, similarity

---

## ZADANIE 6: Aktualizacja tools/vfp.ts

Dodaj nowe narzędzia do `tools/vfp.ts`:

```typescript
// vfp_benchmark
export async function vfp_benchmark(params: {
  project: string;
  table: string;
  operation: string;
  expression?: string;
  field?: string;
  tag?: string;
  iterations?: number;
}): Promise<BenchmarkResult> { ... }

// vfp_form_perf
export async function vfp_form_perf(params: {
  form: string;
  tablesDir: string;
}): Promise<FormPerfResult> { ... }

// vfp_count_patterns
export async function vfp_count_patterns(params: {
  project: string;
  patterns: string;
}): Promise<PatternCounts> { ... }

// vfp_find_duplicates
export async function vfp_find_duplicates(params: {
  form: string;
  minLines?: number;
}): Promise<DuplicateResult> { ... }

// vfp_run_prg
export async function vfp_run_prg(params: {
  prg: string;
  workdir?: string;
  timeout?: number;
}): Promise<PrgRunResult> { ... }
```

---

## ZADANIE 7: Aktualizacja README.md i agents/vfp-analyst.md

### README.md:
- Dodaj sekcję "Performance Audit Tools" z opisem nowych subcommands
- Dodaj przykłady użycia

### agents/vfp-analyst.md:
- Dodaj sekcję "Performance Audit Workflow":
  1. `vfp_count_patterns` — zlicz wzorce w projekcie
  2. `vfp_form_perf` — zbuduj mapę dostępu dla formularza
  3. `vfp_benchmark` — zmierz krytyczne operacje BEFORE
  4. `vfp_find_duplicates` — zidentyfikuj duplikaty kodu
  5. Wykonaj refaktoryzację (ręcznie lub `vfp_modify_scx`)
  6. `vfp_benchmark` — zmierz AFTER
  7. Porównaj BEFORE/AFTER

---

## ZADANIE 8: Testy

Dodaj testy w `tests/`:

```python
# tests/test_benchmark.py
def test_benchmark_calculate_max():
    """Test benchmark with CALCULATE MAX operation"""

# tests/test_form_perf.py  
def test_form_perf_finds_seek_operations():
    """Test that form_perf finds SEEK operations in a form"""

def test_form_perf_rushmore_analysis():
    """Test Rushmore FULL/PARTIAL/NONE detection"""

# tests/test_count_patterns.py
def test_count_patterns_finds_rlock():
    """Test that RLOCK is counted correctly"""

# tests/test_find_duplicates.py
def test_find_duplicates_identical_blocks():
    """Test that identical PROCEDURE blocks are detected"""
```

---

## KOLEJNOŚĆ WYKONANIA

1. Utwórz branch `feature/performance-audit-tools`
2. Zaimplementuj ZADANIE 1 (vfp_run_prg) — to fundament dla ZADANIA 2
3. Zaimplementuj ZADANIE 2 (vfp_benchmark) — zależy od ZADANIA 1
4. Zaimplementuj ZADANIE 3 (vfp_form_perf) — niezależne
5. Zaimplementuj ZADANIE 4 (vfp_count_patterns) — niezależne
6. Zaimplementuj ZADANIE 5 (vfp_find_duplicates) — niezależne
7. Zaimplementuj ZADANIE 6 (tools/vfp.ts) — po ZADANIACH 1-5
8. Zaimplementuj ZADANIE 7 (docs) — po wszystkich
9. Zaimplementuj ZADANIE 8 (tests) — po wszystkich
10. Zrób commit po każdym zadaniu z message: `feat: add <function_name> subcommand`
11. Po wszystkich zadaniach: uruchom pełny test suite, sprawdź README

## WAŻNE ZASADY

- NIE modyfikuj istniejących funkcji (backward compatibility)
- NIE usuwaj istniejących narzędzi
- Każdy nowy subcommand musi być zgodny z protokołem JSON output
- Każdy nowy subcommand musi mieć --help w argparse
- Kod musi być Python 3.8+ compatible
- Używaj type hints tam gdzie możliwe
- Dodaj docstrings do wszystkich nowych funkcji
- Testy muszą przechodzić bez VFP9 zainstalowanego (mock lub skip)
```