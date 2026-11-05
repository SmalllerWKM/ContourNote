import json

import pytest
from PIL import Image
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog

from clinical_annotator.app import MainWindow
from clinical_annotator.data import Shape, atomic_json


@pytest.fixture
def window(qt_app, tmp_path, monkeypatch):
    for name in ["frame_01.png", "frame_02.png"]:
        Image.new("RGB", (320, 240), "#657783").save(tmp_path / name)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: None)
    w = MainWindow(); w.show(); qt_app.processEvents()
    assert w.open_path(tmp_path)
    w.register_category("测试类别")
    w.label_input.setCurrentText("测试类别")
    qt_app.processEvents()
    yield w
    w.canvas.cancel_draft()
    w.close()
    qt_app.processEvents()


def screen(canvas, x, y):
    return (QPointF(x, y)*canvas.scale+canvas.offset).toPoint()


def move(canvas, x, y, modifiers=Qt.KeyboardModifier.NoModifier, buttons=Qt.MouseButton.NoButton):
    local = QPointF(screen(canvas, x, y))
    event = QMouseEvent(QEvent.Type.MouseMove, local, local, Qt.MouseButton.NoButton, buttons, modifiers)
    QApplication.sendEvent(canvas, event)


def test_polygon_autosave_undo_redo_and_labelme_fields(window):
    w = window
    w.set_tool("polygon")
    for x, y in [(30, 30), (150, 30), (130, 140)]:
        QTest.mouseClick(w.canvas, Qt.MouseButton.LeftButton, pos=screen(w.canvas, x, y))
    QTest.keyClick(w.canvas, Qt.Key.Key_Return)
    raw = json.loads(w.label_path().read_text())
    assert raw["shapes"][0]["shape_type"] == "polygon"
    assert "clinical" not in raw
    assert len(w.doc.shapes) == 1
    w.undo()
    assert json.loads(w.label_path().read_text())["shapes"] == []
    w.redo()
    assert len(json.loads(w.label_path().read_text())["shapes"]) == 1


def test_shift_left_sampling_and_live_draft(window):
    w = window
    w.set_tool("polygon")
    for x, y in [(20, 20), (40, 20), (60, 40), (70, 60), (40, 80)]:
        move(w.canvas, x, y, Qt.KeyboardModifier.ShiftModifier, Qt.MouseButton.LeftButton)
    assert len(w.canvas.draft) == 5
    move(w.canvas, 41, 80, Qt.KeyboardModifier.ShiftModifier, Qt.MouseButton.LeftButton)
    assert len(w.canvas.draft) == 5
    QTest.qWait(260)
    assert w.draft_path().exists()
    assert len(json.loads(w.draft_path().read_text())["points"]) == 5
    assert json.loads(w.label_path().read_text())["shapes"] == []
    w.undo(); assert len(w.canvas.draft) == 4
    QTest.keyClick(w.canvas, Qt.Key.Key_Return)
    assert len(w.doc.shapes) == 1 and not w.draft_path().exists()


def test_rectangle_and_point_are_weak_by_default(window):
    w = window
    w.set_tool("rectangle")
    QTest.mousePress(w.canvas, Qt.MouseButton.LeftButton, pos=screen(w.canvas, 20, 20))
    move(w.canvas, 120, 100, buttons=Qt.MouseButton.LeftButton)
    QTest.mouseRelease(w.canvas, Qt.MouseButton.LeftButton, pos=screen(w.canvas, 120, 100))
    assert w.doc.shapes[-1].weak
    assert w.doc.shapes[-1].shape_type == "rectangle"
    w.set_tool("point")
    w.role.setCurrentIndex(1)
    QTest.mouseClick(w.canvas, Qt.MouseButton.LeftButton, pos=screen(w.canvas, 200, 100))
    assert w.doc.shapes[-1].background and w.doc.shapes[-1].weak


def test_edit_vertex_drag_and_live_save(window):
    w = window
    w.doc.shapes = [Shape("神经", [[20, 20], [100, 20], [70, 100]])]
    w.commit(); w.set_tool("edit"); w.canvas.selected = {0}
    QTest.mousePress(w.canvas, Qt.MouseButton.LeftButton, pos=screen(w.canvas, 20, 20))
    move(w.canvas, 35, 35, buttons=Qt.MouseButton.LeftButton)
    QTest.qWait(260)
    raw = json.loads(w.label_path().read_text())
    assert raw["shapes"][0]["points"][0][0] == pytest.approx(35, abs=1)
    QTest.mouseRelease(w.canvas, Qt.MouseButton.LeftButton, pos=screen(w.canvas, 35, 35))
    w.undo()
    assert w.doc.shapes[0].points[0] == [20, 20]


def test_frame_navigation_flush_and_save_failure_prevents_switch(window, monkeypatch):
    w = window
    w.doc.shapes = [Shape("神经", [[20, 20]], "point")]
    w.commit()
    first = w.label_path()
    w.navigate(1)
    assert w.current == 1
    assert json.loads(first.read_text())["shapes"]
    w.autosave.setChecked(False)
    w.doc.shapes = [Shape("新修改", [[40, 40]], "point")]
    w.commit()
    w.autosave.setChecked(True)
    import clinical_annotator.app as module
    w.doc.shapes[0].points = [[60, 60]]
    monkeypatch.setattr(module, "atomic_json", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    w.navigate(-1)
    assert w.current == 1 and w.file_list.currentRow() == 1
    assert "保存失败" in w.save_status.text()


def test_space_pan_zoom_anchor_and_shortcuts(window):
    w = window
    canvas = w.canvas
    QTest.keyClick(canvas, Qt.Key.Key_P)
    assert canvas.tool == "point"
    old = QPointF(canvas.offset)
    QTest.keyPress(canvas, Qt.Key.Key_Space)
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=QPoint(150, 150))
    QTest.mouseMove(canvas, QPoint(210, 190))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=QPoint(210, 190))
    QTest.keyRelease(canvas, Qt.Key.Key_Space)
    assert canvas.offset != old
    anchor = QPointF(250, 200)
    image_point = canvas.to_image(anchor, False)
    canvas.set_zoom(canvas.scale*1.5, anchor)
    assert (canvas.to_image(anchor, False)-image_point).manhattanLength() < 1e-7
    assert not w.doc.shapes


def test_text_input_does_not_trigger_annotation_keys(window):
    w = window
    w.search.setFocus()
    QTest.keyClicks(w.search, "apple")
    assert w.search.text() == "apple"
    assert w.canvas.tool == "edit"


def test_recover_draft_and_preserve_weak_scope(window, monkeypatch):
    w = window
    saved = {"tool": "polygon", "points": [[30, 30], [80, 30], [60, 70]],
             "weak": True, "background": False, "label": "血管", "operation": "new", "selected": []}
    # Simulate recovery after interruption on a different frame.
    second = w.images[1]
    draft = second.parent / ".contour-drafts" / second.with_suffix(".json").name
    atomic_json(draft, saved)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    w.navigate(1)
    assert w.canvas.draft == saved["points"]
    assert w.canvas.label == "血管" and w.canvas.weak
    w.canvas.finish()
    assert w.doc.shapes[0].weak


def test_local_boundary_redraw_and_split(window, monkeypatch):
    w = window
    w.doc.shapes = [Shape("神经", [[30, 30], [180, 30], [180, 170], [30, 170]])]
    w.commit(); w.set_tool("edit")
    c = w.canvas
    QTest.mouseDClick(c, Qt.MouseButton.LeftButton, pos=screen(c, 30, 30))
    assert c.reshape == (0, 0)
    QTest.mouseClick(c, Qt.MouseButton.LeftButton, pos=screen(c, 90, 100))
    monkeypatch.setattr(c, "choose_reshape_parts", lambda: "both")
    QTest.mouseClick(c, Qt.MouseButton.LeftButton, pos=screen(c, 180, 170))
    assert c.reshape is None and not c.draft
    assert len(w.doc.shapes) == 2
    assert w.doc.shapes[0].group_id != w.doc.shapes[1].group_id
    w.undo(); assert len(w.doc.shapes) == 1


def test_open_other_json_same_image_does_not_overwrite_import(window, tmp_path):
    w = window
    external = w.doc.to_dict()
    external["shapes"] = [Shape("外部类别", [[25, 25]], "point").to_dict()]
    source = tmp_path / "external.json"
    atomic_json(source, external)
    assert w.open_path(source)
    assert w.doc.shapes[0].label == "外部类别"
    assert json.loads(source.read_text())["shapes"][0]["label"] == "外部类别"


def test_unsupported_import_protects_existing_file(window, tmp_path):
    w = window
    external = w.doc.to_dict()
    external["shapes"] = [{"label": "x", "points": [[1, 1], [10, 10]], "shape_type": "mask", "mask": "test"}]
    source = tmp_path / "unsupported.json"
    atomic_json(source, external)
    original = source.read_bytes()
    old_target = w.label_path()
    assert not w.open_path(source)
    assert source.read_bytes() == original and w.label_path() == old_target


def test_change_label_directory_copies_entire_project(window, tmp_path, monkeypatch):
    w = window
    w.doc.shapes = [Shape("神经", [[20, 20]], "point")]
    w.commit(); w.navigate(1)
    w.doc.shapes = [Shape("器械", [[80, 80]], "point")]
    w.commit()
    destination = tmp_path / "new_labels"
    destination.mkdir()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(destination))
    w.choose_label_dir()
    assert w.label_dir == destination
    assert len(list(destination.glob("*.json"))) == 2
    w.navigate(-1)
    assert w.doc.shapes[0].label == "神经"


def test_copy_paste_preserves_weak_and_is_undoable(window):
    w = window
    w.doc.shapes = [Shape("神经", [[20, 20]], "point", flags={"weak": True})]
    w.commit(); w.canvas.selected = {0}; w.copy_selected(); w.navigate(1)
    w.paste_selected()
    assert len(w.doc.shapes) == 1 and w.doc.shapes[0].weak
    w.undo(); assert not w.doc.shapes
