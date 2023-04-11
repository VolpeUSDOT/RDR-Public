
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
set TRANSIT_CONNECTOR_HELPER="C:\GitHub\RDR\helper_tools\format_network\create_transit_centroid_connectors.py"
set CONFIG="C:\GitHub\RDR\helper_tools\format_network\format_network.config"

REM ==============================================
REM ====== RUN THE TRANSIT CONNECTOR TOOL ========
REM ==============================================

REM call Transit Centroid Connector Python helper script
%PYTHON% %TRANSIT_CONNECTOR_HELPER% %CONFIG%

pause
exit /b
