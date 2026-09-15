# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['key_generator.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
a.binaries = type(a.binaries)(
    entry
    for entry in a.binaries
    if entry[0].replace('\\', '/').rsplit('/', 1)[-1].lower()
    not in {'icuuc.dll', 'icudt78.dll'}
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='Puma9980KeyGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
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
    upx=False,
    upx_exclude=[],
    name='Puma9980KeyGenerator',
)

