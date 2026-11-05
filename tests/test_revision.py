import json
import os
from pathlib import Path

from PIL import Image
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from clinical_annotator.app import MainWindow
from clinical_annotator.data import Shape, atomic_json
from test_gui import screen, move


@pytest.fixture
def fresh(qt_app, tmp_path, monkeypatch):
    Image.new("RGB", (400, 300), "#777777").save(tmp_path / "sample.png")
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    w = MainWindow(); w.show(); qt_app.processEvents()
    assert w.open_path(tmp_path)
    yield w
    w.last_error = ""
    w.canvas.cancel_draft()
    w.close()
    qt_app.processEvents()


def use_label(w, name="自定义前景"):
    w.register_category(name)
    w.label_input.setCurrentText(name)


def test_no_preset_categories_and_prompt_on_first_annotation(fresh, monkeypatch):
    w = fresh
    assert w.label_input.count() == 0 and w.canvas.label == ""
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("任意组织类别", True))
    w.set_tool("point")
    QTest.mouseClick(w.canvas, Qt.MouseButton.LeftButton, pos=screen(w.canvas, 50, 50))
    assert w.doc.shapes[0].label == "任意组织类别"
    assert w.label_input.count() == 1
    saved = json.loads(w.category_settings_path().read_text())
    assert saved["categories"] == ["任意组织类别"]


def test_shift_path_auto_closes_near_start_without_click(fresh):
    w = fresh; use_label(w); w.set_tool("polygon")
    for x, y in [(50, 50), (180, 50), (180, 180), (50, 180), (52, 52)]:
        move(w.canvas, x, y, Qt.KeyboardModifier.ShiftModifier, Qt.MouseButton.LeftButton)
    assert len(w.doc.shapes) == 1 and not w.canvas.draft
    assert w.doc.shapes[0].shape_type == "polygon"
    assert json.loads(w.label_path().read_text())["shapes"]
    # A held Shift must not leave a new accidental path after closure.
    move(w.canvas, 80, 80, Qt.KeyboardModifier.ShiftModifier, Qt.MouseButton.LeftButton)
    assert not w.canvas.draft
    QTest.keyRelease(w.canvas, Qt.Key.Key_Shift)
    for x, y in [(240, 100), (320, 100), (320, 180), (240, 180), (242, 102)]:
        move(w.canvas, x, y, Qt.KeyboardModifier.ShiftModifier, Qt.MouseButton.LeftButton)
    assert len(w.doc.shapes) == 2
    w.undo(); assert len(w.doc.shapes) == 1


def test_click_path_closes_on_hover_and_option_can_disable_it(fresh):
    w = fresh; use_label(w); w.set_tool("polygon")
    for x, y in [(40, 40), (150, 40), (120, 160)]:
        QTest.mouseClick(w.canvas, Qt.MouseButton.LeftButton, pos=screen(w.canvas, x, y))
    move(w.canvas, 42, 42)
    assert len(w.doc.shapes) == 1
    w.auto_close.setChecked(False)
    for x, y in [(200, 40), (320, 40), (290, 160)]:
        QTest.mouseClick(w.canvas, Qt.MouseButton.LeftButton, pos=screen(w.canvas, x, y))
    move(w.canvas, 202, 42)
    assert len(w.doc.shapes) == 1 and len(w.canvas.draft) == 3


def test_autosave_off_stops_writes_manual_save_updates_real_mtime(fresh):
    w = fresh; use_label(w)
    w.save_live()
    old_bytes = w.label_path().read_bytes()
    old_time = w.label_path().stat().st_mtime_ns
    w.autosave.setChecked(False)
    w.doc.shapes = [Shape("用户类别", [[30, 30]], "point")]; w.commit()
    QTest.qWait(700)
    assert w.label_path().read_bytes() == old_bytes
    assert w.label_path().stat().st_mtime_ns == old_time
    assert "未保存" in w.save_status.text()
    assert w.save_live()
    assert w.label_path().stat().st_mtime_ns != old_time
    assert len(json.loads(w.label_path().read_text())["shapes"]) == 1
    assert "无新修改" in w.save_status.text()
    stamp = w.label_path().stat().st_mtime_ns
    w.save_live(); QTest.qWait(50); w.save_live()
    assert w.label_path().stat().st_mtime_ns == stamp


def test_enable_autosave_flushes_pending_edits(fresh):
    w = fresh; use_label(w); w.autosave.setChecked(False)
    w.doc.shapes = [Shape("病灶", [[50, 60]], "point")]; w.commit()
    assert not w.label_path().exists()
    w.autosave.setChecked(True)
    assert json.loads(w.label_path().read_text())["shapes"][0]["label"] == "病灶"


def test_file_monitor_displays_external_mtime_and_never_overwrites(fresh):
    w = fresh; w.save_live()
    target = w.label_path()
    payload = json.loads(target.read_text())
    payload["shapes"] = [Shape("外部新类别", [[90, 90]], "point").to_dict()]
    atomic_json(target, payload)
    external_time = target.stat().st_mtime_ns
    # Use a different timestamp to make the UI time change observable.
    os.utime(target, ns=(external_time, external_time + 2_000_000_000))
    QTest.qWait(700)
    assert w.external_change and "外部" in w.save_status.text()
    expected_ms = f"{target.stat().st_mtime_ns//1_000_000%1000:03d}"
    assert w.file_mtime_label.text().endswith(expected_ms)
    assert not w.auto_flush()
    assert json.loads(target.read_text())["shapes"][0]["label"] == "外部新类别"
    w.reload_annotation()
    assert w.doc.shapes[0].label == "外部新类别"
    assert not w.external_change
    assert w.label_input.findText("外部新类别") >= 0


def test_explicit_open_labelme_button_and_automatic_arbitrary_categories(fresh, tmp_path, monkeypatch):
    w = fresh
    target = tmp_path / "external.json"
    raw = w.doc.to_dict(target)
    raw["shapes"] = [Shape("artery", [[10, 10], [50, 10], [30, 40]]).to_dict(),
                     Shape("椎间盘", [[150, 150], [210, 210]], "rectangle").to_dict()]
    atomic_json(target, raw)
    before = target.stat().st_mtime_ns
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(target), ""))
    w.open_annotation()
    assert w.label_path() == target
    assert {w.label_input.itemText(i) for i in range(w.label_input.count())} == {"artery", "椎间盘"}
    assert [s.label for s in w.doc.shapes] == ["artery", "椎间盘"]
    assert target.stat().st_mtime_ns == before


def test_open_image_automatically_reads_labelme_without_touching_mtime(fresh, tmp_path):
    w = fresh
    picture = tmp_path / "new.png"; Image.new("RGB", (200, 160)).save(picture)
    from clinical_annotator.data import Document
    doc = Document(picture, 200, 160, shapes=[Shape("用户自定义目标", [[10, 10], [80, 10], [30, 90]])])
    target = picture.with_suffix(".json"); atomic_json(target, doc.to_dict(target))
    stamp = target.stat().st_mtime_ns
    assert w.open_path(picture)
    assert w.doc.shapes[0].label == "用户自定义目标"
    assert target.stat().st_mtime_ns == stamp
    w.save_live(); assert target.stat().st_mtime_ns == stamp


def test_user_categories_are_restored_without_creating_annotations(fresh):
    w = fresh
    w.label_input.setCurrentText("新组织类别")
    w.register_typed_category()
    assert not w.label_path().exists()
    assert w.load_images(list(w.images))
    assert w.label_input.currentText() == "新组织类别"
    assert w.canvas.label == "新组织类别"
    assert not w.label_path().exists()


def test_autosave_off_cancel_close_keeps_memory_and_original_file(fresh, monkeypatch):
    w = fresh; use_label(w); w.save_live()
    old = w.label_path().read_bytes()
    w.autosave.setChecked(False)
    w.doc.shapes = [Shape("目标", [[20, 20]], "point")]; w.commit()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    assert not w.can_leave()
    assert len(w.doc.shapes) == 1 and w.label_path().read_bytes() == old
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)


def test_small_path_does_not_prematurely_close(fresh):
    w = fresh; use_label(w); w.set_tool("polygon")
    for x, y in [(50, 50), (51, 50), (51, 51), (50, 50)]:
        move(w.canvas, x, y, Qt.KeyboardModifier.ShiftModifier, Qt.MouseButton.LeftButton)
    assert not w.doc.shapes
    assert w.canvas.draft


def test_export_uses_visible_unsaved_annotations_with_autosave_off(fresh, tmp_path, monkeypatch):
    w = fresh; use_label(w); w.autosave.setChecked(False)
    w.doc.shapes = [Shape("任意目标", [[20, 20], [100, 20], [60, 90]])]; w.commit()
    assert not w.label_path().exists()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    import clinical_annotator.app as module
    captured = []
    def export(documents, target):
        captured.extend(documents)
        return {"annotations": []}
    monkeypatch.setattr(module, "export_dataset", export)
    w.export_project()
    assert captured[0].shapes[0].label == "任意目标"
    assert not w.label_path().exists()
