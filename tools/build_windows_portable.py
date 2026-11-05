"""Cross-assemble a real Win64 GUI launcher plus official embedded Python.

No claim of Windows runtime validation: the build host may be macOS.
Artifacts are statically audited; run --self-test on Windows to verify there.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "windows"
DEST = ROOT / "dist" / "ContourNote-Windows-x64"
PYTHON_SHA256 = "9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38"
ARCHIVE_ROOT = "CN"
PACKAGE_REVISION = "release"
MAX_ARCHIVE_PATH = 120


def archive_path_audit(paths):
    """Leave room for Explorer's destination under the legacy 259-char limit."""
    paths = list(paths)
    lengths = [len(str(path).encode("utf-16-le")) // 2 for path in paths]
    longest = max(lengths, default=0)
    if longest > MAX_ARCHIVE_PATH:
        path = str(paths[lengths.index(longest)])
        raise RuntimeError(f"Windows archive path is too long ({longest}): {path}")
    return {"archive_root": ARCHIVE_ROOT, "max_relative_utf16_units": longest,
            "path_limit": MAX_ARCHIVE_PATH,
            "legacy_max_destination_utf16_units": 259 - longest - 1}


def main():
    runtime_zip = BUILD / "python-3.13.17-embed-amd64.zip"
    if hashlib.sha256(runtime_zip.read_bytes()).hexdigest() != PYTHON_SHA256:
        raise RuntimeError("Embedded Python checksum does not match the official release.")
    if DEST.exists() and "--resume" not in sys.argv:
        raise RuntimeError(f"Build destination already exists: {DEST}")
    runtime = DEST / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(runtime_zip) as z:
        z.extractall(runtime)
    site = runtime / "Lib" / "site-packages"
    site.mkdir(parents=True, exist_ok=True)
    wheels = sorted((BUILD / "wheels").glob("*.whl"))
    if len(wheels) != 5:
        raise RuntimeError("Expected the five pinned Windows dependency wheels.")
    hashes = {runtime_zip.name: PYTHON_SHA256}
    for wheel in wheels:
        hashes[wheel.name] = hashlib.sha256(wheel.read_bytes()).hexdigest()
        with zipfile.ZipFile(wheel) as z:
            for name in z.namelist():
                # Wheel packages are imported directly; build-time scripts aren't needed.
                if ".data/" in name:
                    if ".data/purelib/" in name or ".data/platlib/" in name:
                        name_target = name.split("lib/", 1)[1]
                    else:
                        continue
                else:
                    name_target = name
                if name.endswith("/"):
                    continue
                target = site / name_target
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
    # This application uses Qt Widgets, not QML/Qt Quick. The wheel includes
    # QML build objects with deeply nested names that break Explorer extraction.
    # Do this after every wheel extraction, including --resume builds.
    qml = site / "PySide6" / "qml"
    if qml.exists():
        shutil.rmtree(qml)
    for dll in (site / "PySide6").glob("*.dll"):
        if dll.name.lower().startswith(("msvcp", "vcruntime", "concrt")):
            shutil.copy2(dll, runtime / dll.name)
    (runtime / "python313._pth").write_text("python313.zip\n.\nLib/site-packages\n../app\nimport site\n", encoding="utf-8")
    app = DEST / "app"; app.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "clinical_annotator", app / "clinical_annotator", ignore=shutil.ignore_patterns("__pycache__"), dirs_exist_ok=True)
    shutil.copy2(ROOT / "tools" / "windows_bootstrap.py", app / "run.py")
    for name in ["LICENSE", "NOTICE.md"]:
        shutil.copy2(ROOT / name, DEST / name)
    environment = dict(os.environ)
    environment["ZIG_GLOBAL_CACHE_DIR"] = str(BUILD / "zig-global-cache")
    environment["ZIG_LOCAL_CACHE_DIR"] = str(BUILD / "zig-local-cache")
    subprocess.run([sys.executable, "-m", "ziglang", "cc", "-target", "x86_64-windows-gnu",
                    "-O2", "-municode", "-Wl,--subsystem,windows", str(ROOT / "tools" / "windows_launcher.c"),
                    "-o", str(DEST / "临绘.exe")], env=environment, cwd=ROOT, check=True)
    import pefile
    pe = pefile.PE(str(DEST / "临绘.exe"))
    assert pe.FILE_HEADER.Machine == 0x8664
    assert pe.OPTIONAL_HEADER.Subsystem == 2  # GUI, not a console program
    audit = audit_dependencies()
    archive_paths = [Path(ARCHIVE_ROOT) / p.relative_to(DEST)
                     for p in DEST.rglob("*") if p.is_file()]
    archive_paths += [Path(ARCHIVE_ROOT) / name
                      for name in ["build-manifest.json", "使用说明.txt"]]
    path_audit = archive_path_audit(archive_paths)
    (DEST / "build-manifest.json").write_text(json.dumps({"version": "0.5.2", "platform": "Windows x64",
        "python": "3.13.17", "sha256": hashes, "gui_launcher": True,
        "package_revision": PACKAGE_REVISION, "archive_path_audit": path_audit,
        "native_windows_validation": False, "dependency_audit": audit}, ensure_ascii=False, indent=2), encoding="utf-8")
    (DEST / "使用说明.txt").write_text(
        "临绘 0.5.2 · Windows 64 位便携版\n\n请解压整个文件夹，双击「临绘.exe」。无需安装 Python 或 pip。\n"
        "请勿单独移动 EXE，runtime 和 app 文件夹需保持在旁边。\n"
        "此为解压路径修复包：移除未使用的 QML 组件，压缩包内文件夹缩短为 CN。\n"
        "请使用本包重新完整解压到一个新文件夹，不要与旧包混用；避免放到过深的目录。\n"
        "已生成 Windows 原生 GUI 启动器，检查内置运行环境和依赖；当前构建环境为 macOS，尚未在 Windows 实机运行验收。\n"
        "窗口默认最大化；Shift+鼠标左键拖动连续采点；F5 放映/暂停；F11 全屏。\n"
        "遇到启动错误请提供 %LOCALAPPDATA%\\ContourNote\\startup.log。\n", encoding="utf-8-sig")
    archive = ROOT.parent / "ContourNote-Windows-x64-v0.5.2.zip"
    archive_path_audit(Path(ARCHIVE_ROOT) / p.relative_to(DEST)
                       for p in DEST.rglob("*") if p.is_file())
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(DEST.rglob("*")):
            if path.is_file(): z.write(path, Path(ARCHIVE_ROOT) / path.relative_to(DEST))
    print(archive)


def audit_dependencies():
    import pefile
    runtime = DEST / "runtime"
    all_files = {p.name.lower(): p for p in runtime.rglob("*") if p.suffix.lower() in {".dll", ".pyd", ".exe"}}
    system = {"kernel32.dll", "user32.dll", "gdi32.dll", "advapi32.dll", "shell32.dll", "ole32.dll",
              "oleaut32.dll", "ws2_32.dll", "winmm.dll", "imm32.dll", "comdlg32.dll", "comctl32.dll",
              "version.dll", "shlwapi.dll", "shcore.dll", "dwmapi.dll", "uxtheme.dll", "userenv.dll",
              "rpcrt4.dll", "bcrypt.dll", "ncrypt.dll", "crypt32.dll", "cryptbase.dll", "secur32.dll",
              "sspicli.dll", "netapi32.dll", "iphlpapi.dll", "dnsapi.dll", "msvcrt.dll", "ntdll.dll",
              "wtsapi32.dll", "d3d11.dll", "dxgi.dll", "dxguid.dll", "dwrite.dll", "d2d1.dll",
              "d3d9.dll", "opengl32.dll", "msimg32.dll", "normaliz.dll", "winhttp.dll", "wininet.dll",
              "powrprof.dll", "mpr.dll", "dhcpcsvc.dll", "wldap32.dll", "hid.dll", "setupapi.dll",
              "cfgmgr32.dll", "authz.dll", "winspool.drv", "propsys.dll", "ntmarta.dll", "wintrust.dll",
              "d3d12.dll", "icuuc.dll", "mscms.dll", "psapi.dll", "uiautomationcore.dll"}
    roots = [runtime / "pythonw.exe", runtime / "python313.dll", DEST / "临绘.exe"]
    roots += [p for p in runtime.rglob("*") if p.name.lower() in {"qtcore.pyd", "qtgui.pyd", "qtwidgets.pyd", "qwindows.dll"}]
    roots += list(runtime.rglob("*.pyd"))
    seen, missing = set(), set()
    pending = roots[:]
    while pending:
        path = pending.pop()
        if path in seen: continue
        seen.add(path)
        image = pefile.PE(str(path), fast_load=True)
        image.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
        for entry in getattr(image, "DIRECTORY_ENTRY_IMPORT", []):
            name = entry.dll.decode("ascii").lower()
            if name in all_files: pending.append(all_files[name])
            elif not (name in system or name.startswith(("api-ms-win-", "ext-ms-win-"))): missing.add(name)
        image.close()
    result = {"pe_files_checked": len(seen), "missing_non_system_dlls": sorted(missing)}
    print("Dependency audit:", result)
    if missing: raise RuntimeError(f"Unresolved Windows DLL imports: {sorted(missing)}")
    return result


if __name__ == "__main__":
    main()
