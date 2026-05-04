#!/usr/bin/env python3
"""
FTP Monitor - Windows Service
Instalacja:  ftp_monitor_service.exe install
Start:       ftp_monitor_service.exe start
Stop:        ftp_monitor_service.exe stop
Usunięcie:   ftp_monitor_service.exe remove
"""

import sys
import os
import json
import ftplib
import time
import logging
import threading
from datetime import datetime
from pathlib import Path

import win32serviceutil
import win32service
import win32event
import servicemanager

# ── Ścieżki ─────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "ftp_monitor_config.json")
LOG_FILE    = os.path.join(BASE_DIR, "ftp_monitor_service.log")

# ── Logger ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("FTPMonitorService")


# ════════════════════════════════════════════════════════════════════════════
#  Logika FTP
# ════════════════════════════════════════════════════════════════════════════
def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Błąd wczytywania konfiguracji: {e}")
    return {"profiles": [], "interval_seconds": 60, "local_folder": ""}


def process_profile(profile: dict, local_root: str):
    host       = profile.get("host", "")
    port       = int(profile.get("port", 21))
    user       = profile.get("user", "")
    password   = profile.get("password", "")
    remote_dir = profile.get("remote_dir", "/")
    name       = profile.get("name", host)
    passive    = profile.get("passive", True)

    if not host:
        return

    subfolder = profile.get("local_subfolder", "") or name
    local_dir = os.path.join(local_root, subfolder)
    os.makedirs(local_dir, exist_ok=True)

    log.info(f"[{name}] Łączę z {host}:{port} ...")

    with ftplib.FTP() as ftp:
        ftp.connect(host, port, timeout=20)
        ftp.set_pasv(passive)
        ftp.login(user, password)
        ftp.cwd(remote_dir)

        files = []
        ftp.retrlines("NLST", files.append)

        if not files:
            log.info(f"[{name}] Brak plików")
            return

        log.info(f"[{name}] Znaleziono {len(files)} element(ów)")

        for filename in files:
            # pomijamy katalogi przez SIZE
            try:
                ftp.size(filename)
            except ftplib.error_perm:
                log.debug(f"[{name}] Pomijam (katalog?): {filename}")
                continue

            local_path = os.path.join(local_dir, filename)
            with open(local_path, "wb") as f:
                ftp.retrbinary(f"RETR {filename}", f.write)

            ftp.delete(filename)
            log.info(f"[{name}] ✔ Pobrano i usunięto: {filename}")


def run_cycle(config: dict):
    profiles   = config.get("profiles", [])
    local_root = config.get("local_folder", "")

    if not local_root:
        log.warning("Brak ustawionego folderu lokalnego — pomijam cykl")
        return

    for profile in profiles:
        if not profile.get("enabled", True):
            continue
        try:
            process_profile(profile, local_root)
        except Exception as e:
            log.error(f"[{profile.get('name','?')}] Błąd: {e}")


# ════════════════════════════════════════════════════════════════════════════
#  Windows Service
# ════════════════════════════════════════════════════════════════════════════
class FTPMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_         = "FTPMonitorService"
    _svc_display_name_ = "FTP Monitor Service"
    _svc_description_  = "Automatycznie pobiera pliki z serwerów FTP i usuwa je ze źródła."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self._stop_event = win32event.CreateEvent(None, 0, 0, None)
        self._running = True

    def SvcStop(self):
        log.info("Serwis: otrzymano sygnał zatrzymania")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._running = False
        win32event.SetEvent(self._stop_event)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        log.info("Serwis FTP Monitor uruchomiony")
        self._main_loop()

    def _main_loop(self):
        while self._running:
            config   = load_config()
            interval = max(5, config.get("interval_seconds", 60))

            log.info(f"Uruchamiam cykl (interwał: {interval}s)")
            try:
                run_cycle(config)
            except Exception as e:
                log.error(f"Nieoczekiwany błąd cyklu: {e}")

            # czekaj N sekund lub aż przyjdzie stop
            result = win32event.WaitForSingleObject(self._stop_event, interval * 1000)
            if result == win32event.WAIT_OBJECT_0:
                break

        log.info("Serwis FTP Monitor zatrzymany")


# ════════════════════════════════════════════════════════════════════════════
#  Punkt wejścia
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) == 1:
        # uruchomiony przez SCM
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(FTPMonitorService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # install / start / stop / remove
        win32serviceutil.HandleCommandLine(FTPMonitorService)
