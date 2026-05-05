@echo off
echo ============================================================
echo  FTP Monitor - post_task: build + git push
echo ============================================================
echo.

:: ── 1. Build ────────────────────────────────────────────────────────────────
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

:: ── 2. Git add (tylko zrodla) ────────────────────────────────────────────────
echo [2/3] Git add...

git add ftp_monitor_service.py ftp_monitor_gui.py build.bat post_task.bat AGENTS.md README_FTPMonitor.md .gitignore

if errorlevel 1 (
    echo [BLAD] git add nie powiodl sie!
    exit /b 1
)

:: ── 3. Commit + push ─────────────────────────────────────────────────────────
echo [3/3] Commit i push...

:: Wiadomosc commita z data i godzina
for /f "tokens=1-3 delims=." %%a in ("%date%") do set D=%%a.%%b.%%c
for /f "tokens=1-2 delims=:" %%a in ("%time: =0%") do set T=%%a:%%b
set MSG=auto: build %D% %T%

git diff --cached --quiet
if errorlevel 1 (
    git commit -m "%MSG%"
    git push origin master
    echo.
    echo [OK] Wypchnięto: %MSG%
) else (
    echo [INFO] Brak zmian do commitowania.
)

echo.
echo ============================================================
echo  Gotowe!
echo  EXE: dist\ftp_monitor_service.exe
echo       dist\ftp_monitor_gui.exe
echo ============================================================
