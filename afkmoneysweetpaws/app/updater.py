"""
Prosty system aktualizacji.
Sprawdza zdalny version.json i pobiera nowy plik programu.
"""
import json
import os
import sys
import urllib.request
import tempfile
import shutil
import subprocess
# === KONFIGURACJA AKTUALIZACJI ===
# Zmień na swoje URL (np. GitHub raw / własne hosting)
UPDATE_URL = "https://raw.githubusercontent.com/PIWKO-bip/discord-afk-panel/tree/main/version.json"
CURRENT_VERSION = "1.0.0"


def _parse_ver(v):
    parts = []
    for p in str(v).split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts + [0, 0, 0])[:3]


def get_exe_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def check_for_update(timeout=8):
    """
    Zwraca dict z info o aktualizacji albo None.
    Oczekiwany format version.json:
    {
      "version": "1.0.1",
      "url": "https://.../DiscordAFKPanel.exe",
      "changelog": "Opis zmian",
      "mandatory": false
    }
    """
    try:
        req = urllib.request.Request(
            UPDATE_URL,
            headers={"User-Agent": "DiscordAFKPanel-Updater"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        remote = str(data.get("version", "0"))
        if _parse_ver(remote) > _parse_ver(CURRENT_VERSION):
            return data
    except Exception:
        return None
    return None


def download_update(url, dest_path, progress_callback=None):
    """Pobiera plik aktualizacji."""
    req = urllib.request.Request(url, headers={"User-Agent": "DiscordAFKPanel-Updater"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        read = 0
        chunk = 64 * 1024
        with open(dest_path, "wb") as f:
            while True:
                data = resp.read(chunk)
                if not data:
                    break
                f.write(data)
                read += len(data)
                if progress_callback and total:
                    progress_callback(read / total)


def apply_update_and_restart(new_file_path):
    """
    Podmienia .exe i restartuje.
    Na Windows używa bat helpera, bo nie można nadpisać działającego exe.
    """
    if not getattr(sys, "frozen", False):
        # Tryb deweloperski – tylko informacja
        return False, "Aktualizacja pliku .exe działa tylko w zbudowanej wersji."

    current_exe = sys.executable
    bat_path = os.path.join(tempfile.gettempdir(), "afk_update.bat")

    # Skrypt: czekaj aż proces padnie, nadpisz, uruchom, usuń bat
    bat = f"""@echo off
:wait
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq {os.path.basename(current_exe)}" | find /I "{os.path.basename(current_exe)}" >nul
if not errorlevel 1 goto wait
copy /Y "{new_file_path}" "{current_exe}" >nul
start "" "{current_exe}"
del "%~f0"
"""
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat)

    subprocess.Popen(["cmd", "/c", bat_path], close_fds=True)
    return True, "Restartuję w celu aktualizacji..."
