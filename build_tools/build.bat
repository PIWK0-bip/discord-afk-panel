@echo off
chcp 65001 >nul
echo ============================================
echo   Budowanie Discord AFK Panel (.exe)
echo ============================================
echo.

cd /d "%~dp0.."

echo [1/3] Instalacja zaleznosci...
python -m pip install -r requirements.txt pyinstaller --quiet
if errorlevel 1 (
  echo Blad instalacji pakietow.
  pause
  exit /b 1
)

echo [2/3] Budowanie exe (moze potrwac 1-3 min)...
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "DiscordAFKPanel" ^
  --paths app ^
  --add-data "app/updater.py;." ^
  app/main.py

if errorlevel 1 (
  echo Blad budowania.
  pause
  exit /b 1
)

echo [3/3] Gotowe!
echo.
echo Plik:
echo   dist\DiscordAFKPanel.exe
echo.
echo Mozesz wyslac ten plik znajomemu.
echo Aby dzialaly aktualizacje, ustaw UPDATE_URL w app\updater.py
echo i wrzuc version.json + nowe exe na hosting/GitHub Releases.
echo.
pause
