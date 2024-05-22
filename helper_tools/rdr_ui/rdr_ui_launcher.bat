
@ECHO OFF
cls
set PYTHONDONTWRITEBYTECODE=1
REM   default is #ECHO OFF, cls (clear screen), and disable .pyc files
REM   for debugging REM @ECHO OFF line above to see commands
REM -------------------------------------------------


REM ==============================================
REM ======== ENVIRONMENT VARIABLES ===============
REM ==============================================
set PATH=C:\Users\%USERNAME%\Anaconda3\Scripts;%PATH%
set PYTHON="C:\Users\%USERNAME%\Anaconda3\envs\RDRenv\python.exe"
set UI="C:\GitHub\RDR\helper_tools\rdr_ui\ui.py"

call activate RDRenv
cd C:\GitHub\RDR\helper_tools\rdr_ui

REM =================================================
REM ================= START RDR UI ==================
REM =================================================

REM call user interface Python helper script
%PYTHON% %UI%
if %ERRORLEVEL% neq 0 goto ProcessError

call conda.bat deactivate
exit /b 0

:ProcessError
REM error handling: print message and clean up
echo ERROR: RDR UI encountered an error. See above messages (and log file) to diagnose.

call conda.bat deactivate
exit /b 1
