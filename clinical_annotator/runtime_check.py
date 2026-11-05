"""Opt-in frozen-application smoke check; never runs during normal startup."""
import json
import sys
import traceback
from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QApplication

from . import __version__
from .data import atomic_json, export_dataset


def run_check(app, window, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    report = {"version": __version__, "frozen": bool(getattr(sys, "frozen", False)),
              "executable": sys.executable, "runtime": sys.prefix}
    try:
        image = output / "synthetic.png"
        Image.new("RGB", (320, 240), "#717c89").save(image)
        assert window.open_path(image)
        window.register_category("运行验证")
        window.label_input.setCurrentText("运行验证")
        window.set_tool("rectangle")
        window.canvas.draft = [[20, 20], [150, 130]]
        window.canvas.finish()
        saved = json.loads(image.with_suffix(".json").read_text(encoding="utf-8"))
        assert saved["shapes"][0]["label"] == "运行验证"
        assert saved["shapes"][0]["flags"]["weak"]
        result = export_dataset([window.doc], output / "export")
        assert len(result["annotations"]) == 1
        assert (output / "export" / "masks").exists()
        QApplication.processEvents()
        assert window.grab().save(str(output / "window.png"))
        report.update(ok=True, json_saved=True, coco_exported=True, window_rendered=True)
        atomic_json(output / "report.json", report)
        window.close()
        app.exit(0)
    except Exception:
        report.update(ok=False, error=traceback.format_exc())
        atomic_json(output / "report.json", report)
        window.hide()
        app.exit(1)
