"""
Build ImBridge into a Windows executable using PyInstaller.

Usage:
    python scripts/build_exe_windows.py

Requirements:
    - PyInstaller must be installed (pip install pyinstaller)
    - Run from the project root directory
    - External tools (Ghostscript, pstoedit, Potrace, libcairo-2.dll) are NOT bundled; users must install them separately
"""
import subprocess
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, "main.py")
DIST_PATH = os.path.join(PROJECT_ROOT, "dist")
BUILD_PATH = os.path.join(PROJECT_ROOT, "build")

# PyInstaller options
PYINSTALLER_OPTS = [
    "--onefile",  # single exe
    "--windowed", # no console window (for GUI)
    f"--distpath={DIST_PATH}",
    f"--workpath={BUILD_PATH}",
    "--name=ImBridge",
    # Add data files if needed, e.g. configs, docs
    "--add-data=requirements.txt;.",
    "--add-data=configs;configs",
    "--add-data=docs;docs",
    "--add-data=output;output",
]

# Build command
cmd = [sys.executable, "-m", "PyInstaller", *PYINSTALLER_OPTS, MAIN_SCRIPT]

print("Building ImBridge executable for Windows...")
print("Command:", " ".join(cmd))

try:
    subprocess.run(cmd, check=True)
    print(f"Build complete! Find your exe in: {DIST_PATH}")
    print("Note: External tools (Ghostscript, pstoedit, Potrace, libcairo-2.dll) must be installed separately and available in PATH.")
except subprocess.CalledProcessError as e:
    print("Build failed:", e)
    sys.exit(1)
