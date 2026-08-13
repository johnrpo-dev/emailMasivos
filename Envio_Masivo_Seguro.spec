# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# ── customtkinter: recursos de tema (.json) y assets que no se detectan solos ──
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# ── pikepdf: extensión binaria (_core) + libqpdf ──
tmp_ret = collect_all('pikepdf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# ── keyring: CRÍTICO ──────────────────────────────────────────────────────────
# keyring descubre sus backends en TIEMPO DE EJECUCIÓN vía entry points
# (keyring.backend._load_plugins usa importlib.metadata). El análisis estático de
# PyInstaller no puede seguir esas importaciones dinámicas, por lo que el .exe
# empaquetado lanza "No recommended backend was available" y deja inoperantes
# tanto la activación de licencia como el guardado de credenciales SMTP.
# Se fuerza la inclusión de todos los backends y de sus metadatos.
tmp_ret = collect_all('keyring')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
hiddenimports += collect_submodules('keyring.backends')
hiddenimports += [
    'keyring.backends.Windows',
    'keyring.backends.chainer',
    'keyring.backends.fail',
    'keyring.backends.null',
    'win32ctypes.core',
    'win32ctypes.core.cffi',
    'win32ctypes.core.ctypes',
    'win32ctypes.pywin32',
    'win32ctypes.pywin32.win32cred',
]

# ── cryptography: backend Ed25519 para la validación de licencia ──
hiddenimports += [
    'cryptography',
    'cryptography.hazmat.backends.openssl',
    'cryptography.hazmat.primitives.asymmetric.ed25519',
    'cryptography.hazmat.primitives.serialization',
]

# ── pandas: motor de lectura CSV ──
hiddenimports += [
    'pandas',
    'pandas._libs.tslibs.base',
    'pandas.io.formats.string',
]

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
    # Se excluyen dependencias pesadas que arrastra pandas pero que la app no usa.
    # Reduce el tamaño del paquete y la superficie de análisis.
    excludes=[
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
    ],
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
