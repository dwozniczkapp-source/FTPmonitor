@echo off
echo ============================================================
echo  FTP Monitor - Budowanie EXE (PyInstaller)
echo ============================================================
echo.

:: Sprawdz czy pip dostepny
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [BLAD] Python/pip nie znaleziony w PATH!
    pause & exit /b 1
)

echo [1/4] Instaluje zaleznosci...
python -m pip install pyqt5 pywin32 pyinstaller --upgrade -q
if errorlevel 1 (
    echo [BLAD] Instalacja zaleznosci nie powiodla sie!
    pause & exit /b 1
)

echo.
echo [2/4] Buduje ftp_monitor_service.exe ...
pyinstaller ^
    --onefile ^
    --noconsole ^
    --name ftp_monitor_service ^
    --hidden-import=win32timezone ^
    --hidden-import=win32serviceutil ^
    --hidden-import=win32service ^
    --hidden-import=win32event ^
    --hidden-import=servicemanager ^
    ftp_monitor_service.py

if errorlevel 1 (
    echo [BLAD] Budowanie serwisu nie powiodlo sie!
    pause & exit /b 1
)

echo.
echo [3/4] Buduje ftp_monitor_gui.exe ...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name ftp_monitor_gui ^
    --hidden-import=win32serviceutil ^
    --hidden-import=win32service ^
    --hidden-import=win32event ^
    ftp_monitor_gui.py

if errorlevel 1 (
    echo [BLAD] Budowanie GUI nie powiodlo sie!
    pause & exit /b 1
)

echo.
echo [4/4] Kopiuje pliki do folderu dist\FTPMonitor ...
mkdir dist\FTPMonitor 2>nul
copy dist\ftp_monitor_service.exe dist\FTPMonitor\
copy dist\ftp_monitor_gui.exe dist\FTPMonitor\

echo.
echo ============================================================
echo  GOTOWE! Pliki w: dist\FTPMonitor\
echo.
echo   ftp_monitor_gui.exe     - Panel zarzadzania (uruchamiaj normalnie)
echo   ftp_monitor_service.exe - Serwis Windows (nie uruchamiaj recznie)
echo.
echo  Instrukcja:
echo   1. Skopiuj oba pliki w to samo miejsce (np. C:\FTPMonitor\)
echo   2. Uruchom ftp_monitor_gui.exe jako Administrator
echo   3. Skonfiguruj profile FTP i folder docelowy
echo   4. Kliknij "Instaluj serwis" a potem "Start"
echo ============================================================
echo.
pause
