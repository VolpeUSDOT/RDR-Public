
@ECHO OFF
cls
set PYTHONDONTWRITEBYTECODE=1
REM   default is #ECHO OFF, cls (clear screen), and disable .pyc files
REM   for debugging REM @ECHO OFF line above to see commands
REM -------------------------------------------------


REM ==============================================
REM ======== ENVIRONMENT VARIABLES ===============
REM ==============================================
set PYTHON="C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
set PREPARE_NETWORK_HELPER="C:\GitHub\RDR\helper_tools\format_network\prepare_rdr_transit_network.py"
set CONFIG="C:\GitHub\RDR\scenarios\rs5_prepare_network\RS5_format_network.config"

REM ==============================================
REM ======== RUN THE PREPARE NETWORK TOOL ========
REM ==============================================

REM call Prepare RDR Transit Network Python helper script
%PYTHON% %PREPARE_NETWORK_HELPER% %CONFIG%

pause
exit /b
