@echo off
setlocal

echo ============================================================
echo  FTP Monitor - post_task: build + git push
echo ============================================================
echo.

:: 1. Build
echo [1/3] Buduje EXE...

pyinstaller --onefile --noconsole --name ftp_monitor_service ^
    --hidden-import=win32timezone ^
    --hidden-import=win32serviceutil ^
    --hidden-import=win32service ^
    --hidden-import=win32event ^
    --hidden-import=servicemanager ^
    ftp_monitor_service.py >build_service.log 2>&1

if errorlevel 1 (
    echo [BLAD] Build serwisu nie powiodl sie! Szczegoly w build_service.log
    exit /b 1
)

pyinstaller --onefile --windowed --name ftp_monitor_gui ^
    --hidden-import=win32serviceutil ^
    --hidden-import=win32service ^
    --hidden-import=win32event ^
    ftp_monitor_gui.py >build_gui.log 2>&1

if errorlevel 1 (
    echo [BLAD] Build GUI nie powiodl sie! Szczegoly w build_gui.log
    exit /b 1
)

echo [OK] Build zakonczony.
echo.

:: 2. Git add (tylko zrodla)
echo [2/3] Git add...

git add ftp_monitor_service.py ftp_monitor_gui.py build.bat post_task.bat AGENTS.md README_FTPMonitor.md .gitignore

if errorlevel 1 (
    echo [BLAD] git add nie powiodl sie!
    exit /b 1
)

:: 3. Commit + push (zawsze po buildzie)
echo [3/3] Commit i push...

for /f "tokens=1-4 delims=/.- " %%a in ("%date%") do set D=%%a-%%b-%%c-%%d
for /f "tokens=1-3 delims=:., " %%a in ("%time%") do set T=%%a-%%b-%%c
set MSG=auto: build %D% %T%

git commit --allow-empty-message -m "%MSG%"
if errorlevel 1 (
    echo [BLAD] git commit nie powiodl sie!
    exit /b 1
)

git push origin master
if errorlevel 1 (
    echo [BLAD] git push nie powiodl sie!
    exit /b 1
)

echo.
echo [OK] Wypchnieto: %MSG%
echo.
echo ============================================================
echo  Gotowe!
echo  EXE: dist\ftp_monitor_service.exe
echo       dist\ftp_monitor_gui.exe
echo ============================================================
endlocal
