#!/usr/bin/env python3
"""
Create Windows .ico icon from ResearchBot.png.
Activates venv if present, installs Pillow if needed.
"""

import os
import sys
import subprocess
from pathlib import Path

# Try to activate venv if it exists
project_root = Path(__file__).resolve().parent
venv_paths = [
    project_root / "venv",
    project_root / ".venv",
    project_root / "rBot",  # from .gitignore
]

for venv_path in venv_paths:
    if venv_path.exists():
        if sys.platform == "win32":
            venv_python = venv_path / "Scripts" / "python.exe"
            venv_pip = venv_path / "Scripts" / "pip.exe"
        else:
            venv_python = venv_path / "bin" / "python"
            venv_pip = venv_path / "bin" / "pip"
        
        if venv_python.exists():
            print(f"Using venv: {venv_path}")
            # Use venv's Python for the rest of the script
            if sys.executable != str(venv_python):
                # Re-run with venv Python
                subprocess.run([str(venv_python), __file__], check=True)
                sys.exit(0)
        break

# Check if Pillow is installed
try:
    from PIL import Image
except ImportError:
    print("Pillow not found. Installing...")
    pip_cmd = [sys.executable, "-m", "pip", "install", "pillow"]
    subprocess.run(pip_cmd, check=True)
    from PIL import Image

# Create .ico from PNG
assets_dir = project_root / "assets"
png_path = assets_dir / "ResearchBot.png"
ico_path = assets_dir / "ResearchBot.ico"

if not png_path.exists():
    print(f"Error: {png_path} not found!")
    sys.exit(1)

print(f"Reading {png_path}...")
img = Image.open(png_path)

# Create .ico with multiple sizes
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
images = []

for size in sizes:
    resized = img.resize(size, Image.Resampling.LANCZOS)
    images.append(resized)

print(f"Creating {ico_path}...")
images[0].save(
    ico_path,
    format='ICO',
    sizes=[(img.width, img.height) for img in images],
    append_images=images[1:]
)

print(f"Success! Created {ico_path}")
