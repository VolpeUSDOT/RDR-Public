
@ECHO OFF
cls
set PYTHONDONTWRITEBYTECODE=1
REM   default is #ECHO OFF, cls (clear screen), and disable .pyc files
REM   for debugging REM @ECHO OFF line above to see commands
REM -------------------------------------------------


REM ==============================================
REM ======== ENVIRONMENT VARIABLES ===============
REM ==============================================
set batdir=%~dp0
for %%A in ("%batdir%") do set TESTPATH=%%~dpA
for %%A in ("%TESTPATH%\..\..\..\") do set RDRBASE=%%~dpA
set HELPERPATH=%RDRBASE%helper_tools\benefits_analysis\

set TAZ_METRICS_HELPER=%HELPERPATH%TAZ_metrics.py

set CONFIG="%TESTPATH%RS3_TAZ_metrics.config"

call activate RDRenv

cd %HELPERPATH%

REM =================================================
REM ======== RUN THE TAZ METRICS HELPER TOOL ========
REM =================================================

REM call TAZ Metrics Python helper script
%PYTHON% %TAZ_METRICS_HELPER% %CONFIG%
if %ERRORLEVEL% neq 0 goto ProcessError

call conda.bat deactivate
pause
exit /b 0

:ProcessError
REM error handling: print message and clean up
echo ERROR: TAZ metrics helper tool run encountered an error. See above messages (and log file) to diagnose.

call conda.bat deactivate
pause
exit /b 1
