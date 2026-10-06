
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
set HELPERPATH=%RDRBASE%helper_tools\exposure_grid_overlay\


if "%GITHUB_ACTIONS%"=="true" (
    echo Running on a GitHub VM
    REM Add your GitHub-specific commands here
    set PYTHON="python"
) else (
    echo Running locally.
    set PYTHON="C:\Users\%USERNAME%\Anaconda3\envs\RDRenv\python.exe"
)

set EXPOSURE_HELPER=%HELPERPATH%exposure_grid_overlay.py

set CONFIG1="%TESTPATH%e1_exposure_grid_haz1.config"

set CONFIG2="%TESTPATH%e1_exposure_grid_haz2.config"

call activate RDRenv
echo Changing Directory

cd %HELPERPATH%

REM =================================================
REM ======== RUN THE EXPOSURE GRID OVERLAY HELPER TOOL ========
REM =================================================
echo First Hazard
REM call Exposure Grid Overlay Python helper script
%PYTHON% %EXPOSURE_HELPER% %CONFIG1% %TESTPATH%
if %ERRORLEVEL% neq 0 goto ProcessError
echo Second Hazard
REM call Exposure Grid Overlay Python helper script
%PYTHON% %EXPOSURE_HELPER% %CONFIG2% %TESTPATH%
if %ERRORLEVEL% neq 0 goto ProcessError

call conda.bat deactivate
pause
exit /b 0

:ProcessError
REM error handling: print message and clean up
echo ERROR: Exposure grid overlay helper tool run encountered an error. See above messages (and log file) to diagnose.

call conda.bat deactivate
pause
exit /b 1
