@echo off
REM ============================================================
REM  Cam Kesim Optimizasyon - Windows Kurulum Scripti
REM  Python sanal ortami olusturur ve bagimliliklari kurar.
REM ============================================================

setlocal
cd /d "%~dp0"

echo.
echo [1/4] Python kontrol ediliyor...
where python >nul 2>&1
if errorlevel 1 (
    echo HATA: Python bulunamadi. Lutfen https://www.python.org/downloads/ adresinden Python 3.9+ kurun.
    echo Kurulum sirasinda "Add Python to PATH" secenegini isaretlemeyi unutmayin.
    pause
    exit /b 1
)

python --version

echo.
echo [2/4] Sanal ortam (venv) olusturuluyor...
if not exist ".venv\" (
    python -m venv .venv
    if errorlevel 1 (
        echo HATA: Sanal ortam olusturulamadi.
        pause
        exit /b 1
    )
    echo Sanal ortam olusturuldu: .venv
) else (
    echo Sanal ortam zaten mevcut.
)

echo.
echo [3/4] pip guncelleniyor...
call ".venv\Scripts\python.exe" -m pip install --upgrade pip

echo.
echo [4/4] Gerekli paketler kuruluyor (ortools, matplotlib, pydantic, rich, typer)...
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo HATA: Paket kurulumu basarisiz.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Kurulum tamamlandi.
echo  Optimizasyonu calistirmak icin: run.bat
echo ============================================================
pause
endlocal
