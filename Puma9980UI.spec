# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('README.md', '.'),
        ('docs/OPERATOR_GUIDE.md', 'docs'),
        ('docs/SOURCE_ACCEPTANCE_CHECKLIST.md', 'docs'),
        ('docs/MANUAL_COVERAGE_MATRIX.md', 'docs'),
        ('docs/MANUAL_PAGE_AUDIT.md', 'docs'),
        ('docs/MANUAL_INTERACTION_ACCEPTANCE_2026-09-08.md', 'docs'),
        ('docs/UserManual-9980.pdf', 'docs'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
# Codex's document runtime adds Poppler's ICU 78 DLLs to PATH. Qt uses the
# Windows ICU shim, so bundling the Poppler copies breaks QtCore at startup.
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
    name='Puma9980UI',
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
    name='Puma9980UI',
)
