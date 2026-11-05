"""Generate deterministic, non-medical demonstration fixtures and UI previews."""
import math
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from clinical_annotator.data import Document, Shape, atomic_json


def generate():
    directory = ROOT / "demo"
    directory.mkdir(exist_ok=True)
    for frame in range(3):
        width, height = 960, 680
        yy, xx = np.mgrid[:height, :width]
        texture = np.sin(xx/71)*5+np.cos(yy/61)*4
        rgb = np.stack([52+texture+xx/50, 66+texture+yy/80, 82+texture], axis=-1)
        image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
        draw = ImageDraw.Draw(image)
        for x in range(0, width, 80):
            draw.line([(x, 0), (x, height)], fill=(72, 85, 103))
        for y in range(0, height, 80):
            draw.line([(0, y), (width, y)], fill=(72, 85, 103))
        top, bottom = [], []
        for x in range(150, 811, 15):
            center = 335+58*math.sin((x-150)/150+frame*.08)
            radius = 32+9*math.sin(x/130)
            top.append([x, center-radius])
            bottom.append([x, center+radius])
        outline = top+bottom[::-1]
        draw.polygon([tuple(p) for p in outline], fill=(164, 136, 112), outline=(211, 183, 147), width=3)
        draw.rounded_rectangle((25, 25, 490, 74), radius=7, fill=(31, 44, 60))
        draw.text((40, 44), "SYNTHETIC DEMO / NO PATIENT DATA", fill=(202, 215, 231))
        draw.text((35, height-35), "A: contour   B: box   P: point   Shift + left drag: sample", fill=(185, 204, 219))
        path = directory / f"demo_{frame+1:03d}.png"
        image.save(path)
        doc = Document(path.resolve(), width, height)
        if frame == 0:
            doc.shapes = [Shape("组织 A", outline),
                          Shape("组织 B", [[630, 225], [800, 405]], "rectangle", flags={"weak": True}),
                          Shape("组织 A", [[400, 385]], "point", flags={"weak": True})]
        elif frame == 1:
            doc.shapes = [Shape("组织 A", [[375, 370]], "point", flags={"weak": True}),
                          Shape("组织 B", [[650, 235], [800, 410]], "rectangle", flags={"weak": True})]
        else:
            doc.shapes = [Shape("组织 A", [[280, 380], [420, 350], [550, 305]], "linestrip", flags={"weak": True})]
        doc.clinical.update(presence="present", confidence="medium", review="initial",
                            quality=["清晰"], note="合成演示图，非真实病例；仅用于体验标注交互。")
        target = path.with_suffix(".json")
        atomic_json(target, doc.to_dict(target))
    blank = directory / "demo_004.png"
    image.save(blank)
    empty = Document(blank.resolve(), width, height)
    atomic_json(blank.with_suffix(".json"), empty.to_dict(blank.with_suffix(".json")))
    return directory


def preview(directory):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from clinical_annotator.app import MainWindow
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.showMaximized()
    app.processEvents()
    window.open_path(directory)
    app.processEvents()
    window.canvas.selected = {0}
    window.sync_selection()
    window.project_label.setText("示例项目 · 4 张合成图像")
    window.path_label.setText("demo/demo_001.json")
    app.processEvents()
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    assert window.grab().save(str(docs / "preview.png"))
    # Close saves a backup; demo backups are not needed in the source package.
    window.close()
    for backup in directory.glob("*.bak"):
        backup.unlink()


if __name__ == "__main__":
    preview(generate())
