# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs,
)
from PyInstaller.building.build_main import Analysis, PYZ, EXE

project_dir = Path.cwd()
site_packages = project_dir / '.venv' / 'Lib' / 'site-packages'
pyqt5_dir = site_packages / 'PyQt5'
qt5_dir = pyqt5_dir / 'Qt5'
plugins_dir = qt5_dir / 'plugins'
translations_dir = qt5_dir / 'translations'

datas = [
    ('config.json', '.'),
    ('patterns/*.csv', 'patterns'),
    ('app.manifest', '.'),
]

binaries = []
hiddenimports = []

# Project modules
hiddenimports += collect_submodules('core')
hiddenimports += collect_submodules('data')
hiddenimports += collect_submodules('ui')

# Theme package
datas += collect_data_files('qdarktheme')
hiddenimports += collect_submodules('qdarktheme')

# PyQt5 base modules
hiddenimports += [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
]

# Common hidden imports for this project
hiddenimports += [
    'matplotlib',
    'matplotlib.backends.backend_qt5agg',
    'matplotlib.backends.backend_agg',
    'numpy',
    'dxcam',
    'watchdog',
    'watchdog.observers',
    'watchdog.events',
    'win32api',
    'win32con',
    'win32gui',
    'win32com',
    'win32com.client',
    'pythoncom',
    'pywintypes',
]

# Collect package resources and dynamic libraries
datas += collect_data_files('PyQt5')
binaries += collect_dynamic_libs('PyQt5')
datas += collect_data_files('matplotlib')
datas += collect_data_files('numpy')
datas += collect_data_files('dxcam')
datas += collect_data_files('watchdog')

# Manually include Qt plugins using tuple format that Analysis accepts
plugin_subdirs = [
    'platforms',
    'styles',
    'imageformats',
    'iconengines',
    'platformthemes',
    'printsupport',
]

for name in plugin_subdirs:
    src = plugins_dir / name
    if src.exists():
        binaries.append((str(src / '*'), f'PyQt5/Qt5/plugins/{name}'))

if translations_dir.exists():
    datas.append((str(translations_dir / '*'), 'PyQt5/Qt5/translations'))

a = Analysis(
    ['main.py'],
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CS2_RCS_Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico',
    version='version_info.txt',
    uac_admin=True,
    manifest='app.manifest',
    onefile=True,
)
