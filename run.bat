@echo off
REM ============================================================
REM  Cam Kesim Optimizasyon - Windows Calistirma Scripti
REM
REM  Kullanim:
REM      run.bat                              -> ornek girdi ile calisir
REM      run.bat my_job.json                  -> kendi girdi dosyaniz
REM      run.bat my_job.json output_klasoru   -> ozel cikti klasoru
REM ============================================================

setlocal
cd /d "%~dp0"

REM Argumanlar
set "JOB_FILE=%~1"
if "%JOB_FILE%"=="" set "JOB_FILE=examples\sample_input.json"

set "OUT_DIR=%~2"
if "%OUT_DIR%"=="" set "OUT_DIR=output"

set "TIME_LIMIT=%~3"
if "%TIME_LIMIT%"=="" set "TIME_LIMIT=30"

REM Sanal ortam kontrol
if not exist ".venv\Scripts\python.exe" (
    echo Sanal ortam bulunamadi. Once setup.bat dosyasini calistirin.
    pause
    exit /b 1
)

REM Girdi dosyasi kontrol
if not exist "%JOB_FILE%" (
    echo HATA: Girdi dosyasi bulunamadi: %JOB_FILE%
    pause
    exit /b 1
)

set "PYTHONPATH=%CD%\src"

echo.
echo ============================================================
echo  Cam Kesim Optimizasyonu calistiriliyor
echo  Girdi      : %JOB_FILE%
echo  Cikti      : %OUT_DIR%
echo  Sure siniri: %TIME_LIMIT% saniye / plaka
echo ============================================================
echo.

call ".venv\Scripts\python.exe" main.py "%JOB_FILE%" --output "%OUT_DIR%" --time-limit %TIME_LIMIT%

if errorlevel 1 (
    echo.
    echo HATA: Optimizasyon basarisiz.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Tamamlandi. Sonuclar: %OUT_DIR%
echo ============================================================

REM Cikti klasorunu otomatik ac
if exist "%OUT_DIR%" start "" explorer "%OUT_DIR%"

pause
endlocal
