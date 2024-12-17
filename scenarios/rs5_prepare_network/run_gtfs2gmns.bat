
@ECHO OFF
cls
set PYTHONDONTWRITEBYTECODE=1
REM   default is #ECHO OFF, cls (clear screen), and disable .pyc files
REM   for debugging REM @ECHO OFF line above to see commands
REM -------------------------------------------------


REM ==============================================
REM ======== ENVIRONMENT VARIABLES ===============
REM ==============================================
set PYTHON="C:\Users\%USERNAME%\Anaconda3\envs\RDRenv\python.exe"
set GMNS_CONVERTER="C:\GitHub\GTFS2GMNS\src\gtfs2gmns.py"

set GTFS_DIR="C:\GitHub\RDR\scenarios\rs5_prepare_network\Data\inputs\GTFS_data"

REM ==============================================
REM ========== RUN THE GTFS2GMNS TOOL ============
REM ==============================================

REM call GTFS2GMNS Python script
%PYTHON% %GMNS_CONVERTER% %GTFS_DIR%

pause
exit /b
