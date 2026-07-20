# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Icono de ventana en tiempo de ejecución (iconbitmap necesita el .ico en disco)
datas += [('img\\iconoSems.ico', 'img')]


a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Modo onedir (EXE + COLLECT): evita la autoextracción a %TEMP% del modo onefile,
# que las heurísticas antivirus tratan como comportamiento de dropper/packer.
# UPX desactivado: la compresión de ejecutables es un disparador clásico de falsos positivos.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Envio_Masivo_Seguro',
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
    icon='img\\iconoSems.ico',
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Envio_Masivo_Seguro',
)
