@echo off
chcp 65001 >nul
setlocal

echo ==========================================
echo Build CS2_RCS_Tool Release (Python 3.13)
echo ==========================================

echo [1/7] Checking project path...
echo Current path: %cd%
echo.
echo IMPORTANT:
echo 1. Place this project in an English-only path, for example:
echo    C:\build\cs2_rcs_tool
echo 2. Do not build from a Chinese path.
echo.

echo [2/7] Clean old outputs...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/7] Recreate virtual environment with Python 3.13...
if exist .venv rmdir /s /q .venv
py -3.13 -m venv .venv
if errorlevel 1 (
    echo ERROR: Python 3.13 was not found. Run: py -0p
    pause
    exit /b 1
)

echo [4/7] Activate environment...
call .venv\Scripts\activate.bat

echo [5/7] Install dependencies...
python -m pip install --upgrade pip setuptools wheel
pip uninstall -y PyQt5 PyQt5-Qt5 PyQt5-sip >nul 2>nul
pip install -r requirements.txt
pip install pyinstaller
pip install --no-cache-dir --force-reinstall PyQt5

echo [Check] Verify Qt plugin folders...
if not exist ".venv\Lib\site-packages\PyQt5\Qt5\plugins" (
    echo ERROR: PyQt5 Qt plugin folder not found.
    pause
    exit /b 1
)
if not exist ".venv\Lib\site-packages\PyQt5\Qt5\plugins\platforms\qwindows.dll" (
    echo ERROR: qwindows.dll not found.
    pause
    exit /b 1
)

echo [6/7] Build executable...
pyinstaller --clean --noconfirm build.spec
if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)

echo [7/7] Done.
echo Output: dist\CS2_RCS_Tool.exe
echo This build is configured as:
echo - onefile
echo - no console
echo - admin privilege prompt
echo - icon enabled
echo - version info enabled
pause
