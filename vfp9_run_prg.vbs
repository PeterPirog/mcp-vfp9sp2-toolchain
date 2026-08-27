'---------------------------------------------------------------------------------------------------
' vfp9_run_prg.vbs - minimal VFP9 COM host: run ONE toolchain-generated PRG.
'
' Arguments (discrete WScript.Arguments - no shell interpolation):
'   (0) prgPath  full path of the .prg to execute
'
' Output protocol (stdout, machine-parseable):
'   RC=<n>            0 = OK (PRG ran to completion), 1 = VFP runtime error
'                     inside the PRG, 2 = COM/host failure, 3 = timeout/kill
'
' SAFETY (v0.3):
'   - runs exactly one PRG supplied by the toolchain (template-generated);
'   - the toolchain owns this child process (PID-scoped timeout handling in
'     vfp_protocol.run_process). If the COM host outlives the client, the
'     toolchain does NOT kill arbitrary vfp9.exe instances — it reports
'     VFP9_TIMEOUT with manual-diagnostics instructions;
'   - SET SYS(2023,0) prevents .ERR file creation by VFP on errors;
'   - SET SYS(1486,0) prevents auto .fpt/.cdx rebuilds next to any table;
'   - the PRG's cwd is set by the caller (always the workspace).
'---------------------------------------------------------------------------------------------------
Option Explicit
Dim fso, oVFP9, cPrg
cPrg = WScript.Arguments(0)
Set fso = CreateObject("Scripting.FileSystemObject")

Function q(p) : q = "'" & Replace(p, "'", "''") : End Function

WScript.Echo "starting VisualFoxPro.Application.9 ..."
On Error Resume Next
Set oVFP9 = CreateObject("VisualFoxPro.Application.9")
If Err.Number <> 0 Then
  WScript.Echo "RC=2"
  WScript.Echo "VFP9 COM host unavailable: " & Err.Number & " " & Err.Description
  Err.Clear
  WScript.Quit 2
End If
On Error GoTo 0

On Error Resume Next
oVFP9.DoCmd "SET TALK OFF"
oVFP9.DoCmd "SET SAFE OFF"
oVFP9.DoCmd "SET ESCAPE OFF"
oVFP9.DoCmd "SET SYS(2023, 0)"
oVFP9.DoCmd "SET SYS(1486, 0)"
On Error GoTo 0

' Run the PRG. A VFP runtime error aborts DoCmd and raises a host error.
On Error Resume Next
oVFP9.DoCmd "DO " & q(cPrg)
Dim rc
If Err.Number <> 0 Then
  rc = 1
  WScript.Echo "PRG_ERROR=" & Err.Number & " " & Err.Description
  Err.Clear
Else
  rc = 0
End If
On Error GoTo 0

' Cleanup (best-effort; never kill other VFP9 instances).
On Error Resume Next
oVFP9.DoCmd "SET TALK ON"
oVFP9.DoCmd "SET SAFE ON"
oVFP9.DoCmd "SET ESCAPE ON"
oVFP9.DoCmd "CLEAR ALL"
oVFP9.Quit
On Error GoTo 0
Set oVFP9 = Nothing

WScript.Echo "RC=" & rc
WScript.Quit rc
