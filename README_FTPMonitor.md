# FTP Monitor — Windows Service + GUI

Dwa pliki EXE:
- **`ftp_monitor_gui.exe`** — panel zarządzania (uruchamiasz normalnie)  
- **`ftp_monitor_service.exe`** — serwis Windows (działa w tle, nawet bez logowania)

---

## Jak zbudować EXE

Potrzebujesz Pythona (jednorazowo, na maszynie deweloperskiej):

```
python --version    # min. 3.10
build.bat           # uruchom i poczekaj ~2 minuty
```

Gotowe pliki będą w `dist\FTPMonitor\`.  
Na docelowym komputerze Python **nie jest potrzebny**.

---

## Instalacja na docelowym komputerze

1. Skopiuj oba `.exe` w to samo miejsce, np. `C:\FTPMonitor\`
2. Uruchom **`ftp_monitor_gui.exe` jako Administrator** (prawy klik → Uruchom jako administrator)
3. Skonfiguruj profile FTP i folder docelowy w GUI
4. Kliknij **"Instaluj serwis"** → **"Start"**
5. Gotowe — serwis startuje automatycznie razem z Windowsem

---

## Opis GUI

### Pasek statusu serwisu
| Przycisk | Działanie |
|----------|-----------|
| ⬇ Instaluj serwis | Rejestruje serwis w Windows (wymaga admina) |
| ▶ Start | Uruchamia serwis |
| ⏹ Stop | Zatrzymuje serwis |
| 🗑 Odinstaluj | Usuwa serwis z Windows |

### Zakładka: Profile FTP
Każdy profil to jeden serwer FTP:

| Pole | Opis |
|------|------|
| Nazwa profilu | Identyfikator w logach |
| Host FTP | Adres serwera (np. `ftp.firma.pl`) |
| Port | Domyślnie 21 |
| Użytkownik / Hasło | Dane logowania |
| Katalog zdalny | Ścieżka na FTP do monitorowania (np. `/upload`) |
| Podkatalog lokalny | Opcjonalny podkatalog w folderze docelowym |
| Tryb pasywny | Zalecany gdy jest NAT/firewall |
| Aktywny | Odznacz aby tymczasowo wyłączyć profil |

### Zakładka: Ustawienia
| Pole | Opis |
|------|------|
| Folder docelowy | Gdzie trafiają pobrane pliki |
| Interwał sprawdzania | Co ile sekund serwis sprawdza FTP (min. 5s) |

> Ustawienia są czytane przez serwis na początku każdego cyklu — **nie trzeba restartować serwisu** po zmianie konfiguracji.

### Zakładka: Log serwisu
Wyświetla ostatnie 500 linii z pliku `ftp_monitor_service.log` (obok EXE serwisu).

---

## Jak działa serwis

1. Co N sekund budzi się i wczytuje konfigurację z `%USERPROFILE%\ftp_monitor_config.json`
2. Dla każdego aktywnego profilu łączy się z FTP
3. Pobiera wszystkie pliki z katalogu zdalnego do folderu lokalnego
4. Po udanym pobraniu usuwa plik z FTP
5. Przy błędzie jednego profilu — kontynuuje z pozostałymi
6. Katalogi są pomijane (pobierane tylko pliki)

---

## Pliki tworzone przez aplikację

| Plik | Lokalizacja | Opis |
|------|-------------|------|
| `ftp_monitor_config.json` | `%USERPROFILE%\` | Konfiguracja (profile, interwał, folder) |
| `ftp_monitor_service.log` | Obok `ftp_monitor_service.exe` | Log serwisu |

---

## Uwagi

- **Hasła** są przechowywane w pliku JSON jako plaintext. Jeśli wymagane jest wyższe bezpieczeństwo, należy wdrożyć szyfrowanie (np. DPAPI lub Windows Credential Manager).
- Serwis uruchamia się pod kontem **Local System** — upewnij się, że folder docelowy jest dostępny dla tego konta (lub zmień konto serwisu w `services.msc`).
- Jeśli serwis nie startuje — sprawdź log w Podglądzie zdarzeń Windows (`eventvwr.msc` → Dzienniki Windows → Aplikacja).
