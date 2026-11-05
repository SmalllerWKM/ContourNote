"""Capture the real UI with synthetic data and draw bilingual SVG diagrams."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QApplication, QLabel, QTabWidget, QToolButton
from clinical_annotator.app import MainWindow
from clinical_annotator.data import atomic_json

IMAGES = ROOT / "docs" / "images"


def grab(widget, name, rect=None):
    QApplication.processEvents()
    pixmap = widget.grab(rect) if rect is not None else widget.grab()
    if not pixmap.save(str(IMAGES / name)):
        raise RuntimeError(f"Could not save {name}")


def capture_ui():
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="contournote-docs-") as temporary:
        folder = Path(temporary)
        for path in (ROOT / "demo").iterdir():
            if path.suffix in {".png", ".json"}:
                shutil.copy2(path, folder / path.name)
        window = MainWindow()
        window.showMaximized()
        app.processEvents()
        assert window.open_path(folder)
        window.project_label.setText("Synthetic demo · 合成示例")
        app.processEvents()
        grab(window, "workspace.png")
        window.canvas.selected = {0}
        window.sync_selection()
        grab(window.canvas, "vertex-editing.png")
        window.canvas.selected.clear()
        window.sync_selection()

        for title, filename in [("绘制设置", "drawing-settings.png"), ("图片放映", "slideshow-settings.png")]:
            control = next(b for b in window.findChildren(QToolButton) if b.text().startswith(title))
            menu = control.menu()
            menu.popup(window.mapToGlobal(QPoint(220, 160)))
            grab(menu, filename)
            menu.hide()
        section = next(label for label in window.findChildren(QLabel) if label.text() == "标注文件")
        widgets = [section, window.path_label, window.file_mtime_label, window.save_status, window.reload_button]
        region = QRect()
        for widget in widgets:
            region = region.united(QRect(widget.mapTo(window, QPoint()), widget.size()))
        region = region.adjusted(-6, -6, 6, 6)
        window.save_live()
        grab(window, "file-saved.png", region)
        window.autosave.setChecked(False)
        window.doc.shapes[0].description = "Unsaved documentation example / 未保存演示"
        window.commit()
        grab(window, "file-unsaved.png", region)
        window.save_live()
        value = json.loads(window.label_path().read_text(encoding="utf-8"))
        value["flags"]["external_demo"] = True
        atomic_json(window.label_path(), value)
        window.refresh_file_state()
        grab(window, "file-external.png", region)
        window.close()
        window.deleteLater()
        app.processEvents()


def svg(width, height, title, elements):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
<title>{html.escape(title)}</title><style>text{{font-family:Arial,"Microsoft YaHei","Noto Sans CJK SC",sans-serif;fill:#26384d}}.muted{{fill:#69788a}}.small{{font-size:14px}}.body{{font-size:17px}}.heading{{font-size:23px;font-weight:600}}</style>
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="#7c91a9"/></marker></defs>
<rect width="100%" height="100%" fill="#f7f9fc"/>{''.join(elements)}</svg>'''


def text(x, y, value, css="body", **attributes):
    extra = " ".join(f'{k.replace("_", "-")}="{html.escape(str(v))}"' for k, v in attributes.items())
    return f'<text x="{x}" y="{y}" class="{css}" {extra}>{html.escape(value)}</text>'


def card(x, y, width, height):
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" fill="#fff" stroke="#dce3ed"/>'


def diagrams():
    for language in ["en", "zh"]:
        zh = language == "zh"
        steps = ([('打开项目', '图像 / Labelme JSON'), ('添加类别', '完整区域或弱提示'), ('人工描绘', 'Shift＋左键连续采点'), ('保存与复核', 'JSON · 文件时间 · 审核'), ('导出数据集', 'COCO · JSON · Mask')]
                 if zh else [('Open a project', 'Images / Labelme JSON'), ('Choose labels', 'Full regions or weak cues'), ('Annotate manually', 'Shift + left-button drag'), ('Save and review', 'JSON, timestamps, review'), ('Export a dataset', 'COCO, JSON, masks')])
        items = [text(28, 40, '从图像到数据集' if zh else 'From images to a dataset', 'heading')]
        for i, (heading, detail) in enumerate(steps):
            x = 26+i*246
            items += [card(x, 70, 226, 130), text(x+18, 105, f'0{i+1}', 'small'), text(x+18, 142, heading), text(x+18, 174, detail, 'small muted')]
            if i < 4:
                items.append(f'<path d="M{x+229} 135H{x+242}" stroke="#7c91a9" stroke-width="2" marker-end="url(#arrow)"/>')
        items.append(text(28, 239, '帧间复用仅复制坐标；每一帧仍需人工检查。' if zh else 'Frame reuse copies coordinates. Review every destination frame.', 'small muted'))
        (IMAGES / f"workflow-{language}.svg").write_text(svg(1250, 265, 'Annotation workflow', items), encoding="utf-8")

        items = [text(28, 40, 'Shift＋鼠标左键：连续采点与闭合' if zh else 'Shift + left-button drag: sampling and closure', 'heading')]
        titles = ['按住 Shift 和左键', '沿边界拖动', '返回起点附近'] if zh else ['Hold Shift + left button', 'Drag along the boundary', 'Return near the start']
        notes = ['只按 Shift 不会落点', '松开左键可暂停', '默认 12 屏幕像素内闭合'] if zh else ['Shift alone adds no points', 'Release the button to pause', 'Default closure radius: 12 screen px']
        for i in range(3):
            x = 26+i*410
            items += [card(x, 65, 390, 248), text(x+20, 102, f'{i+1}. {titles[i]}')]
            points = [(x+67, 240), (x+105, 168), (x+173, 143), (x+254, 164), (x+312, 224), (x+230, 257), (x+135, 260)]
            count = 1 if i == 0 else 5 if i == 1 else 7
            path = ' '.join(f'{a},{b}' for a, b in points[:count])
            if i == 2:
                items.append(f'<polygon points="{path}" fill="#ddf1eb" stroke="#369c86" stroke-width="3"/>')
                items.append(f'<circle cx="{points[0][0]}" cy="{points[0][1]}" r="18" stroke="#87a8c8" stroke-dasharray="4 4" fill="none"/>')
            elif i == 1:
                items.append(f'<polyline points="{path}" fill="none" stroke="#369c86" stroke-width="3"/>')
            for a, b in points[:count]:
                items.append(f'<circle cx="{a}" cy="{b}" r="5" fill="#369c86" stroke="white" stroke-width="2"/>')
            items.append(text(x+20, 293, notes[i], 'small muted'))
        items.append(text(28, 350, '示意图：至少 3 点、路径已离开起点且区域有效才自动闭合；采样间距默认 8 屏幕像素。' if zh else 'Schematic: auto-close requires 3+ points, sufficient travel, and valid geometry. Default sampling: 8 screen px.', 'small muted'))
        (IMAGES / f"gesture-{language}.svg").write_text(svg(1250, 380, 'Shift and left-button annotation gesture', items), encoding="utf-8")

        columns = ['标记类型', 'Labelme JSON', 'COCO', 'Mask'] if zh else ['Annotation', 'Labelme JSON', 'COCO', 'Masks']
        rows = ([['完整区域', 'polygon / rectangle / circle', 'segmentation + bbox', 'masks/'], ['弱框', 'rectangle + weak=true', 'bbox; segmentation=[]', 'weak_masks/'], ['点 / 线 / 涂鸦', 'point / line / linestrip', 'weak_annotations.json', 'weak_masks/'], ['背景提示', 'background=true', 'weak_annotations.json', 'weak_masks/: 0']]
                if zh else [['Full regions', 'polygon / rectangle / circle', 'segmentation + bbox', 'masks/'], ['Weak boxes', 'rectangle + weak=true', 'bbox; segmentation=[]', 'weak_masks/'], ['Points / lines / scribbles', 'point / line / linestrip', 'weak_annotations.json', 'weak_masks/'], ['Background cues', 'background=true', 'weak_annotations.json', 'weak_masks/: 0']])
        items = [text(28, 40, '导出语义：完整区域与弱提示分开' if zh else 'Export semantics: keep full regions and weak cues separate', 'heading')]
        xs = [42, 292, 650, 1000]
        items.append(card(26, 65, 1198, 310))
        for x, value in zip(xs, columns): items.append(text(x, 104, value))
        for i, row in enumerate(rows):
            y = 151+i*61
            items.append(f'<path d="M40 {y-26}H1210" stroke="#e8edf3"/>')
            for x, value in zip(xs, row): items.append(text(x, y, value, 'small'))
        items += [text(28, 411, '像素值：0 背景 · 1–254 前景类别 · 255 未知 / 忽略' if zh else 'Pixel IDs: 0 = background, 1–254 = foreground classes, 255 = unknown / ignore', 'body'),
                  text(28, 444, '只有弱提示时，完整区域 Mask 保持未知；弱框不是精确分割真值。' if zh else 'Weak-only images keep an unknown semantic mask. A weak box is not a precise segmentation.', 'small muted')]
        (IMAGES / f"exports-{language}.svg").write_text(svg(1250, 475, 'Annotation export semantics', items), encoding="utf-8")


if __name__ == "__main__":
    IMAGES.mkdir(parents=True, exist_ok=True)
    diagrams()
    capture_ui()
    print(f"Wrote documentation assets to {IMAGES}")
