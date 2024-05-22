
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
set EQUITY_OVERLAY_HELPER="C:\GitHub\RDR\helper_tools\equity_and_benefits_analysis\equity_overlay.py"
set CONFIG="C:\GitHub\RDR\helper_tools\equity_and_benefits_analysis\equity_metrics.config"

REM =============================================
REM ======== RUN THE EQUITY OVERLAY TOOL ========
REM =============================================

REM call Equity Overlay Python helper script
%PYTHON% %EQUITY_OVERLAY_HELPER% %CONFIG%

pause
exit /b
