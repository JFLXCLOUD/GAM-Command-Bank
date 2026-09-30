# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller build for GAM Command Bank.
#
#   pyinstaller GAM_Command_Bank.spec
#       -> dist/GAM_Command_Bank.exe        single-file portable exe
#
#   set GCB_ONEDIR=1  (PowerShell: $env:GCB_ONEDIR = "1")
#   pyinstaller GAM_Command_Bank.spec
#       -> dist/GAM_Command_Bank/           folder used by the Windows installer
#                                           (starts faster: nothing to unpack)
import os

ONEDIR = os.environ.get("GCB_ONEDIR") == "1"

a = Analysis(
    ['command_bank.py'],
    pathex=[],
    binaries=[],
    datas=[('commands.json', '.'), ('icon.ico', '.'), ('assets/icon-*.png', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe_options = dict(
    name='GAM_Command_Bank',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
    version='version_info.txt',
)

if ONEDIR:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exe_options)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[],
                   name='GAM_Command_Bank')
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], runtime_tmpdir=None, **exe_options)
