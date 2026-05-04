#!/usr/bin/env python3
"""
FTP Monitor - GUI (menedżer konfiguracji + kontrola serwisu Windows)
"""

import sys
import os
import json
import ftplib
import subprocess
import ctypes
import threading
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QTabWidget, QTextEdit,
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QSystemTrayIcon,
    QMenu, QAction, QStyle, QFrame, QGroupBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

# ── Stałe ────────────────────────────────────────────────────────────────────
SERVICE_NAME = "FTPMonitorService"
CONFIG_FILE  = os.path.join(os.path.expanduser("~"), "ftp_monitor_config.json")

# Ścieżka do exe serwisu — zakładamy że jest obok GUI exe
BASE_DIR     = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
SERVICE_EXE  = os.path.join(BASE_DIR, "ftp_monitor_service.exe")


# ════════════════════════════════════════════════════════════════════════════
#  Pomocnicze: obsługa serwisu Windows
# ════════════════════════════════════════════════════════════════════════════
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin(args: list[str]) -> tuple[bool, str]:
    """Uruchamia SERVICE_EXE z podanymi args jako administrator."""
    try:
        result = subprocess.run(
            [SERVICE_EXE] + args,
            capture_output=True, text=True, timeout=15
        )
        out = (result.stdout + result.stderr).strip()
        return result.returncode == 0, out
    except FileNotFoundError:
        return False, f"Nie znaleziono: {SERVICE_EXE}"
    except Exception as e:
        return False, str(e)


def get_service_status() -> str:
    """Zwraca status serwisu: Running / Stopped / Not Installed / Unknown"""
    try:
        import win32serviceutil
        import win32service
        status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
        state  = status[1]
        mapping = {
            win32service.SERVICE_RUNNING:       "Running",
            win32service.SERVICE_STOPPED:       "Stopped",
            win32service.SERVICE_START_PENDING: "Starting...",
            win32service.SERVICE_STOP_PENDING:  "Stopping...",
        }
        return mapping.get(state, "Unknown")
    except Exception as e:
        msg = str(e)
        if "does not exist" in msg or "1060" in msg:
            return "Not Installed"
        return "Unknown"


# ════════════════════════════════════════════════════════════════════════════
#  Dialog: dodaj / edytuj profil FTP
# ════════════════════════════════════════════════════════════════════════════
class ProfileDialog(QDialog):
    def __init__(self, parent=None, profile: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Profil FTP")
        self.setMinimumWidth(440)
        self._build(profile or {})

    def _build(self, p: dict):
        layout = QVBoxLayout(self)
        form   = QFormLayout()

        self.name_edit     = QLineEdit(p.get("name", ""))
        self.host_edit     = QLineEdit(p.get("host", ""))
        self.port_spin     = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(int(p.get("port", 21)))
        self.user_edit     = QLineEdit(p.get("user", ""))
        self.pass_edit     = QLineEdit(p.get("password", ""))
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.dir_edit      = QLineEdit(p.get("remote_dir", "/"))
        self.sub_edit      = QLineEdit(p.get("local_subfolder", ""))
        self.passive_cb    = QCheckBox("Tryb pasywny (PASV)")
        self.passive_cb.setChecked(p.get("passive", True))
        self.enabled_cb    = QCheckBox("Profil aktywny")
        self.enabled_cb.setChecked(p.get("enabled", True))

        form.addRow("Nazwa profilu *:", self.name_edit)
        form.addRow("Host FTP *:",      self.host_edit)
        form.addRow("Port:",            self.port_spin)
        form.addRow("Użytkownik:",      self.user_edit)
        form.addRow("Hasło:",           self.pass_edit)
        form.addRow("Katalog zdalny *:", self.dir_edit)
        form.addRow("Podkatalog lokalny:", self.sub_edit)
        form.addRow("", self.passive_cb)
        form.addRow("", self.enabled_cb)
        layout.addLayout(form)

        test_btn = QPushButton("🔌 Testuj połączenie")
        test_btn.clicked.connect(self._test)
        layout.addWidget(test_btn)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _accept(self):
        if not self.host_edit.text().strip():
            QMessageBox.warning(self, "Błąd", "Host FTP jest wymagany!")
            return
        self.accept()

    def _test(self):
        host     = self.host_edit.text().strip()
        port     = self.port_spin.value()
        user     = self.user_edit.text().strip()
        password = self.pass_edit.text()
        rdir     = self.dir_edit.text().strip()
        try:
            with ftplib.FTP() as ftp:
                ftp.connect(host, port, timeout=10)
                ftp.set_pasv(self.passive_cb.isChecked())
                ftp.login(user, password)
                ftp.cwd(rdir)
                files = []
                ftp.retrlines("NLST", files.append)
            QMessageBox.information(
                self, "Sukces",
                f"✔ Połączenie udane!\nZnaleziono {len(files)} element(ów) w {rdir}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Błąd połączenia", str(e))

    def get_profile(self) -> dict:
        return {
            "name":           self.name_edit.text().strip() or self.host_edit.text().strip(),
            "host":           self.host_edit.text().strip(),
            "port":           self.port_spin.value(),
            "user":           self.user_edit.text().strip(),
            "password":       self.pass_edit.text(),
            "remote_dir":     self.dir_edit.text().strip() or "/",
            "local_subfolder":self.sub_edit.text().strip(),
            "passive":        self.passive_cb.isChecked(),
            "enabled":        self.enabled_cb.isChecked(),
        }


# ════════════════════════════════════════════════════════════════════════════
#  Główne okno
# ════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FTP Monitor — Panel zarządzania")
        self.setMinimumSize(960, 640)

        self._config: dict = self._load_config()
        self._build_ui()
        self._populate_profiles()

        # Timer odświeżania statusu serwisu co 3s
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_service_status)
        self._status_timer.start(3000)
        self._refresh_service_status()

        self._tray = self._build_tray()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Pasek statusu serwisu ──
        svc_group = QGroupBox("Status serwisu Windows")
        svc_layout = QHBoxLayout(svc_group)

        self.svc_status_label = QLabel("Sprawdzam...")
        self.svc_status_label.setFont(QFont("Consolas", 11, QFont.Bold))

        self.install_btn   = QPushButton("⬇ Instaluj serwis")
        self.uninstall_btn = QPushButton("🗑 Odinstaluj")
        self.svc_start_btn = QPushButton("▶ Start")
        self.svc_stop_btn  = QPushButton("⏹ Stop")

        for btn in [self.install_btn, self.uninstall_btn,
                    self.svc_start_btn, self.svc_stop_btn]:
            btn.setFixedHeight(34)

        self.install_btn.setStyleSheet(  "background:#2980b9;color:white;border-radius:4px;font-weight:bold;")
        self.svc_start_btn.setStyleSheet("background:#27ae60;color:white;border-radius:4px;font-weight:bold;")
        self.svc_stop_btn.setStyleSheet( "background:#c0392b;color:white;border-radius:4px;font-weight:bold;")

        self.install_btn.clicked.connect(  self._install_service)
        self.uninstall_btn.clicked.connect(self._uninstall_service)
        self.svc_start_btn.clicked.connect(self._start_service)
        self.svc_stop_btn.clicked.connect( self._stop_service)

        svc_layout.addWidget(QLabel("Status:"))
        svc_layout.addWidget(self.svc_status_label)
        svc_layout.addStretch()
        svc_layout.addWidget(self.install_btn)
        svc_layout.addWidget(self.uninstall_btn)
        svc_layout.addWidget(self.svc_start_btn)
        svc_layout.addWidget(self.svc_stop_btn)

        root.addWidget(svc_group)

        # ── Admin warning ──
        if not is_admin():
            warn = QLabel(
                "⚠  Uruchom jako Administrator aby móc instalować/sterować serwisem Windows!"
            )
            warn.setStyleSheet(
                "background:#7d3c00;color:#f8c471;padding:6px 10px;"
                "border-radius:4px;font-weight:bold;"
            )
            root.addWidget(warn)

        # ── Tabs ──
        tabs = QTabWidget()
        root.addWidget(tabs)
        tabs.addTab(self._build_profiles_tab(), "📂 Profile FTP")
        tabs.addTab(self._build_settings_tab(), "⚙ Ustawienia")
        tabs.addTab(self._build_log_tab(),      "📋 Log serwisu")

    def _build_profiles_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.profiles_table = QTableWidget(0, 6)
        self.profiles_table.setHorizontalHeaderLabels(
            ["Nazwa", "Host", "Port", "Użytkownik", "Katalog zdalny", "Aktywny"]
        )
        self.profiles_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.profiles_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.profiles_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.profiles_table.doubleClicked.connect(self._edit_profile)
        layout.addWidget(self.profiles_table)

        btn_row = QHBoxLayout()
        add_btn  = QPushButton("➕ Dodaj profil")
        edit_btn = QPushButton("✏ Edytuj")
        del_btn  = QPushButton("🗑 Usuń")
        add_btn.clicked.connect(self._add_profile)
        edit_btn.clicked.connect(self._edit_profile)
        del_btn.clicked.connect(self._delete_profile)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    def _build_settings_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        form   = QFormLayout()

        folder_row = QHBoxLayout()
        self.local_folder_edit = QLineEdit(self._config.get("local_folder", ""))
        browse_btn = QPushButton("📁")
        browse_btn.setFixedWidth(36)
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(self.local_folder_edit)
        folder_row.addWidget(browse_btn)
        form.addRow("Folder docelowy *:", folder_row)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(5, 86400)
        self.interval_spin.setValue(self._config.get("interval_seconds", 60))
        self.interval_spin.setSuffix(" sekund")
        form.addRow("Interwał sprawdzania:", self.interval_spin)

        layout.addLayout(form)
        layout.addStretch()

        info = QLabel(
            "💡 Ustawienia są od razu widoczne dla serwisu — nie trzeba go restartować.\n"
            "Serwis czyta konfigurację na początku każdego cyklu."
        )
        info.setStyleSheet("color:#95a5a6;font-size:11px;")
        layout.addWidget(info)

        save_btn = QPushButton("💾 Zapisz ustawienia")
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet("background:#2980b9;color:white;border-radius:4px;font-weight:bold;")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        return w

    def _build_log_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_edit)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Odśwież log")
        refresh_btn.clicked.connect(self._load_service_log)
        clear_btn = QPushButton("🗑 Wyczyść widok")
        clear_btn.clicked.connect(self.log_edit.clear)
        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._load_service_log()
        return w

    def _build_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(self)
        tray.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        menu = QMenu()
        show_a = QAction("Pokaż panel", self)
        show_a.triggered.connect(self.show)
        quit_a = QAction("Zamknij panel", self)
        quit_a.triggered.connect(QApplication.quit)
        menu.addAction(show_a)
        menu.addSeparator()
        menu.addAction(quit_a)
        tray.setContextMenu(menu)
        tray.activated.connect(
            lambda r: self.show() if r == QSystemTrayIcon.DoubleClick else None
        )
        tray.show()
        return tray

    # ── Profile ──────────────────────────────────────────────────────────────

    def _populate_profiles(self):
        self.profiles_table.setRowCount(0)
        for p in self._config.get("profiles", []):
            row = self.profiles_table.rowCount()
            self.profiles_table.insertRow(row)
            self.profiles_table.setItem(row, 0, QTableWidgetItem(p.get("name", "")))
            self.profiles_table.setItem(row, 1, QTableWidgetItem(p.get("host", "")))
            self.profiles_table.setItem(row, 2, QTableWidgetItem(str(p.get("port", 21))))
            self.profiles_table.setItem(row, 3, QTableWidgetItem(p.get("user", "")))
            self.profiles_table.setItem(row, 4, QTableWidgetItem(p.get("remote_dir", "/")))
            ei = QTableWidgetItem("✔" if p.get("enabled", True) else "✖")
            ei.setTextAlignment(Qt.AlignCenter)
            self.profiles_table.setItem(row, 5, ei)

    def _add_profile(self):
        dlg = ProfileDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self._config.setdefault("profiles", []).append(dlg.get_profile())
            self._save_config()
            self._populate_profiles()

    def _edit_profile(self):
        row = self.profiles_table.currentRow()
        if row < 0: return
        dlg = ProfileDialog(self, self._config["profiles"][row])
        if dlg.exec_() == QDialog.Accepted:
            self._config["profiles"][row] = dlg.get_profile()
            self._save_config()
            self._populate_profiles()

    def _delete_profile(self):
        row = self.profiles_table.currentRow()
        if row < 0: return
        name = self._config["profiles"][row].get("name", "?")
        if QMessageBox.question(
            self, "Usuń profil", f"Na pewno usunąć '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            del self._config["profiles"][row]
            self._save_config()
            self._populate_profiles()

    # ── Serwis Windows ───────────────────────────────────────────────────────

    def _refresh_service_status(self):
        status = get_service_status()
        colors = {
            "Running":      "#2ecc71",
            "Stopped":      "#e74c3c",
            "Not Installed":"#95a5a6",
            "Starting...":  "#f39c12",
            "Stopping...":  "#f39c12",
        }
        icons = {
            "Running":      "▶ Running",
            "Stopped":      "⏹ Stopped",
            "Not Installed":"✖ Nie zainstalowany",
        }
        label = icons.get(status, status)
        color = colors.get(status, "#ecf0f1")
        self.svc_status_label.setText(label)
        self.svc_status_label.setStyleSheet(f"color:{color};")

        installed = status != "Not Installed"
        running   = status == "Running"
        self.install_btn.setEnabled(not installed)
        self.uninstall_btn.setEnabled(installed and not running)
        self.svc_start_btn.setEnabled(installed and not running)
        self.svc_stop_btn.setEnabled(running)

    def _install_service(self):
        if not is_admin():
            QMessageBox.warning(self, "Brak uprawnień",
                "Uruchom aplikację jako Administrator!")
            return
        ok, msg = run_as_admin(["install"])
        QMessageBox.information(self, "Instalacja serwisu", msg or ("OK" if ok else "Błąd"))
        self._refresh_service_status()

    def _uninstall_service(self):
        if not is_admin():
            QMessageBox.warning(self, "Brak uprawnień",
                "Uruchom aplikację jako Administrator!")
            return
        ok, msg = run_as_admin(["remove"])
        QMessageBox.information(self, "Odinstalowanie serwisu", msg or ("OK" if ok else "Błąd"))
        self._refresh_service_status()

    def _start_service(self):
        if not is_admin():
            QMessageBox.warning(self, "Brak uprawnień",
                "Uruchom aplikację jako Administrator!")
            return
        ok, msg = run_as_admin(["start"])
        self._refresh_service_status()

    def _stop_service(self):
        if not is_admin():
            QMessageBox.warning(self, "Brak uprawnień",
                "Uruchom aplikację jako Administrator!")
            return
        ok, msg = run_as_admin(["stop"])
        self._refresh_service_status()

    # ── Ustawienia ───────────────────────────────────────────────────────────

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder lokalny")
        if folder:
            self.local_folder_edit.setText(folder)

    def _save_settings(self):
        self._config["local_folder"]      = self.local_folder_edit.text().strip()
        self._config["interval_seconds"]  = self.interval_spin.value()
        self._save_config()
        QMessageBox.information(self, "Zapisano",
            "✔ Ustawienia zapisane. Serwis zastosuje je przy następnym cyklu.")

    # ── Log ──────────────────────────────────────────────────────────────────

    def _load_service_log(self):
        base    = os.path.dirname(os.path.abspath(
            sys.executable if getattr(sys, 'frozen', False) else __file__
        ))
        log_path = os.path.join(base, "ftp_monitor_service.log")
        if not os.path.exists(log_path):
            self.log_edit.setPlainText(f"Brak pliku logu:\n{log_path}")
            return
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            # ostatnie 500 linii
            content = "".join(lines[-500:])
            self.log_edit.setPlainText(content)
            # przewiń na dół
            sb = self.log_edit.verticalScrollBar()
            sb.setValue(sb.maximum())
        except Exception as e:
            self.log_edit.setPlainText(f"Błąd odczytu logu: {e}")

    # ── Config ───────────────────────────────────────────────────────────────

    def _load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"profiles": [], "interval_seconds": 60, "local_folder": ""}

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można zapisać konfiguracji:\n{e}")

    # ── Zamknięcie ───────────────────────────────────────────────────────────

    def closeEvent(self, event):
        event.accept()


# ════════════════════════════════════════════════════════════════════════════
#  Wejście
# ════════════════════════════════════════════════════════════════════════════
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FTP Monitor GUI")
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(28, 28, 30))
    palette.setColor(QPalette.WindowText,      QColor(230, 230, 230))
    palette.setColor(QPalette.Base,            QColor(18, 18, 20))
    palette.setColor(QPalette.AlternateBase,   QColor(38, 38, 40))
    palette.setColor(QPalette.Text,            QColor(230, 230, 230))
    palette.setColor(QPalette.Button,          QColor(48, 48, 52))
    palette.setColor(QPalette.ButtonText,      QColor(230, 230, 230))
    palette.setColor(QPalette.Highlight,       QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
