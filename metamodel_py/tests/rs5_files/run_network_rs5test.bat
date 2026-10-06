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
set HELPERPATH=%RDRBASE%helper_tools\format_network\


if "%GITHUB_ACTIONS%"=="true" (
    echo Running on a GitHub VM
    REM Add your GitHub-specific commands here
    set PYTHON="python"
) else (
    echo Running locally.
    set PYTHON="C:\Users\%USERNAME%\Anaconda3\envs\RDRenv\python.exe"
)

set NETWORK_HELPER=%HELPERPATH%prepare_rdr_transit_network.py
set CONFIG="%TESTPATH%RS5_format_network.config"

call activate RDRenv
echo Changing Directory

cd %HELPERPATH%

REM =================================================
REM ======== RUN THE EXPOSURE GRID OVERLAY HELPER TOOL ========
REM =================================================
echo Prepare Network
echo %CONFIG%
echo %NETWORK_HELPER%
%PYTHON% %NETWORK_HELPER% %CONFIG% %TESTPATH%
