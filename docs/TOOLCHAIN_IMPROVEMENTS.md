# Rekomendacje ulepszeń vfp-integration-toolchain

## Kontekst

Po przeprowadzeniu 3 pełnych sesji refaktoryzacji formularzy VFP9 (`karty_meteo`, `karty_pr`, `karty_pr_pp` — łącznie ~9000 linii kodu w 400+ procedurach) zidentyfikowano następujące luki w obecnym toolchainie, które utrudniają lub uniemożliwiają automatyzację audytu wydajnościowego i refaktoryzacji.

---

## A. NOWE FUNKCJE DO DODANIA

### A1. `vfp_benchmark` — pomiar czasu operacji dostępu do danych

**Problem:** Audyt wydajnościowy wymaga pomiarów BEFORE/AFTER. Obecnie trzeba pisać własne skrypty `.prg` i uruchamiać je przez VFP9 ręcznie.

**Rozwiązanie:** Nowy subcommand `benchmark` w `vfp_driver.py`:

```
vfp_benchmark --project <root> --table <alias> --operation <name> --iterations N --out <file>
```

**Operacje do wbudowania:**
- `calculate_max` — CALCULATE MAX(field) [FOR condition]
- `calculate_for` — CALCULATE ... FOR wyrażenie (test Rushmore)
- `seek` — SEEK na wskazanym TAG
- `scan` — SCAN [FOR condition]
- `count_for` — COUNT FOR condition
- `sum` — SUM field [FOR condition]
- `set_filter_goto` — SET FILTER + GO TOP
- `sys3054` — zwraca status Rushmore dla wyrażenia

**Wyjście JSON:**
```json
{
  "operation": "calculate_for",
  "table": "ksiazka_k_d",
  "iterations": 10,
  "coldMs": 45.2,
  "warmMs": 21.4,
  "avgMs": 21.4,
  "minMs": 20.8,
  "maxMs": 22.1,
  "rushmore": "PARTIAL",
  "sys3054": "1"
}
```

**Implementacja:** Generuje `.prg` z pomiarem `SECONDS()`, uruchamia przez VFP9 COM (jak `vfp_verno.vbs`), parsuje wynik.

---

### A2. `vfp_rushmore_check` — analiza Rushmore dla wyrażenia

**Problem:** `SYS(3054)` wymaga uruchomienia w VFP9. Nie można sprawdzić offline czy `LEFT(k_pr_sp_nr,10)` jest zoptymalizowane.

**Rozwiązanie:** Nowy subcommand `rushmore`:

```
vfp_rushmore --table <dbf> --expression "LEFT(k_pr_sp_nr,10)='ABC'" --out <file>
```

**Działanie:**
1. Otwiera tabelę w VFP9 (COM)
2. Wykonuje `SYS(3054, 1, expression)`
3. Zwraca: FULL / PARTIAL / NONE + listę użytych TAGów + brakujące TAGi
4. Sugeruje indeks: jeżeli wyrażenie zawiera `LEFT(field,N)`, proponuje `INDEX ON LEFT(field,N) TAG ...`

**Wyjście JSON:**
```json
{
  "expression": "LEFT(k_pr_sp_nr,10)='ABC'",
  "rushmore": "PARTIAL",
  "usedTags": ["K_PR_SP_NR (partial prefix)"],
  "missingTags": ["LEFT(k_pr_sp_nr,10)"],
  "suggestedIndex": "INDEX ON LEFT(k_pr_sp_nr,10) TAG kprsp10"
}
```

---

### A3. `vfp_analyze_form_performance` — mapa dostępu do danych formularza

**Problem:** Obecnie `vfp_audit` eksportuje formy i schemy, ale nie łączy ich w mapę: FORMULARZ → METODA → TABELA → OPERACJA → INDEKS → RUSHMORE.

**Rozwiązanie:** Nowy subcommand `form_perf`:

```
vfp_form_perf --form <scx> --tables-dir <dane> --out <file>
```

**Działanie:**
1. Parsuje `.sc2` formularza (jak `vfp_indexer`)
2. Dla każdej procedury szuka: `SEEK`, `SCAN FOR`, `CALCULATE FOR`, `COUNT FOR`, `SUM FOR`, `LOCATE FOR`, `SET FILTER`, `DELETE ALL FOR`, `REPLACE FOR`
3. Dla każdego znalezionego wyrażenia `FOR`:
   - Identyfikuje tabelę (z kontekstu `SELECT alias`)
   - Sprawdza CDX (z `vfp_cdx`)
   - Szuka pasującego TAGu
   - Oznacza: RUSHMORE FULL / PARTIAL / NONE
4. Generuje mapę JSON + Markdown

**Wyjście JSON:**
```json
{
  "form": "karty_pr_pp",
  "accessMap": [
    {
      "procedure": "Text4.LostFocus",
      "operation": "CALCULATE MAX(VAL(nr_dr)) FOR LEFT(k_pr_sp_nr,10)=...",
      "table": "ksiazka_k_d",
      "records": 189984,
      "existingTag": "K_PR_SP_NR",
      "tagExpression": "K_PR_SP_NR",
      "rushmore": "PARTIAL",
      "reason": "LEFT() function blocks full TAG match",
      "suggestedIndex": "INDEX ON LEFT(k_pr_sp_nr,10)+indeks+nr_dr TAG nr_dr_idx",
      "frequency": "low (per podpis pracownika)",
      "severity": "medium"
    }
  ]
}
```

---

### A4. `vfp_modify_scx` — modyfikacja METHODS w formularzu (write)

**Problem:** Toolchain jest strict read-only. Refaktoryzacja wymaga modyfikacji `.scx` — obecnie trzeba pisać własne skrypty `.prg` z `USE ... AS TABLE` + `REPLACE METHODS`.

**Rozwiązanie:** Nowy subcommand `modify_scx` (z显nym oznaczeniem jako WRITE):

```
vfp_modify_scx --scx <file> --objname "Form1" --methods-file <methods.prg> --backup
```

**Działanie:**
1. Kopiuje `.scx`/`.sct` do backup (SHA256 zapisany)
2. Otwiera `.scx` jako tabelę (USE ... EXCLUSIVE)
3. `LOCATE FOR OBJNAME = tcObjname`
4. `REPLACE METHODS WITH <z pliku>`
5. Zamyka, weryfikuje (otwarcie w VFP9, DO FORM)
6. Zwraca: przed/po SHA256, liczba zmienionych rekordów

**Bezpieczeństwo:**
- Wymaga `--backup` (zawsze tworzy kopię)
- Wymaga `--confirm` (nie uruchamia bez potwierdzenia)
- Zapisuje log zmian: `modify_log.json` z timestamp, SHA256 before/after, diff METHODS

---

### A5. `vfp_find_duplicates` — detekcja zduplikowanych bloków kodu

**Problem:** Refaktoryzacja głównie polega na eliminacji duplikacji. Obecnie trzeba ręcznie szukać w `.sc2`.

**Rozwiązanie:** Nowy subcommand `find_duplicates`:

```
vfp_find_duplicates --form <sc2> --min-lines 10 --out <file>
```

**Działanie:**
1. Parsuje `.sc2` i dzieli na bloki `PROCEDURE ... ENDPROC`
2. Normalizuje ( usuwa komentarze, whitespace)
3. Haszuje bloki (SHA256 lub simhash)
4. Znajduje bloki o identycznych/zbliżonych hashach
5. Zwraca listę duplikatów z linii i procentem podobieństwa

**Wyjście JSON:**
```json
{
  "form": "karty_pr_pp",
  "duplicates": [
    {
      "block1": "Check1.GotFocus (lines 3366-3387)",
      "block2": "CheckOST.GotFocus (lines 3521-3536)",
      "similarity": 100,
      "lines": 18,
      "suggestion": "Extract to BlokadaTrzyTabele() method"
    }
  ]
}
```

---

### A6. `vfp_count_patterns` — statystyki wzorców w całym projekcie

**Problem:** Analiza projektu wymaga zliczenia wzorców (RLOCK, UNLOCK ALL, SET FILTER, SET OPTIMIZE, etc.) we wszystkich formularzach. Obecnie trzeba pisać własny skrypt Python.

**Rozwiązanie:** Nowy subcommand `count_patterns`:

```
vfp_count_patterns --project <root> --patterns "RLOCK,UNLOCK ALL,SET OPTIMIZE,SET MULTILOCKS,CURSORSETPROP,TABLEUPDATE,FLUSH,SYS(1104),SET RELATION,SET FILTER" --out <file>
```

**Działanie:**
1. Skanuje wszystkie `.sc2` w `.vfp-ai` cache
2. Zlicza wystąpienia każdego wzorca
3. Zwraca per-form i total

**Wyjście JSON:**
```json
{
  "totalForms": 834,
  "patterns": {
    "RLOCK": {"total": 620, "topForms": [{"form": "karty_pr_pp", "count": 101}, ...]},
    "UNLOCK_ALL": {"total": 464, "topForms": [{"form": "karty_pr_pp", "count": 47}, ...]},
    "SET_OPTIMIZE": {"total": 0, "topForms": []}
  }
}
```

---

## B. FUNKCJE DO MODYFIKACJI

### B1. `vfp_cdx` — dodaj weryfikację zgodności FOR z TAG

**Obecnie:** `vfp_cdx` zwraca listę TAGów z nazwami i wyrażeniami.

**Zmiana:** Dodaj funkcję `match_tag_to_expression(tag_expr, for_expr)`:
- Sprawdza czy wyrażenie `FOR` pasuje do wyrażenia `TAG`
- Wykrywa funkcje blokujące Rushmore: `LEFT()`, `RIGHT()`, `ALLTRIM()`, `UPPER()`, `SUBSTR()`, `DTOC()`, `TRANSFORM()`
- Zwraca: `FULL` / `PARTIAL` / `NONE` + powód

**Użycie w `vfp_form_perf` (A3):** automatyczna analiza Rushmore bez uruchamiania VFP9.

---

### B2. `vfp_audit` — dodaj sekcję "Performance Audit"

**Obecnie:** `vfp_audit` generuje: schema, relationships, classes, forms.

**Zmiana:** Dodaj `performance_audit.json` z:
- Liczba RLOCK/UNLOCK ALL per form
- Liczba SET FILTER / SET OPTIMIZE / SET MULTILOCKS per form
- Liczba CALCULATE FOR / SCAN FOR / COUNT FOR per form
- Tabele z >10k rekordów bez indeksów na polach używanych w FOR
- Lista operacji z `LEFT()`/`ALLTRIM()` w FOR (potencjalne PARTIAL Rushmore)

---

### B3. `vfp_driver` — dodaj subcommand `run_prg`

**Obecnie:** Nie ma możliwości uruchomić dowolnego skryptu `.prg` w VFP9 przez toolchain.

**Zmiana:**
```
vfp_run_prg --prg <file.prg> --workdir <dir> --timeout 120 --out <logfile>
```

**Działanie:** Uruchamia `vfp9.exe -c <prg>` z przekierowaniem stdout/stderr do logu.

**Uzasadnienie:** Benchmarking, modyfikacja SCX, audyt Rushmore — wszystkie wymagają uruchomienia VFP9. Obecnie każda z tych operacji wymaga ręcznego `Start-Process` w PowerShell.

---

### B4. `tools/vfp.ts` — dodaj narzędzia dla nowych subcommands

**Obecnie:** 15 narzędzi (vfp_detect, vfp_status, vfp_export_*, vfp_audit, etc.)

**Zmiana:** Dodaj:
- `vfp_benchmark` — pomiar operacji
- `vfp_rushmore` — analiza Rushmore
- `vfp_form_perf` — mapa wydajności formularza
- `vfp_modify_scx` — modyfikacja METHODS (WRITE)
- `vfp_find_duplicates` — detekcja duplikatów
- `vfp_count_patterns` — statystyki wzorców
- `vfp_run_prg` — uruchomienie PRG w VFP9

---

### B5. `agents/vfp-analyst.md` — dodaj sekcję "Performance Audit Workflow"

**Obecnie:** Agent opisuje workflow analizy strukturalnej.

**Zmiana:** Dodaj sekcję:
1. `vfp_count_patterns` — zlicz wzorce w projekcie
2. `vfp_form_perf` — zbuduj mapę dostępu dla formularza
3. `vfp_benchmark` — zmierz krytyczne operacje BEFORE
4. `vfp_rushmore` — sprawdź Rushmore dla PARTIAL operacji
5. `vfp_find_duplicates` — zidentyfikuj duplikaty kodu
6. Wykonaj refaktoryzację (`vfp_modify_scx`)
7. `vfp_benchmark` — zmierz AFTER
8. Porównaj BEFORE/AFTER

---

## C. PRIORYTETY IMPLEMENTACJI

| Priorytet | Funkcja | Wpływ na refaktoryzację | Trudność |
|-----------|---------|------------------------|----------|
| 1 | `vfp_run_prg` | Wszystkie pomiary wymagają VFP9 | Niska |
| 2 | `vfp_benchmark` | Pomiar BEFORE/AFTER to podstawa | Średnia |
| 3 | `vfp_form_perf` | Automatyczna mapa FORM→DBF→INDEX | Średnia |
| 4 | `vfp_count_patterns` | Statystyki projektu w 1 komendzie | Niska |
| 5 | `vfp_rushmore` | Analiza Rushmore offline | Średnia |
| 6 | `vfp_find_duplicates` | Automatyczna detekcja duplikatów | Wysoka |
| 7 | `vfp_modify_scx` | Modyfikacja SCX przez toolchain | Średnia |
| 8 | `vfp_cdx` match_tag | Łączenie FOR z TAG offline | Średnia |
| 9 | `vfp_audit` perf section | Perf audit w głównym audycie | Niska |
| 10 | `tools/vfp.ts` new tools | Integracja z OpenCode | Niska |