
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
set REVIEW_TRIP_TABLE="C:\GitHub\RDR\helper_tools\format_demand\review_trip_table.py"

call activate RDRenv


REM =======================================================
REM ======== RUN THE REVIEW TRIP TABLE HELPER TOOL ========
REM =======================================================

REM call Review Trip Table Python helper script
%PYTHON% %REVIEW_TRIP_TABLE%
if %ERRORLEVEL% neq 0 goto ProcessError

call conda.bat deactivate
pause
exit /b 0

:ProcessError
REM error handling: print message and clean up
echo ERROR: Review trip table helper tool run encountered an error. See above messages (and log file) to diagnose.

call conda.bat deactivate
pause
exit /b 1
