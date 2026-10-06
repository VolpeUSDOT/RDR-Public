@ECHO OFF
cls
set PYTHONDONTWRITEBYTECODE=1
REM   default is #ECHO OFF, cls (clear screen), and disable .pyc files
REM   for debugging REM @ECHO OFF line above to see commands
REM -------------------------------------------------


REM ==============================================
REM ======== ENVIRONMENT VARIABLES ===============
REM ==============================================
IF EXIST "C:/Users/%USERNAME%/AppData/Local/anaconda3/Scripts/" (
	set "PATH=C:/Users/%USERNAME%/AppData/Local/anaconda3/Scripts;%PATH%"
) ELSE IF EXIST "C:/Users/%USERNAME%/Anaconda3/Scripts/" (
	set "PATH=C:/Users/%USERNAME%/Anaconda3/Scripts;%PATH%"
) ELSE IF EXIST "C:/Users/%USERNAME%/.conda/Scripts/" (
	set "PATH=C:/Users/%USERNAME%/.conda/Scripts;%PATH%"
) ELSE IF EXIST "C:/Users/%USERNAME%/AppData/Local/.conda/Scripts/" (
	set "PATH=C:/Users/%USERNAME%/AppData/Local/.conda/Scripts;%PATH%"
) ELSE (
	REM ERROR: Could not find Anaconda install location. See documentation for guidance.
	goto ProcessError
)

set UI="C:\GitHub\RDR\gui\Main_Menu.py"

call activate RDRenv
cd C:\GitHub\RDR\gui

REM =================================================
REM ================= START RDR UI ==================
REM =================================================

REM call user interface Python helper script
streamlit run %UI%

if %ERRORLEVEL% neq 0 goto ProcessError

call conda.bat deactivate
exit /b 0

:ProcessError
REM error handling: print message and clean up
echo ERROR: RDR UI encountered an error. See above messages (and log file) to diagnose.

call conda.bat deactivate
exit /b 1
