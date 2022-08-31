
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
set INPUT_VALIDATION="C:\GitHub\RDR\helper_tools\input_validation\rdr_input_validation.py"

set CONFIG="C:\GitHub\RDR\quick_starts\qs1_full_run\QS1.config"

call activate RDRenv


REM ==============================================
REM ======== RUN THE INPUT VALIDATION HELPER TOOL ==================
REM ==============================================

REM call input validation Python helper script
%PYTHON% %INPUT_VALIDATION% %CONFIG%
if %ERRORLEVEL% neq 0 goto ProcessError

call conda.bat deactivate
pause
exit /b 0

:ProcessError
REM error handling: print message and clean up
echo ERROR: Input validation helper tool run encountered an error. See above messages (and log file) to diagnose.

call conda.bat deactivate
pause
exit /b 1
