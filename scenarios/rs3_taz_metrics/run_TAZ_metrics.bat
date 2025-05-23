
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
set TAZ_METRICS_HELPER="C:\GitHub\RDR\helper_tools\benefits_analysis\TAZ_metrics.py"

set CONFIG="C:\GitHub\RDR\scenarios\rs3_taz_metrics\RS3_TAZ_metrics.config"

call activate RDRenv
cd C:\GitHub\RDR\helper_tools\benefits_analysis

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
