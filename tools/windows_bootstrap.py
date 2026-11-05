"""Entry point shipped alongside the embedded Windows Python runtime."""
import ctypes
import os
from pathlib import Path
import sys
import traceback

root = Path(__file__).resolve().parent.parent
site = root / "runtime" / "Lib" / "site-packages"
_dll_directories = []
for path in [root / "runtime", site / "PySide6", site / "shiboken6"]:
    if path.exists():
        _dll_directories.append(os.add_dll_directory(str(path)))
os.environ["QT_PLUGIN_PATH"] = str(site / "PySide6" / "plugins")
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(site / "PySide6" / "plugins" / "platforms")

if __name__ == "__main__":
    try:
        from clinical_annotator.app import main
        main()
    except SystemExit:
        raise
    except Exception:
        log = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ContourNote" / "startup.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        ctypes.windll.user32.MessageBoxW(None, f"启动失败，详情请查看：\n{log}", "临绘", 16)
        sys.exit(1)
