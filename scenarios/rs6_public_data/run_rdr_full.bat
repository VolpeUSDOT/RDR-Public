
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
set RDR="C:\GitHub\RDR\metamodel_py\Run_RDR.py"

set CONFIG="C:\GitHub\RDR\scenarios\rs6_public_data\RS6.config"

call activate RDRenv
cd C:\GitHub\RDR\metamodel_py


REM ==============================================
REM ======== RUN THE RDR SCRIPT ==================
REM ==============================================

REM lhs: select AequilibraE runs needed to fill in for TDM
%PYTHON% %RDR% %CONFIG% lhs
if %ERRORLEVEL% neq 0 goto ProcessError

REM aeq_run: use AequilibraE to run core model for runs identified by LHS
%PYTHON% %RDR% %CONFIG% aeq_run
if %ERRORLEVEL% neq 0 goto ProcessError

REM aeq_compile: compile all AequilibraE run results
%PYTHON% %RDR% %CONFIG% aeq_compile
if %ERRORLEVEL% neq 0 goto ProcessError

REM rr: run regression module
%PYTHON% %RDR% %CONFIG% rr
if %ERRORLEVEL% neq 0 goto ProcessError

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
