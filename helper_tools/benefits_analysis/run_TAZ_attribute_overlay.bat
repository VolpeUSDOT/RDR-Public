
@ECHO OFF
cls
set PYTHONDONTWRITEBYTECODE=1
REM   default is #ECHO OFF, cls (clear screen), and disable .pyc files
REM   for debugging REM @ECHO OFF line above to see commands
REM ---------------------------------------------------


REM ===================================================
REM ======== ENVIRONMENT VARIABLES ====================
REM ===================================================
set PYTHON="C:\Users\%USERNAME%\Anaconda3\envs\RDRenv\python.exe"
set ATTRIBUTE_OVERLAY_HELPER="C:\GitHub\RDR\helper_tools\benefits_analysis\TAZ_attribute_overlay.py"

set CONFIG="C:\GitHub\RDR\helper_tools\benefits_analysis\TAZ_metrics.config"

REM ====================================================
REM ======== RUN THE TAZ ATTRIBUTE OVERLAY TOOL ========
REM ====================================================

REM call TAZ Attribute Overlay Python helper script
%PYTHON% %ATTRIBUTE_OVERLAY_HELPER% %CONFIG%
if %ERRORLEVEL% neq 0 goto ProcessError

pause
exit /b 0

:ProcessError
REM error handling: print message
echo ERROR: TAZ attribute overlay helper tool run encountered an error. See above messages (and log file) to diagnose.

pause
exit /b 1
