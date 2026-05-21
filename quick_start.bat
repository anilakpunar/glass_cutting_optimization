@echo off
REM ============================================================
REM  Cam Kesim Optimizasyon - Tek Tikla Baslat
REM
REM  Bu script ilk calistirmada kurulum yapar, sonrasinda
REM  dogrudan optimizasyonu calistirir.
REM ============================================================

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ilk calistirma tespit edildi - kurulum baslatiliyor...
    echo.
    call setup.bat
    if errorlevel 1 exit /b 1
)

call run.bat %*
endlocal
