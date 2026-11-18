"""
Build script to compile GSTR-1 Master Suite into a standalone Windows executable.
Collects all Playwright, PySide6, Pandas, and OpenPyXL dependencies into a self-contained package.
"""
import os
import sys
import shutil
import zipfile
from pathlib import Path
import PyInstaller.__main__

base_dir = Path(__file__).resolve().parent

print("=============================================================")
print("   BUILDING STANDALONE GSTR-1 MASTER SUITE EXECUTABLE        ")
print("=============================================================")

# Clean prior builds
build_dir = base_dir / "build"
dist_dir = base_dir / "dist"
if build_dir.exists():
    shutil.rmtree(build_dir, ignore_errors=True)
if dist_dir.exists():
    shutil.rmtree(dist_dir, ignore_errors=True)

# PyInstaller command line arguments
pyinstaller_args = [
    str(base_dir / "run.py"),
    "--name=GSTR1_Master_Suite",
    "--noconsole",
    "--onefile",
    "--clean",
    "--collect-all=playwright",
    "--collect-all=playwright_stealth",
    "--collect-all=openpyxl",
    "--collect-all=pandas",
    "--hidden-import=playwright.sync_api",
    "--hidden-import=playwright_stealth",
    "--hidden-import=openpyxl",
    "--hidden-import=pandas",
    "--hidden-import=PySide6.QtCore",
    "--hidden-import=PySide6.QtGui",
    "--hidden-import=PySide6.QtWidgets",
    f"--distpath={dist_dir}",
    f"--workpath={build_dir}",
]

print("Running PyInstaller to compile single-file executable...")
PyInstaller.__main__.run(pyinstaller_args)

exe_output = dist_dir / "GSTR1_Master_Suite.exe"
if exe_output.exists():
    size_mb = exe_output.stat().st_size / (1024 * 1024)
    print(f"\n[OK] Single Standalone Executable generated: {exe_output} ({size_mb:.1f} MB)")

    # Provide a starter .env in dist for convenience
    env_src = base_dir / ".env"
    if env_src.exists():
        shutil.copy2(env_src, dist_dir / ".env")

    readme_text = """============================================================
   UNIFIED GSTR-1 DOWNLOADER & EXCEL MASTER SUITE
============================================================

STANDALONE EXECUTABLE:
You can copy JUST 'GSTR1_Master_Suite.exe' anywhere!
No folder, no zip, and no Python installation needed.

HOW TO USE:
1. Double-click 'GSTR1_Master_Suite.exe' to launch the GUI.
2. In the 'Settings & .env Manager' tab, configure your GST portal credentials or WhiteBooks API keys.
3. Select your target period (Quarter, Financial Year, Single Month, or Custom).
4. Run your desired download and conversion workflow.

BROWSER AUTOMATION NOTE:
- On any Windows 10 or Windows 11 machine, this application automatically uses your installed Microsoft Edge or Google Chrome browser.
- No Python or manual browser installations required!
"""
    (dist_dir / "README.txt").write_text(readme_text, encoding="utf-8")
    print("[ALL DONE] Standalone .exe ready to run anywhere on its own!")
else:
    print("\n[X] Build failed: Standalone executable not found.")
