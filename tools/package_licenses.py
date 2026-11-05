"""Ship the legal bundle and retain only Qt Widgets runtime dependencies."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_REVISION = "licensefix1"
MAC_EXCLUDED = ("QtPdf", "QtVirtualKeyboard", "QtQml", "QtQuick")


def copy_licenses(destination):
    source = ROOT / "licenses"
    for name in ("LGPL-3.0-only.txt", "GPL-3.0-only.txt", "manifest.json"):
        if not (source / name).is_file():
            raise RuntimeError(f"Missing release license material: {name}")
    shutil.copytree(source, Path(destination) / "licenses", dirs_exist_ok=True)
    for name in ("LICENSE", "NOTICE.md", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, Path(destination) / name)


def prune_macos(app):
    contents = Path(app) / "Contents"
    # These plugins pull PDF/virtual-keyboard and QML runtimes into a Widgets app.
    # They are unused by this image annotator and are not distributed in this revision.
    for path in sorted(contents.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.name.startswith(MAC_EXCLUDED) or path.name in {
            "libqpdf.dylib", "libqtvirtualkeyboardplugin.dylib"
        }:
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)


def prune_windows(runtime):
    import pefile
    runtime = Path(runtime)
    site = runtime / "Lib" / "site-packages"
    pyside = site / "PySide6"
    keep_bindings = {"QtCore.pyd", "QtGui.pyd", "QtWidgets.pyd"}
    for path in pyside.glob("*.pyd"):
        if path.name not in keep_bindings:
            path.unlink()
    allowed_plugins = {"platforms", "styles", "imageformats", "iconengines"}
    plugins = pyside / "plugins"
    for directory in plugins.iterdir():
        if directory.is_dir() and directory.name not in allowed_plugins:
            shutil.rmtree(directory)
    for path in plugins.rglob("*pdf*"):
        if path.is_file():
            path.unlink()
    # Determine DLL closure from the actual bindings and retained plugins.
    files = {p.name.lower(): p for p in runtime.rglob("*")
             if p.suffix.lower() in {".dll", ".pyd"}}
    pending = list(pyside.glob("*.pyd")) + list(plugins.rglob("*.dll"))
    seen = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        image = pefile.PE(str(path), fast_load=True)
        image.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
        for entry in getattr(image, "DIRECTORY_ENTRY_IMPORT", []):
            dependency = files.get(entry.dll.decode("ascii").lower())
            if dependency:
                pending.append(dependency)
        image.close()
    for path in pyside.glob("Qt6*.dll"):
        if path not in seen:
            path.unlink()
    for directory in ("qml", "include", "typesystems", "translations", "scripts", "glue"):
        path = pyside / directory
        if path.is_dir():
            shutil.rmtree(path)
    for pattern in ("*.exe", "*.lib", "*.prl", "*.pdb"):
        for path in pyside.rglob(pattern):
            path.unlink()
    remaining = sorted(p.name for p in pyside.glob("Qt6*.dll"))
    allowed = {"Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "Qt6Svg.dll",
               "Qt6OpenGL.dll", "Qt6DBus.dll", "Qt6Network.dll"}
    if set(remaining) - allowed:
        raise RuntimeError(f"Unreviewed Qt libraries remain: {remaining}")
    return remaining
