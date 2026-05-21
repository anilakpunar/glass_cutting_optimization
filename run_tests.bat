@echo off
REM ============================================================
REM  Cam Kesim Optimizasyon - Birim Test Calistirma
REM ============================================================

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Sanal ortam bulunamadi. Once setup.bat dosyasini calistirin.
    pause
    exit /b 1
)

set "PYTHONPATH=%CD%\src"

call ".venv\Scripts\python.exe" -m pip install -q pytest

echo.
echo Birim testler calistiriliyor...
echo.
call ".venv\Scripts\python.exe" -m pytest tests\ -v

echo.
pause
endlocal
