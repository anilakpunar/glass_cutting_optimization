@echo off
REM ============================================================
REM  Cam Kesim Optimizasyon - Web Arayuzu (Windows)
REM  Streamlit arayuzunu baslatir ve tarayicida acar.
REM ============================================================

setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Sanal ortam bulunamadi. Once setup.bat dosyasini calistirin.
    pause
    exit /b 1
)

REM streamlit kurulu degilse kur
call ".venv\Scripts\python.exe" -c "import streamlit" 2>nul
if errorlevel 1 (
    echo streamlit kuruluyor...
    call ".venv\Scripts\python.exe" -m pip install -q streamlit
)

echo Arayuz baslatiliyor... Tarayici otomatik acilacak (http://localhost:8501)
call ".venv\Scripts\python.exe" -m streamlit run streamlit_app.py

endlocal
