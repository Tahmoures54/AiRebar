#!/usr/bin/env python3
"""Build a standalone RebarAgent executable with PyInstaller."""
from __future__ import annotations
import os, platform, subprocess, sys

def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not installed. Run:  pip install pyinstaller")
        return 1
    name = "RebarAgent"
    icon = os.path.join(root, "app_icon.ico")
    separator = ";" if platform.system() == "Windows" else ":"
    datas = [f"app_config.json{separator}.", f"User_Guide.html{separator}."]
    if os.path.isfile(icon):
        datas.append(f"app_icon.ico{separator}.")
    hidden = ["pulp", "mip", "pandas", "openpyxl", "reportlab", "svgwrite", "numpy"]
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", name, "--paths", root]
    if os.path.isfile(icon):
        cmd.extend(["--icon", icon])
    for d in datas:
        cmd.extend(["--add-data", d])
    for h in hidden:
        cmd.extend(["--hidden-import", h])
    cmd.append("main.py")
    print("Running:", " ".join(cmd))
    result = subprocess.call(cmd)
    if result == 0:
        print(f"Build OK → dist/{name}/")
    return result

if __name__ == "__main__":
    raise SystemExit(main())
