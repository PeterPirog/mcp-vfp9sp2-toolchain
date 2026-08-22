'---------------------------------------------------------------------------------------------------
' vfp_convert.vbs — STRICT READ-ONLY BIN2PRG driver for the OpenCode VFP toolchain.
'
' Mechanism: identical to the official upstream helper Convert_VFP9_BIN_2_PRG.vbs
' (fdbozzo/foxbin2prg). There is no standalone FoxBin2Prg.exe in the upstream repo;
' the only official runtime is the VFP9 COM host driving the c_foxbin2prg object.
'
' Arguments (each a DISCRETE WScript.Argument — no shell string interpolation):
'   (0) inputFile      full path of the .scx/.vcx/.frx/.mnx/.lbx/.pjx/.dbc/.dbf to convert,
'                      OR "lib.vcx::ClassName" for class-per-file extraction
'   (1) cType          BIN2PRG (default) | *  (whole project, incl. pjx) | -*- (project excl. pjx)
'   (2) outputFolder   folder to receive the generated text (keeps relative structure)
'   (3) cfgFile        FoxBin2Prg-AI.cfg path (read-only AI profile)
'   (4) prgPath        full path of foxbin2prg.prg
'
' Return value (VBS host exit code = FoxBin2Prg execute() return): 0=OK, 1=Error, 41=missing .sct ...
' A machine-parseable line "RC=<n>" is always printed to stdout.
'
' SAFETY: this script only ever issues cType=BIN2PRG/* (Text generation). It never calls PRG2BIN.
'---------------------------------------------------------------------------------------------------
Option Explicit
Dim WshShell, fso, oVFP9
Set WshShell = CreateObject("WScript.Shell")
Set fso      = CreateObject("Scripting.FileSystemObject")

Dim cIn, cType, cOut, cCfg, cPrg, rc
cIn   = WScript.Arguments(0)
cType = "BIN2PRG"
cOut  = ""
cCfg  = ""
cPrg  = ""
If WScript.Arguments.Count > 1 Then cType = WScript.Arguments(1)
If WScript.Arguments.Count > 2 Then cOut  = WScript.Arguments(2)
If WScript.Arguments.Count > 3 Then cCfg  = WScript.Arguments(3)
If WScript.Arguments.Count > 4 Then cPrg  = WScript.Arguments(4)

' Quote single-quotes defensively in paths (VFP string literal)
Function q(p) : q = "'" & Replace(p, "'", "''") & "'" : End Function

' Hard safety gate (WHITELIST): only the TEXT-generation directions are permitted.
If Not (cType = "BIN2PRG" Or cType = "*" Or cType = "*-*") Then
  WScript.Echo "RC=-1"
  WScript.Echo "ABORTED: only BIN2PRG / * / -*- are permitted (strict read-only). Got: " & cType
  WScript.Quit 1
End If
If InStr(1, UCase(cType), "PRG2BIN") > 0 Then
  WScript.Echo "RC=-1"
  WScript.Echo "ABORTED: PRG2BIN is not permitted in read-only AI mode"
  WScript.Quit 1
End If

' Ensure output directory exists (Strtofile fails silently on missing dir → RC=1)
If Len(cOut) > 0 Then
  If Not fso.FolderExists(cOut) Then
    On Error Resume Next
    fso.CreateFolder cOut
    On Error GoTo 0
  End If
  If Not fso.FolderExists(cOut) Then
    WScript.Echo "RC=-1"
    WScript.Echo "ABORTED: cannot create output directory: " & cOut
    WScript.Quit 1
  End If
End If

WScript.Echo "FB2PRG-DRIVER start in=" & cIn & " type=" & cType
WScript.Echo "starting VisualFoxPro.Application.9 ..."
Set oVFP9 = CreateObject("VisualFoxPro.Application.9")
WScript.Echo "COM created"

oVFP9.DoCmd "SET PROCEDURE TO " & q(cPrg)
oVFP9.DoCmd "PUBLIC oFb"
oVFP9.DoCmd "oFb = CREATEOBJECT('c_foxbin2prg')"
If Len(cOut) > 0 Then
  oVFP9.DoCmd "oFb.cOutputFolder = " & q(cOut)
  WScript.Echo "cOutputFolder set to [" & oVFP9.Eval("oFb.cOutputFolder") & "]"
End If
If Len(cCfg) > 0 Then
  WScript.Echo "cfgFile = [" & cCfg & "]"
End If

' Build execute() with all 17 parameters (read-only AI profile defaults)
Dim cmd
cmd = "rc = oFb.execute("
cmd = cmd & q(cIn)                          '  1 tcInputFile
cmd = cmd & ",'" & cType & "'"              '  2 tcType
cmd = cmd & ",''"                           '  3 tcTextName
cmd = cmd & ",.F."                          '  4 tlGenText
cmd = cmd & ",'1'"                          '  5 tcDontShowErrors
cmd = cmd & ",'0'"                          '  6 tcDebug
cmd = cmd & ",'1'"                          '  7 tcDontShowProgress
cmd = cmd & ",''"                           '  8 toModule
cmd = cmd & ",''"                           '  9 toEx
cmd = cmd & ",.F."                          ' 10 tlRelanzarError
cmd = cmd & ",''"                           ' 11 tcOriginalFileName
cmd = cmd & ",'0'"                          ' 12 tcRecompile (keep .PRG source intact)
cmd = cmd & ",'1'"                          ' 13 tcNoTimestamps
cmd = cmd & ",'0'"                          ' 14 tcBackupLevels
cmd = cmd & ",'1'"                          ' 15 tcClearUniqueID
cmd = cmd & ",'0'"                          ' 16 tcOptimizeByFilestamp
cmd = cmd & "," & q(cCfg)                   ' 17 tcCFG_File
cmd = cmd & ")"
WScript.Echo "calling execute ..."
WScript.Echo "VFP CMD: " & cmd
oVFP9.DoCmd cmd
rc = oVFP9.Eval("rc")
WScript.Echo "RC=" & rc
WScript.Echo "l_Error=" & oVFP9.Eval("oFb.l_Error")
WScript.Echo "l_Errors=" & oVFP9.Eval("oFb.l_Errors")
oVFP9.DoCmd "oFb = NULL"
oVFP9.DoCmd "CLEAR ALL"
On Error Resume Next
oVFP9.Quit
On Error GoTo 0
Set oVFP9 = Nothing
WScript.Quit CInt(rc)
