# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for Novelshop.

One-folder (onedir) build: the Qt libraries stay as separate files
next to the executable, which is what the LGPL asks for — a user
can swap the Qt DLLs for a different build. Run with:

    pyinstaller novelshop.spec

The result is dist/Novelshop/ (a folder). Zip that folder for
distribution; the executable inside is called Novelshop.

Notes on what gets bundled:
- The app's own files (LICENSE, icon, the two toolbar images) are
  added as data below, at the same relative paths they have in
  the project folder. novel_shop/resources.py resolves them from
  the bundle folder when frozen, and from the project folder
  when run from source.
- piper-tts is in requirements.txt, so it is installed during the
  build and bundled into the executable (the app imports it in a
  try/except, which PyInstaller follows). That is fine now that
  the app is LGPLv2.1-or-later — the combined executable is
  distributed under GPLv3 terms. The voice files (.onnx, ~63MB
  each) are NOT bundled: the user still downloads one separately
  and picks it in the app, exactly as in the source install.
- The WordNet data (for the dictionary) is NOT bundled either.
  It lives in the user's home folder (~/.wn_data), and the app
  greys the dictionary out when it is missing. A frozen user
  who wants the dictionary needs a Python with `wn` and its
  data, or the data bundled separately.
- The libraries' own data files ARE bundled: pyspellchecker's
  English dictionary and python-docx's default template are
  collected with collect_data_files. PyInstaller does not find
  them on its own (they are loaded at runtime with
  pkgutil.get_data), and without them the frozen app crashes
  on startup (spellchecker) or on export (python-docx).
- UPX is left off: compressing the Qt libraries would stop a
  user swapping them, which the LGPL relink rule relies on.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

project_root = Path(SPECPATH)

datas = [
    ("LICENSE", "."),
    ("novel_shop/icon.png", "novel_shop"),
    ("novel_shop/icon.ico", "novel_shop"),
    ("novel_shop/down_arrow.png", "novel_shop"),
    ("novel_shop/close.png", "novel_shop"),
]
# Package data files PyInstaller does not find on its own: the
# libraries load them at runtime with pkgutil.get_data, which the
# static analysis cannot see. Without them the frozen app crashes
# on startup (spellchecker) or on export (python-docx).
# - spellchecker: the English dictionary (resources/en.json.gz).
# - docx: the default document template (templates/default.docx).
datas += collect_data_files("spellchecker")
datas += collect_data_files("docx")

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Novelshop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Windowed: no console window on Windows/macOS.
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # The .ico is the Windows executable icon. macOS wants a .icns,
    # which the project does not have yet, so no icon is set there.
    icon="novel_shop/icon.ico" if sys.platform.startswith("win") else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Novelshop",
)
