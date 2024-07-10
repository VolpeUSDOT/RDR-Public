
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
set HELPERPATH=%RDRBASE%helper_tools\equity_and_benefits_analysis\

REM Check to see if running on a local machine on a C: drive. If not, do not alter PATH or set Python
set drive=%~d0
if %drive%==C: set PATH=C:\Users\%USERNAME%\Anaconda3\Scripts;%PATH%
if %drive%==C: (set PYTHON="C:\Users\%USERNAME%\Anaconda3\envs\RDRenv\python.exe") else (set PYTHON="python")

set EQUITY_HELPER=%HELPERPATH%TAZ_metrics.py

set CONFIG="%TESTPATH%RS3_equity_metrics.config"

call activate RDRenv

cd %HELPERPATH%

REM =================================================
REM ======== RUN THE TAZ METRICS HELPER TOOL ========
REM =================================================

REM call TAZ equity metrics Python helper script
%PYTHON% %EQUITY_HELPER% %CONFIG%
if %ERRORLEVEL% neq 0 goto ProcessError

call conda.bat deactivate
pause
exit /b 0

:ProcessError
REM error handling: print message and clean up
echo ERROR: TAZ equity metrics helper tool run encountered an error. See above messages (and log file) to diagnose.

call conda.bat deactivate
pause
exit /b 1
