'---------------------------------------------------------------------------------------------------
' vfp_verno.vbs — returns the FoxBin2Prg version via the official COM host.
' Argument (0): full path of foxbin2prg.prg
' Prints exactly one line: VERNO=<version>   (or VERNO=unknown)
'---------------------------------------------------------------------------------------------------
Option Explicit
Dim oVFP9, cPrg, v, ErrN, ErrD
cPrg = WScript.Arguments(0)
Function q(p) : q = "'" & Replace(p, "'", "''") & "'" : End Function
Set oVFP9 = CreateObject("VisualFoxPro.Application.9")
oVFP9.DoCmd "SET PROCEDURE TO " & q(cPrg)
oVFP9.DoCmd "PUBLIC oV"
oVFP9.DoCmd "oV = CREATEOBJECT('c_foxbin2prg')"
oVFP9.DoCmd "PUBLIC cVerno"
oVFP9.DoCmd "cVerno = ''"
ErrN = 0 : ErrD = ""
On Error Resume Next
oVFP9.DoCmd "cVerno = oV.c_FB2PRG_EXE_Version"
v = oVFP9.Eval("cVerno")
If Err.Number <> 0 Then
  ErrN = Err.Number : ErrD = Err.Description : Err.Clear
End If
On Error GoTo 0
oVFP9.DoCmd "oV = NULL"
oVFP9.DoCmd "cVerno = NULL"
oVFP9.DoCmd "CLEAR ALL"
On Error Resume Next
oVFP9.Quit
On Error GoTo 0
Set oVFP9 = Nothing
If ErrN <> 0 Then
  WScript.Echo "VERNO=unknown  (error " & ErrN & ": " & ErrD & ")"
ElseIf Len(v) = 0 Then
  WScript.Echo "VERNO=unknown"
Else
  WScript.Echo "VERNO=" & v
End If
WScript.Quit 0
