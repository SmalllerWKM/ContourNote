import json
import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox
from shapely.geometry import Polygon

from clinical_annotator.data import Shape
from test_gui import window, screen
from test_workspace import workspace


def forbid_dialogs(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail('This operation must not show a modal dialog')
    for name in ['question', 'information', 'warning']:
        monkeypatch.setattr(QMessageBox, name, fail)


def test_redraw_defaults_large_then_double_click_small_and_undo(window, monkeypatch):
    w=window; c=w.canvas
    forbid_dialogs(monkeypatch)
    w.doc.shapes=[Shape('测试类别',[[40,40],[220,40],[220,180],[40,180]], description='keep metadata')]
    w.commit(); w.set_tool('edit')
    QTest.mouseDClick(c,Qt.MouseButton.LeftButton,pos=screen(c,40,40))
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,180,65))
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,220,180))
    assert c.reshape is None and c.reshape_alternative
    large=Polygon(w.doc.shapes[0].points).area
    small=c.reshape_alternative[2]
    center=Polygon(small.points).representative_point()
    assert json.loads(w.label_path().read_text())['shapes'][0]['points']==w.doc.shapes[0].points
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,center.x,center.y))
    assert Polygon(w.doc.shapes[0].points).area==large
    QTest.mouseDClick(c,Qt.MouseButton.LeftButton,pos=screen(c,center.x,center.y))
    assert Polygon(w.doc.shapes[0].points).area < large
    assert w.doc.shapes[0].description=='keep metadata'
    assert json.loads(w.label_path().read_text())['shapes'][0]['points']==w.doc.shapes[0].points
    w.undo(); assert Polygon(w.doc.shapes[0].points).area==large
    assert c.reshape_alternative is None


def test_copy_previous_without_dialogs_saves_origin_and_undo(workspace, monkeypatch):
    w=workspace; w.navigate(1); w.navigate(1)
    forbid_dialogs(monkeypatch)
    w.copy_previous()
    assert '复制成功' in w.workflow_status.text()
    raw=json.loads(w.label_path().read_text())
    assert raw['contour_note_copy']['source_image']=='frame_1.png'
    w.undo(); assert 'contour_note_copy' not in w.doc.extra


def test_multi_frame_copy_count_and_persistent_warning(workspace, monkeypatch):
    w=workspace; w.navigate(1)
    assert w.copy_frame_count.value()==1
    w.copy_frame_count.setValue(2)
    forbid_dialogs(monkeypatch)
    w.propagate()
    assert '后续 2 帧' in w.workflow_status.text()
    for image in w.images[2:]:
        raw=json.loads(image.with_suffix('.json').read_text())
        assert raw['contour_note_copy']['source_image']=='frame_1.png'
    w.navigate(1)
    assert '本帧标注来自于前帧的复制' in w.workflow_status.text()
    w.navigate(1)
    assert '请仔细检查' in w.workflow_status.text()


def test_copy_range_validation_never_silently_truncates(workspace, monkeypatch):
    w=workspace; w.navigate(1); w.copy_frame_count.setValue(99)
    before=w.images[2].with_suffix('.json').read_bytes()
    forbid_dialogs(monkeypatch); w.propagate()
    assert '复制未开始' in w.workflow_status.text()
    assert w.images[2].with_suffix('.json').read_bytes()==before


def test_slideshow_controls_are_visible(workspace):
    for control in [workspace.slideshow_interval, workspace.slideshow_button, workspace.slideshow_loop]:
        assert control.isVisible()


@pytest.mark.parametrize('modifier', [Qt.KeyboardModifier.ControlModifier] + ([Qt.KeyboardModifier.MetaModifier] if sys.platform=='darwin' else []))
def test_copy_paste_save_shortcuts(window, modifier):
    w=window; c=w.canvas
    w.doc.shapes=[Shape('测试类别',[[80,80]],'point')]; w.commit()
    c.selected={0}; c.setFocus()
    QTest.keyClick(c,Qt.Key.Key_C,modifier)
    QTest.keyClick(c,Qt.Key.Key_V,modifier)
    assert len(w.doc.shapes)==2
    w.autosave.setChecked(False)
    w.doc.shapes[1].points=[[120,120]]; w.commit()
    QTest.keyClick(c,Qt.Key.Key_S,modifier)
    assert json.loads(w.label_path().read_text())['shapes'][1]['points']==[[120,120]]
