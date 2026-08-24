'---------------------------------------------------------------------------------------------------
' vfp_cdx_enrich.vbs — STRICT READ-ONLY: reads the index tag EXPRESSIONS of a
' DBF table through the VFP9 COM host (SYST(325) after SET INDEX TO).
'
' Arguments (discrete WScript.Arguments — no shell interpolation):
'   (0) dbfPath    full path of the .dbf whose structural index to describe
'   (1) outDir     scratch cwd for the process (keeps any side-effect away
'                  from the source tree; nothing is ever written there)
'
' Output: one line per tag, tab-separated:
'   TAG <TAB> <tag name> <TAB> <index expression> <TAB> OK|ERR:<n>
' and a final line:
'   DONE <TAB> <ok count> <TAB> <err count>
'
' SAFETY:
'   - SET SYS(2023,0)  no .ERR files on VFP errors
'   - SET SYS(1486,0)  no auto .fpt/.cdx rebuild
'   - table opened in a scratch alias, SHARED (non-exclusive) mode,
'     closed with CLOSE ALL before the host quits. No writes, no DDL,
'     no PRG2BIN anywhere.
'---------------------------------------------------------------------------------------------------
Option Explicit
Dim fso, oVFP9, cDbf, cOut
cDbf = WScript.Arguments(0)
cOut = ""
If WScript.Arguments.Count > 1 Then cOut = WScript.Arguments(1)
Set fso = CreateObject("Scripting.FileSystemObject")
If Len(cOut) > 0 Then
  If Not fso.FolderExists(cOut) Then
    On Error Resume Next
    fso.CreateFolder cOut
    On Error GoTo 0
  End If
End If

Function q(p) : q = "'" & Replace(p, "'", "''") & "'" : End Function
Function tab() : tab = Chr(9) : End Function

WScript.Echo "starting VisualFoxPro.Application.9 ..."
Set oVFP9 = CreateObject("VisualFoxPro.Application.9")
On Error Resume Next
oVFP9.DoCmd "SET TALK OFF"
oVFP9.DoCmd "SET SAFE OFF"
oVFP9.DoCmd "SET SYS(2023, 0)"
oVFP9.DoCmd "SET SYS(1486, 0)"
oVFP9.DoCmd "SET EXCLUSIVE OFF"
On Error GoTo 0

Dim lcAlias
lcAlias = "vfpai_cdxtmp"
If oVFP9.Eval("ALIAS(" & lcAlias & ")") <> "" Then
  oVFP9.DoCmd "USE " & lcAlias & " IN 0"
End If

Dim okN, errN
okN = 0 : errN = 0
On Error Resume Next
oVFP9.DoCmd "USE " & q(cDbf) & " NEW ALIAS " & lcAlias
Dim opened
opened = (Err.Number = 0)
If Err.Number <> 0 Then Err.Clear
If Not opened Then
  WScript.Echo "TAG" & tab() & "(table-not-opened)" & tab() & tab() & "ERR"
  WScript.Echo "DONE" & tab() & "0" & tab() & "1"
  On Error GoTo 0
  oVFP9.DoCmd "CLEAR ALL"
  oVFP9.Quit
  Set oVFP9 = Nothing
  WScript.Quit 1
End If

Dim n, cTag, cExpr
n = 1
Do
  cTag = oVFP9.Eval("_GETTAG(" & n & ", '" & lcAlias & "')")
  If Err.Number <> 0 Then Err.Clear : cTag = ""
  If Len(cTag) = 0 Then Exit Do
  On Error Resume Next
  oVFP9.DoCmd "SET INDEX TO " & lcAlias & "." & cTag
  Dim setOk
  setOk = (Err.Number = 0)
  If Err.Number <> 0 Then Err.Clear
  cExpr = ""
  If setOk Then
    cExpr = oVFP9.Eval("TRIM(SYST(325))")
    If Err.Number <> 0 Then Err.Clear : cExpr = ""
  End If
  ' sanitize tabs inside the expression (never expected, defensive)
  cExpr = Replace(cExpr, Chr(9), " ")
  If setOk Then
    WScript.Echo "TAG" & tab() & cTag & tab() & cExpr & tab() & "OK"
    okN = okN + 1
  Else
    WScript.Echo "TAG" & tab() & cTag & tab() & tab() & "ERR"
    errN = errN + 1
  End If
  On Error GoTo 0
  n = n + 1
Loop

On Error Resume Next
oVFP9.DoCmd "SET INDEX TO "
oVFP9.DoCmd "USE " & lcAlias & " IN 0"
oVFP9.DoCmd "CLEAR ALL"
oVFP9.Quit
On Error GoTo 0
Set oVFP9 = Nothing
WScript.Echo "DONE" & tab() & okN & tab() & errN
WScript.Quit 0
