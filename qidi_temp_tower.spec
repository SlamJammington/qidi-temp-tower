# PyInstaller build recipe. Used by .github/workflows/release.yml; to build locally:
#   pip install pyinstaller
#   pyinstaller qidi_temp_tower.spec
# Output: dist/QidiTempTower.exe (Windows), dist/QidiTempTower.app (macOS), dist/QidiTempTower (Linux)
import re
import sys

version = re.search(r'__version__ = "([^"]+)"', open("qidi_temp_tower.py", encoding="utf-8").read()).group(1)

a = Analysis(
    ["qidi_temp_tower.py"],
    datas=[("assets/digits.json", "assets"), ("assets/icon.png", "assets"),
           ("LICENSE", "."), ("assets/LICENSE-DejaVu-font.txt", "assets")],
    excludes=["unittest", "pydoc", "doctest", "lib2to3", "pdb"],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="QidiTempTower",
    console=False,  # GUI app; qidi_temp_tower.attach_console() handles command-line use on Windows
    icon="assets/icon.icns" if sys.platform == "darwin" else "assets/icon.ico",
    upx=False,      # UPX-packed executables trip antivirus heuristics far more often
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="QidiTempTower.app",
        icon="assets/icon.icns",
        bundle_identifier="io.github.slamjammington.qiditemptower",
        version=version,
        info_plist={"NSHighResolutionCapable": True, "CFBundleDisplayName": "QIDI Temp Tower"},
    )
