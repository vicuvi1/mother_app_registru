# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Registru Digital Bibliotecă."""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)
APP = ROOT / "app"

a = Analysis(
    [str(APP / "main.py")],
    pathex=[str(APP)],
    binaries=[],
    datas=[
        (str(APP / "resources" / "stylesheet.qss"), "resources"),
        (str(APP / "resources" / "stylesheet_dark.qss"), "resources"),
        (str(APP / "resources" / "fonts"), "resources/fonts"),
    ],
    hiddenimports=[
        "sqlalchemy.dialects.sqlite",
        "openpyxl",
        "docx",
        "reportlab",
        "cryptography",
        "ui.widgets.table.delegates.checkbox_delegate",
        "ui.widgets.table.delegates.responsabil_delegate",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RegistruDigital",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="RegistruDigital",
)
