
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
set BASE_YEAR_HELPER="C:\GitHub\RDR\helper_tools\base_year_run\base_year_run.py"

set CONFIG="C:\GitHub\RDR\scenarios\qs1_sioux_falls\QS1.config"

call activate RDRenv


REM ==============================================
REM ======== RUN THE BASE YEAR HELPER TOOL ==================
REM ==============================================

REM call base year run Python helper script
%PYTHON% %BASE_YEAR_HELPER% %CONFIG%
if %ERRORLEVEL% neq 0 goto ProcessError

call conda.bat deactivate
pause
exit /b 0

:ProcessError
REM error handling: print message and clean up
echo ERROR: Base year helper tool run encountered an error. See above messages (and log file) to diagnose.

call conda.bat deactivate
pause
exit /b 1
