@echo off
chcp 65001 >nul
echo ====================================
echo Building RCS single EXE...
echo ====================================

pyinstaller --noconsole --onefile ^
  --add-data "patterns;patterns" ^
  --hidden-import win32api ^
  --hidden-import pynput ^
  --hidden-import win32con ^
  --hidden-import win32security ^
  --hidden-import win32process ^
  --hidden-import PyQt5 ^
  --hidden-import PyQt5.QtCore ^
  --hidden-import PyQt5.QtWidgets ^
  --hidden-import numpy ^
  --name "RCS" ^
  main.py

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS: dist\RCS.exe created
) else (
    echo.
    echo FAILED: build error
)
pause
