
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
set EXPOSURE_GRID_OVERLAY_HELPER="C:\GitHub\RDR\helper_tools\exposure_grid_overlay\exposure_grid_overlay.py"
set CONFIG="C:\GitHub\RDR\helper_tools\exposure_grid_overlay\exposure_grid_sample.config"


REM ==============================================
REM ======== RUN THE EXPOSURE ANALYSIS TOOL ==================
REM ==============================================

REM call Exposure Grid Overlay Python helper script
%PYTHON% %EXPOSURE_GRID_OVERLAY_HELPER% %CONFIG%

pause
exit /b
