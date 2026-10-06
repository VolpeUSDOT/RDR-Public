
@ECHO OFF
cls
set PYTHONDONTWRITEBYTECODE=1
REM   default is #ECHO OFF, cls (clear screen), and disable .pyc files
REM   for debugging REM @ECHO OFF line above to see commands
REM -------------------------------------------------

REM ==============================================
REM ======== ENVIRONMENT VARIABLES ===============
REM ==============================================

REM Optional: set both values only when automatic discovery cannot find RDRenv.
set "USER_INPUT_CONDA_BASE="
set "USER_INPUT_RDR_PYTHON="

REM Update the values below from their defaults if needed.
set "USER_INPUT_RDR_ROOT=C:\GitHub\RDR"
set "USER_INPUT_CONFIG=C:\GitHub\RDR\scenarios\qs1_sioux_falls\QS1.config"

REM Do not modify values in the rest of this file below; they are determined automatically.
set "CONDA_BASE="
set "ENV_PREFIX="
set "PYTHON="
set "REGISTRY_SELECTED="

IF DEFINED USER_INPUT_CONDA_BASE (
    IF NOT DEFINED USER_INPUT_RDR_PYTHON GOTO IncompleteOverride
    IF NOT EXIST "%USER_INPUT_RDR_PYTHON%" GOTO OverridePythonNotFound
    call :SetEnvironmentPrefix "%USER_INPUT_RDR_PYTHON%"
    set "CONDA_BASE=%USER_INPUT_CONDA_BASE%"
    set PYTHON="%USER_INPUT_RDR_PYTHON%"
    GOTO PythonFound
)
IF DEFINED USER_INPUT_RDR_PYTHON GOTO IncompleteOverride

IF EXIST "%USERPROFILE%\.conda\environments.txt" (
    FOR /F "usebackq delims=" %%E IN ("%USERPROFILE%\.conda\environments.txt") DO (
        call :TryRegistryCandidate "%%~E"
        IF DEFINED PYTHON GOTO PythonFound
    )
)

IF EXIST "%LOCALAPPDATA%\anaconda3\envs\RDRenv\python.exe" (
    set "CONDA_BASE=%LOCALAPPDATA%\anaconda3"
    set "ENV_PREFIX=%LOCALAPPDATA%\anaconda3\envs\RDRenv"
    set PYTHON="%LOCALAPPDATA%\anaconda3\envs\RDRenv\python.exe"
    GOTO PythonFound
)
IF EXIST "%USERPROFILE%\Anaconda3\envs\RDRenv\python.exe" (
    set "CONDA_BASE=%USERPROFILE%\Anaconda3"
    set "ENV_PREFIX=%USERPROFILE%\Anaconda3\envs\RDRenv"
    set PYTHON="%USERPROFILE%\Anaconda3\envs\RDRenv\python.exe"
    GOTO PythonFound
)
GOTO PythonNotFound

:PythonFound
IF DEFINED REGISTRY_SELECTED IF NOT DEFINED CONDA_BASE GOTO RegistryCondaBaseNotFound
set "INPUT_VALIDATION="%USER_INPUT_RDR_ROOT%\helper_tools\input_validation\rdr_input_validation.py""
set "CONFIG="%USER_INPUT_CONFIG%""

IF NOT EXIST "%USER_INPUT_RDR_ROOT%\" (
    echo ERROR: USER_INPUT_RDR_ROOT does not name an existing RDR root: "%USER_INPUT_RDR_ROOT%".
    exit /b 1
)
IF NOT EXIST %INPUT_VALIDATION% (
    echo ERROR: USER_INPUT_RDR_ROOT does not contain the required rdr_input_validation.py helper: "%USER_INPUT_RDR_ROOT%".
    exit /b 1
)
IF NOT EXIST %CONFIG% (
    echo ERROR: USER_INPUT_CONFIG does not name an existing config file: "%USER_INPUT_CONFIG%".
    exit /b 1
)

set "CONDA_ACTIVATION="
IF EXIST "%CONDA_BASE%\condabin\conda.bat" (
    set "CONDA_COMMAND=%CONDA_BASE%\condabin\conda.bat"
    set "CONDA_ACTIVATION=activate"
) ELSE IF EXIST "%CONDA_BASE%\Scripts\activate.bat" (
    set "CONDA_COMMAND=%CONDA_BASE%\Scripts\activate.bat"
) ELSE (
    echo ERROR: No Conda activation command was found under "%CONDA_BASE%".
    exit /b 1
)
call "%CONDA_COMMAND%" %CONDA_ACTIVATION% "%ENV_PREFIX%"
IF ERRORLEVEL 1 (
    echo ERROR: Failed to activate RDRenv.
    exit /b 1
)

REM ======================================================
REM ======== RUN THE INPUT VALIDATION HELPER TOOL ========
REM ======================================================

REM call input validation Python helper script
%PYTHON% %INPUT_VALIDATION% %CONFIG%
if %ERRORLEVEL% neq 0 goto ProcessError

call "%CONDA_COMMAND%" deactivate
pause
exit /b 0

:ProcessError
REM error handling: print message and clean up
echo ERROR: Input validation helper tool run encountered an error. See above messages (and log file) to diagnose.

call "%CONDA_COMMAND%" deactivate
pause
exit /b 1

:RegistryCondaBaseNotFound
echo ERROR: The registry-selected RDRenv interpreter does not have a usable Conda base.
echo Set both USER_INPUT_CONDA_BASE and USER_INPUT_RDR_PYTHON at the top of this launcher.
exit /b 1

:PythonNotFound
echo ERROR: RDRenv Python interpreter was not found through registry lookup or conventional fallbacks.
echo Checked registry entries in "%USERPROFILE%\.conda\environments.txt" when present.
echo Attempted conventional fallbacks:
echo   %LOCALAPPDATA%\anaconda3\envs\RDRenv\python.exe
echo   %USERPROFILE%\Anaconda3\envs\RDRenv\python.exe
echo Set both USER_INPUT_CONDA_BASE and USER_INPUT_RDR_PYTHON at the top of this launcher.
exit /b 1

:IncompleteOverride
echo ERROR: USER_INPUT_CONDA_BASE and USER_INPUT_RDR_PYTHON must either both be blank or both be set.
echo Set both values at the top of this launcher to use a manual override.
exit /b 1

:OverridePythonNotFound
echo ERROR: USER_INPUT_RDR_PYTHON does not name an existing Python interpreter: "%USER_INPUT_RDR_PYTHON%".
echo Set both USER_INPUT_CONDA_BASE and USER_INPUT_RDR_PYTHON at the top of this launcher.
exit /b 1

:SetEnvironmentPrefix
for %%P in ("%~dp1.") do set "ENV_PREFIX=%%~fP"
exit /b

:TryRegistryCandidate
setlocal EnableExtensions EnableDelayedExpansion
set "CANDIDATE=%~1"
if not defined CANDIDATE (
    endlocal
    exit /b
)
if "!CANDIDATE:~-1!"=="\" set "CANDIDATE=!CANDIDATE:~0,-1!"
for %%P in ("!CANDIDATE!") do set "ENV_NAME=%%~nxP"
if not "!ENV_NAME!"=="RDRenv" (
    endlocal
    exit /b
)
if not exist "!CANDIDATE!\python.exe" (
    endlocal
    exit /b
)
for %%P in ("!CANDIDATE!") do set "SELECTED_PREFIX=%%~fP"
for %%P in ("!SELECTED_PREFIX!") do set "PREFIX_PARENT=%%~dpP"
set "PREFIX_PARENT=!PREFIX_PARENT:~0,-1!"
for %%P in ("!PREFIX_PARENT!") do set "PARENT_NAME=%%~nxP"
set "USABLE_CONDA_BASE="
if /I "!PARENT_NAME!"=="envs" (
    set "CANDIDATE_CONDA_BASE=!PREFIX_PARENT:~0,-5!"
    if exist "!CANDIDATE_CONDA_BASE!\condabin\conda.bat" set "USABLE_CONDA_BASE=!CANDIDATE_CONDA_BASE!"
    if not defined USABLE_CONDA_BASE if exist "!CANDIDATE_CONDA_BASE!\Scripts\activate.bat" set "USABLE_CONDA_BASE=!CANDIDATE_CONDA_BASE!"
)
if defined USABLE_CONDA_BASE (
    for %%A in ("!SELECTED_PREFIX!") do for %%B in ("!USABLE_CONDA_BASE!") do (
        endlocal
        set "ENV_PREFIX=%%~fA"
        set PYTHON="%%~fA\python.exe"
        set "CONDA_BASE=%%~fB"
        set "REGISTRY_SELECTED=1"
        exit /b
    )
) else (
    for %%A in ("!SELECTED_PREFIX!") do (
        endlocal
        set "ENV_PREFIX=%%~fA"
        set PYTHON="%%~fA\python.exe"
        set "REGISTRY_SELECTED=1"
        exit /b
    )
)
exit /b
