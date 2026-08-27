* extract_vfp9sp2_runtime_inventory.prg
* Run inside the exact Microsoft Visual FoxPro 9 SP2 installation used by the project.

LPARAMETERS tcOutputFile

LOCAL lcOut, lcCRLF, lnI, lnCount, lcClass
LOCAL ARRAY laCommands[1]
LOCAL ARRAY laFunctions[1,2]
LOCAL ARRAY laClasses[1]
LOCAL ARRAY laDbcEvents[1]
LOCAL ARRAY laMembers[1,2]

lcCRLF = CHR(13) + CHR(10)

IF VARTYPE(tcOutputFile) # "C" OR EMPTY(tcOutputFile)
    lcOut = FULLPATH("vfp9sp2_runtime_inventory.txt")
ELSE
    lcOut = FULLPATH(tcOutputFile)
ENDIF

IF FILE(lcOut)
    ERASE (lcOut)
ENDIF

=STRTOFILE("[ENV]" + lcCRLF, lcOut, .F.)
=STRTOFILE("VERSION=" + VERSION() + lcCRLF, lcOut, .T.)
=STRTOFILE("VERSION1=" + VERSION(1) + lcCRLF, lcOut, .T.)
=STRTOFILE("VERSION5=" + TRANSFORM(VERSION(5)) + lcCRLF, lcOut, .T.)
=STRTOFILE("ENGINEBEHAVIOR=" + TRANSFORM(SYS(3099)) + lcCRLF, lcOut, .T.)
=STRTOFILE("CPCURRENT=" + TRANSFORM(CPCURRENT()) + lcCRLF, lcOut, .T.)
=STRTOFILE("SET_EXACT=" + SET("EXACT") + lcCRLF, lcOut, .T.)
=STRTOFILE("SET_ANSI=" + SET("ANSI") + lcCRLF, lcOut, .T.)
=STRTOFILE("SET_DELETED=" + SET("DELETED") + lcCRLF, lcOut, .T.)
=STRTOFILE("SET_EXCLUSIVE=" + SET("EXCLUSIVE") + lcCRLF, lcOut, .T.)
=STRTOFILE(lcCRLF, lcOut, .T.)

lnCount = ALANGUAGE(laCommands, 1)
=STRTOFILE("[COMMANDS]" + lcCRLF, lcOut, .T.)
FOR lnI = 1 TO lnCount
    =STRTOFILE(laCommands[lnI] + lcCRLF, lcOut, .T.)
ENDFOR

lnCount = ALANGUAGE(laFunctions, 2)
=STRTOFILE(lcCRLF + "[FUNCTIONS]" + lcCRLF, lcOut, .T.)
FOR lnI = 1 TO lnCount
    =STRTOFILE(laFunctions[lnI,1] + "|" + TRANSFORM(laFunctions[lnI,2]) + lcCRLF, lcOut, .T.)
ENDFOR

lnCount = ALANGUAGE(laClasses, 3)
=STRTOFILE(lcCRLF + "[BASE_CLASSES]" + lcCRLF, lcOut, .T.)
FOR lnI = 1 TO lnCount
    =STRTOFILE(laClasses[lnI] + lcCRLF, lcOut, .T.)
ENDFOR

lnCount = ALANGUAGE(laDbcEvents, 4)
=STRTOFILE(lcCRLF + "[DBC_EVENTS]" + lcCRLF, lcOut, .T.)
FOR lnI = 1 TO lnCount
    =STRTOFILE(laDbcEvents[lnI] + lcCRLF, lcOut, .T.)
ENDFOR

=STRTOFILE(lcCRLF + "[PEM]" + lcCRLF, lcOut, .T.)
lnCount = ALANGUAGE(laClasses, 3)
FOR lnI = 1 TO lnCount
    lcClass = laClasses[lnI]
    LOCAL lnMember, lnMemberCount
    lnMemberCount = 0
    ON ERROR lnMemberCount = 0
    lnMemberCount = AMEMBERS(laMembers, lcClass, 1)
    ON ERROR
    FOR lnMember = 1 TO lnMemberCount
        =STRTOFILE("MEMBER|" + lcClass + "|" + ;
            TRANSFORM(laMembers[lnMember,1]) + "|" + ;
            TRANSFORM(laMembers[lnMember,2]) + lcCRLF, lcOut, .T.)
    ENDFOR
ENDFOR

=STRTOFILE(lcCRLF + "[END]" + lcCRLF, lcOut, .T.)
? "Created:", lcOut
RETURN lcOut
