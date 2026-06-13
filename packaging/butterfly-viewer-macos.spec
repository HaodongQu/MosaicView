# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()
ROOT = SPEC_DIR if (SPEC_DIR / "pyproject.toml").exists() else SPEC_DIR.parent


a = Analysis(
    [str(ROOT / "packaging" / "pyinstaller_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (
            str(ROOT / "butterfly_viewer" / "icons"),
            "butterfly_viewer/icons",
        ),
    ],
    hiddenimports=["PyQt5.sip"],
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
    name="Butterfly Viewer",
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
    icon=str(ROOT / "butterfly_viewer" / "icons" / "icon.icns"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Butterfly Viewer",
)
app = BUNDLE(
    coll,
    name="Butterfly Viewer.app",
    icon=str(ROOT / "butterfly_viewer" / "icons" / "icon.icns"),
    bundle_identifier="com.olivegroves.butterflyviewer",
    info_plist={
        "CFBundleName": "Butterfly Viewer",
        "CFBundleDisplayName": "Butterfly Viewer",
        "CFBundleShortVersionString": "1.1.0",
        "CFBundleVersion": "1.1.0",
        "NSHighResolutionCapable": "True",
    },
)
