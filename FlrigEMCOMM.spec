# PyInstaller recipe for FlrigEMCOMM.exe (one file, no console window).
# Used by build_windows.bat:   python -m PyInstaller FlrigEMCOMM.spec
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ["run.py"],
    pathex=["."],
    datas=[("flrig_emcomm/assets", "flrig_emcomm/assets"),
           ("flrig_emcomm/data", "flrig_emcomm/data")],
    hiddenimports=collect_submodules("flrig_emcomm"),
    excludes=["unittest", "pydoc", "doctest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="FlrigEMCOMM",
    icon="flrig_emcomm/assets/icon.ico",
    console=False,
    upx=False,
)
