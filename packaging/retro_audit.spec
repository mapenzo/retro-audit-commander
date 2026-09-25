# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller definition for the Retro Audit Commander executable."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, copy_metadata


PROJECT_ROOT = Path(SPECPATH).resolve().parent

datas = [(str(PROJECT_ROOT / "pyproject.toml"), ".")]
datas += collect_data_files("pyfiglet")
datas += copy_metadata("hacking")
datas += copy_metadata("paramiko")
datas += copy_metadata("textual")


analysis = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="retro-audit",
    console=True,
)

distribution = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name="retro-audit",
)