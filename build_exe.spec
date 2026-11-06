# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file untuk Depo Air - Sistem Kasir
Build: pyinstaller build_exe.spec
"""

import os

block_cipher = None

# Path ke folder project
project_dir = os.path.dirname(os.path.abspath(SPECPATH))

a = Analysis(
    ['main.py'],
    pathex=[project_dir],
    binaries=[],
    datas=[
        # Sertakan gambar logo
        (os.path.join('views', 'img', 'Aria_Depo.jpeg'), os.path.join('views', 'img')),
        (os.path.join('views', 'img', 'DepoAir.ico'), os.path.join('views', 'img')),
    ],
    hiddenimports=[
        'database',
        'styles',
        'views',
        'views.login',
        'views.dashboard',
        'views.products',
        'views.customers',
        'views.transaction',
        'views.expenses',
        'views.reports',
        'views.users',
        'views.courier',
        'views.flowmeter',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL.ImageChops',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude modul besar yang tidak dibutuhkan agar EXE ringan
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
        'unittest',
        'doctest',
        'pydoc',
        'tkinter.test',
        'lib2to3',
        'xmlrpc',
        'pdb',
        'profile',
        'cProfile',
        'ensurepip',
        'venv',
        'distutils',
        'curses',
    ],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DepoAir',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Tanpa console window (GUI only)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join('views', 'img', 'DepoAir.ico'),
)
