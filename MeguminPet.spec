# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')]+collect_data_files('live2d',includes=['FrameworkShaders/*'])+collect_data_files('vosk',includes=['libvosk.dll']),
    hiddenimports=['OpenGL.platform.win32','live2d._live2d'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml', 'PySide6.QtQuick'],
    noarchive=False,
    optimize=0,
)
# Windows provides these system libraries. Other tools on PATH may contain incompatible ICU builds.
a.binaries = [entry for entry in a.binaries if not (entry[0].replace('\\', '/').split('/')[-1].lower().startswith(('api-ms-win-', 'icudt')) or entry[0].replace('\\', '/').split('/')[-1].lower() in ('icuuc.dll', 'ucrtbase.dll'))]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MeguminPet-Live2D-v23',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'],
)



