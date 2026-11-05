import json

from PIL import Image
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from clinical_annotator.app import MainWindow
from clinical_annotator.data import Document, Shape, atomic_json
from test_gui import move, screen


@pytest.fixture
def workspace(qt_app, tmp_path, monkeypatch):
    for i in range(4):
        Image.new("RGB", (400, 300), "gray").save(tmp_path / f"frame_{i}.png")
    annotated = Document(tmp_path / "frame_1.png", 400, 300, shapes=[Shape("目标", [[30, 30]], "point")])
    atomic_json(annotated.image.with_suffix(".json"), annotated.to_dict())
    blank = Document(tmp_path / "frame_2.png", 400, 300)
    atomic_json(blank.image.with_suffix(".json"), blank.to_dict())
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    w = MainWindow(); w.show(); qt_app.processEvents(); assert w.open_path(tmp_path)
    w.register_category("目标"); w.label_input.setCurrentText("目标")
    yield w
    w.canvas.cancel_draft(); w.close(); qt_app.processEvents()


def test_canvas_refits_on_resize_but_preserves_manual_zoom(workspace, qt_app):
    w = workspace
    w.resize(1050, 680); qt_app.processEvents(); w.canvas.fit()
    before = w.canvas.scale
    w.resize(1600, 1000); qt_app.processEvents()
    assert w.canvas.scale > before
    assert w.canvas.image.width()*w.canvas.scale <= w.canvas.width()
    assert w.canvas.image.height()*w.canvas.scale <= w.canvas.height()
    w.canvas.set_zoom(w.canvas.scale*2)
    zoom = w.canvas.scale
    w.resize(1200, 800); qt_app.processEvents()
    assert w.canvas.scale == zoom
    w.canvas.fit(); assert w.canvas.fit_mode


def test_chinese_tool_buttons_fit_and_frame_controls_are_visible(workspace, qt_app):
    w = workspace
    w.resize(1000, 700); qt_app.processEvents()
    for b in w.tool_buttons.values():
        assert b.width() >= b.sizeHint().width(), b.text()
        assert b.height() >= b.sizeHint().height(), b.text()
    for b in [w.previous_frame_button, w.next_frame_button, w.copy_frame_button, w.propagate_frame_button, w.weak_copy]:
        assert b.isVisible()
        assert b.parentWidget().rect().contains(b.geometry())
    assert w.copy_frame_button.menu() is None


def test_shift_alone_does_nothing_shift_left_drag_samples(workspace):
    w = workspace; c = w.canvas; w.set_tool("polygon")
    for x, y in [(20, 20), (100, 20), (100, 100)]:
        move(c, x, y, Qt.KeyboardModifier.ShiftModifier)
    assert not c.draft
    QTest.mousePress(c, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, screen(c, 20, 20))
    move(c, 100, 20, Qt.KeyboardModifier.ShiftModifier, Qt.MouseButton.LeftButton)
    move(c, 100, 100, Qt.KeyboardModifier.ShiftModifier, Qt.MouseButton.LeftButton)
    QTest.mouseRelease(c, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, screen(c, 100, 100))
    count = len(c.draft)
    move(c, 120, 120, Qt.KeyboardModifier.ShiftModifier)
    assert len(c.draft) == count == 3
    QTest.keyClick(c, Qt.Key.Key_Return)
    assert len(w.doc.shapes) == 1


def test_checkmarks_load_existing_and_change_after_edit_undo_delete(workspace):
    w = workspace
    assert not w.file_list.item(0).text().startswith("✓")
    assert w.file_list.item(1).text().startswith("✓")
    assert not w.file_list.item(2).text().startswith("✓")
    w.doc.shapes = [Shape("目标", [[40, 40]], "point")]; w.commit()
    assert w.file_list.item(0).text().startswith("✓")
    w.undo(); assert not w.file_list.item(0).text().startswith("✓")
    w.redo(); assert w.file_list.item(0).text().startswith("✓")
    w.canvas.selected = {0}; w.canvas.delete_selected()
    assert not w.file_list.item(0).text().startswith("✓")


def test_outline_width_is_display_only_and_persisted(workspace):
    w = workspace
    w.save_live(); before = w.label_path().read_bytes()
    w.outline_width.setValue(4.5)
    assert w.canvas.stroke_width == 4.5
    assert w.label_path().read_bytes() == before
    saved = json.loads(w.category_settings_path().read_text())
    assert saved["stroke_width"] == 4.5
    w.canvas.stroke_width = 1.7
    w.load_categories()
    assert w.canvas.stroke_width == 4.5


def test_slideshow_speed_pause_resume_loop_and_manual_pause(workspace):
    w = workspace
    w.slideshow_interval.setValue(.2)
    w.toggle_slideshow()
    assert w.slideshow_timer.isActive() and w.slideshow_timer.interval() == 200
    w.slideshow_tick(); assert w.current == 1 and w.slideshow_timer.isActive()
    w.slideshow_interval.setValue(.5); assert w.slideshow_timer.interval() == 500
    w.toggle_slideshow(); assert not w.slideshow_timer.isActive()
    current = w.current
    w.toggle_slideshow(); w.slideshow_tick(); assert w.current == current+1
    w.navigate(1); assert w.current == 3 and not w.slideshow_timer.isActive()
    w.toggle_slideshow(); w.slideshow_tick(); assert not w.slideshow_timer.isActive()
    w.slideshow_loop.setChecked(True); w.toggle_slideshow(); w.slideshow_tick()
    assert w.current == 0 and w.slideshow_timer.isActive()
    QTest.mouseClick(w.canvas, Qt.MouseButton.LeftButton, pos=screen(w.canvas, 50, 50))
    assert not w.slideshow_timer.isActive()


def test_slideshow_cannot_skip_unsaved_edits_or_draft(workspace):
    w = workspace
    w.autosave.setChecked(False)
    w.doc.shapes = [Shape("目标", [[40, 40]], "point")]; w.commit()
    w.toggle_slideshow(); assert not w.slideshow_timer.isActive()
    w.save_live(); w.toggle_slideshow(); assert w.slideshow_timer.isActive()
    w.canvas.draft = [[20, 20], [100, 20]]
    w.slideshow_tick(); assert not w.slideshow_timer.isActive() and w.current == 0


def test_slideshow_stops_before_showing_a_load_error(workspace, monkeypatch):
    w = workspace
    (w.images[1].with_suffix(".json")).write_text("invalid json")
    seen = []
    def error(*args, **kwargs):
        seen.append(True)
        assert not w.slideshow_timer.isActive()
    monkeypatch.setattr(QMessageBox, "critical", error)
    w.toggle_slideshow(); w.slideshow_tick()
    assert seen and w.current == 0 and not w.slideshow_timer.isActive()


def test_f5_remains_available_while_search_has_focus(workspace):
    w = workspace
    w.search.setFocus()
    QTest.keyClick(w.search, Qt.Key.Key_F5)
    assert w.slideshow_timer.isActive()
    QTest.keyClick(w.search, Qt.Key.Key_F5)
    assert not w.slideshow_timer.isActive()
