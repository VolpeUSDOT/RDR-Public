
@ECHO OFF
cls
set PYTHONDONTWRITEBYTECODE=1
REM   default is #ECHO OFF, cls (clear screen), and disable .pyc files
REM   for debugging REM @ECHO OFF line above to see commands
REM -------------------------------------------------


REM ==============================================
REM ======== ENVIRONMENT VARIABLES ===============
REM ==============================================

REM for QS2, need to go up one more level to find the metamodel_py directory

set batdir=%~dp0
for %%A in ("%batdir%") do set TESTPATH=%%~dpA
for %%A in ("%TESTPATH%\..\..\..\") do set RDRPATH=%%~dpA

REM Check to see if running on a local machine on a C: drive. If not, do not alter PATH or set Python
set drive=%~d0
if %drive%==C: set PATH=C:\Users\%USERNAME%\Anaconda3\Scripts;%PATH%
if %drive%==C: (set PYTHON="C:\Users\%USERNAME%\Anaconda3\envs\RDRenv\python.exe") else (set PYTHON="python")

set RDR="%RDRPATH%Run_RDR.py"

set CONFIG="%TESTPATH%QS2A.config"

call activate RDRenv

cd %RDRPATH%

REM ==============================================
REM ======== RUN THE RDR SCRIPT ==================
REM ==============================================

REM lhs: select AequilibraE runs needed to fill in for TDM
REM %PYTHON% %RDR% %CONFIG% lhs
REM if %ERRORLEVEL% neq 0 goto ProcessError

REM aeq_run: use AequilibraE to run core model for runs identified by LHS
REM %PYTHON% %RDR% %CONFIG% aeq_run
REM if %ERRORLEVEL% neq 0 goto ProcessError

REM aeq_compile: compile all AequilibraE run results
REM %PYTHON% %RDR% %CONFIG% aeq_compile
REM if %ERRORLEVEL% neq 0 goto ProcessError

REM rr: run regression module
REM %PYTHON% %RDR% %CONFIG% rr
REM if %ERRORLEVEL% neq 0 goto ProcessError

REM recov_init: read in input files and extend scenarios for recovery process
%PYTHON% %RDR% %CONFIG% recov_init
if %ERRORLEVEL% neq 0 goto ProcessError

REM recov_calc: consolidate metamodel and recovery results for economic analysis
%PYTHON% %RDR% %CONFIG% recov_calc
if %ERRORLEVEL% neq 0 goto ProcessError

REM o: summarize and write output
%PYTHON% %RDR% %CONFIG% o
if %ERRORLEVEL% neq 0 goto ProcessError

REM test: use to test methods under development
REM %PYTHON% %RDR% %CONFIG% test
REM if %ERRORLEVEL% neq 0 goto ProcessError

call conda.bat deactivate
pause
exit /b 0

:ProcessError
REM error handling: print message and clean up
echo ERROR: RDR run encountered an error. See above messages (and log files) to diagnose.

call conda.bat deactivate
pause
exit /b 1