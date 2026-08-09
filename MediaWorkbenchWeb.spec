# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: zero-dep local web workbench (onedir).

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

project_dir = Path(SPECPATH).resolve()

hidden = []
for pkg in (
    "uvicorn",
    "fastapi",
    "starlette",
    "pydantic",
    "anyio",
    "textgrid",
    "app",
):
    try:
        hidden += collect_submodules(pkg)
    except Exception:
        pass

hidden += [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "app.main",
    "app.worker",
    "app.config",
    "app.store",
    "app.dispatcher",
    "app.converter",
    "app.cme",
    "app.media",
    "app.paths",
    "app.schemas",
    "app.textgrid_ops",
    "app.healthcheck",
]

datas = [
    (str(project_dir / "app" / "static"), "app/static"),
    (str(project_dir / ".env.local.example"), "."),
]

# Optional icon (from sibling MediaConverter if present)
icon_path = project_dir / "icon.ico"
if not icon_path.is_file():
    sibling = project_dir.parent / "MediaConverter" / "icon.ico"
    if sibling.is_file():
        icon_path = sibling

a = Analysis(
    [str(project_dir / "launcher.py")],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "PySide6", "PyQt5"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MediaWorkbenchWeb",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=str(icon_path) if icon_path.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MediaWorkbenchWeb",
)
