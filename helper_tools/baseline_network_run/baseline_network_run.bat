
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
set BASELINE_NETWORK_HELPER="C:\GitHub\RDR\helper_tools\baseline_network_run\baseline_network_run.py"

set CONFIG="C:\GitHub\RDR\scenarios\qs1_sioux_falls\QS1.config"

call activate RDRenv


REM ==============================================
REM ======== RUN THE BASELINE NETWORK HELPER TOOL ==================
REM ==============================================

REM call baseline network run Python helper script
%PYTHON% %BASELINE_NETWORK_HELPER% %CONFIG%
if %ERRORLEVEL% neq 0 goto ProcessError

call conda.bat deactivate
pause
exit /b 0

:ProcessError
REM error handling: print message and clean up
echo ERROR: Baseline network helper tool run encountered an error. See above messages (and log file) to diagnose.

call conda.bat deactivate
pause
exit /b 1
