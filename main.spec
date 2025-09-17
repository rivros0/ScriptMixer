# per eseguirlo pyinstaller main.spec

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],                # file di ingresso (il tuo programma principale)
    pathex=[],
    binaries=[],
    datas=[
        # Aggiungi qui eventuali file extra che vuoi includere
        # Esempio: ('config/config.json', 'config'),
        # ('templates/', 'templates'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Smixer',             # nome dell’eseguibile
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,              # False → non apre la console nera (utile per Tkinter)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None                   # Se vuoi un’icona: "icone/app.ico"
)
