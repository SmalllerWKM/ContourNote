"""Build a self-contained Apple Silicon .app with its own Python and Qt."""
import os
import platform
import subprocess
import sys
import plistlib
import shutil
import importlib.metadata
from pathlib import Path

try:
    from tools.package_licenses import copy_licenses, prune_macos
except ModuleNotFoundError:
    from package_licenses import copy_licenses, prune_macos

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "macos"
DIST = ROOT / "dist"


def main():
    if sys.platform != "darwin":
        raise SystemExit("Build the macOS app on macOS.")
    BUILD.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((80, 80, 944, 944), radius=185, fill="#fafbfc", outline="#d7dee8", width=10)
    points = [(285, 315), (690, 270), (755, 680), (350, 755)]
    draw.polygon(points, fill="#e3edf9", outline="#4f76a6", width=28)
    for x, y in points:
        draw.ellipse((x-32, y-32, x+32, y+32), fill="#4f76a6", outline="#fafbfc", width=8)
    icon = BUILD / "ContourNote.icns"
    image.save(icon)
    environment = dict(os.environ)
    environment["PYINSTALLER_CONFIG_DIR"] = str(BUILD / "cache")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--onedir",
               "--name", "ContourNote", "--osx-bundle-identifier", "org.contournote.desktop",
               "--target-arch", platform.machine(), "--icon", str(icon),
               "--distpath", str(DIST), "--workpath", str(BUILD / "work"),
               "--specpath", str(BUILD), "--paths", str(ROOT),
               "--add-data", f"{ROOT / 'LICENSE'}:licenses",
               "--add-data", f"{ROOT / 'NOTICE.md'}:licenses",
               "--exclude-module", "pytest", "--exclude-module", "PySide6.QtWebEngineCore",
               "--exclude-module", "PySide6.QtWebEngineWidgets", "--exclude-module", "PySide6.QtQml",
               "--exclude-module", "PySide6.QtQuick", "--exclude-module", "tkinter", str(ROOT / "run.py")]
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    app = DIST / "ContourNote.app"
    metadata_path = app / "Contents" / "Info.plist"
    metadata = plistlib.loads(metadata_path.read_bytes())
    metadata.update(CFBundleName="临绘", CFBundleDisplayName="临绘 ContourNote",
                    CFBundleShortVersionString="1.0.0", CFBundleVersion="1.0.0")
    metadata_path.write_bytes(plistlib.dumps(metadata))
    prune_macos(app)
    copy_licenses(app / "Contents" / "Resources")
    licenses = app / "Contents" / "Resources" / "licenses"
    for name in ["PySide6", "PySide6_Essentials", "shiboken6", "numpy", "Pillow", "shapely", "pyinstaller"]:
        dist = importlib.metadata.distribution(name)
        for entry in dist.files or []:
            relative = Path(entry)
            if any("license" in p.lower() or p.lower() == "copying" for p in relative.parts) or relative.name == "METADATA":
                location = Path(dist.locate_file(entry))
                if location.is_file():
                    target = licenses / name / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(location, target)
    for name in ["LICENSE", "LICENSE.txt"]:
        path = Path(sys.base_prefix) / name
        if path.exists(): shutil.copy2(path, licenses / ("Python-" + name))
    subprocess.run(["/usr/bin/codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)
    subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    print(app)


if __name__ == "__main__":
    main()
