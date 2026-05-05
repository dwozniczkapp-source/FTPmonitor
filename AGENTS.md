# FTP Monitor — instrukcje dla agenta

## Struktura projektu

| Plik | Rola |
|------|------|
| `ftp_monitor_service.py` | Windows Service — logika FTP, działa w tle |
| `ftp_monitor_gui.py` | GUI PyQt5 — konfiguracja i sterowanie serwisem |
| `build.bat` | Buduje oba EXE przez PyInstaller |
| `post_task.bat` | Uruchamiaj po każdej zmianie: build + git push |

## Stack

- Python 3.10+
- PyQt5 (GUI)
- pywin32 (Windows Service)
- PyInstaller (budowanie EXE)
- ftplib (wbudowana, bez dodatkowych zależności)

## Zasady kodowania

- Komentarze i nazwy zmiennych po polsku lub angielsku — bez mieszania w obrębie jednej funkcji
- Logika serwisu (`ftp_monitor_service.py`) i GUI (`ftp_monitor_gui.py`) są rozdzielone — nie łącz ich w jeden plik
- Konfiguracja trzymana w `%USERPROFILE%\ftp_monitor_config.json` — nie zmieniaj tej ścieżki
- Log serwisu trafia do `ftp_monitor_service.log` obok EXE serwisu
- Nie commituj: `dist/`, `build/`, `*.spec`, `*.log`, `*.json` — są w `.gitignore`

## Po każdej zmianie kodu — OBOWIĄZKOWO

Uruchom:
```
post_task.bat
```

Ten skrypt:
1. Buduje `ftp_monitor_service.exe` i `ftp_monitor_gui.exe`
2. Robi `git add` tylko plików źródłowych
3. Commituje z automatyczną wiadomością zawierającą datę i godzinę
4. Pushuje na `origin master`

Nie rób ręcznego `git commit` ani `git push` — używaj wyłącznie `post_task.bat`.
