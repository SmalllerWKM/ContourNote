import copy,json
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QTabWidget
from clinical_annotator.data import Shape,atomic_json
from test_gui import window,screen,move


def test_hover_and_shift_drag_do_not_confirm_redraw(window,monkeypatch):
    w=window;c=w.canvas
    w.doc.shapes=[Shape('测试类别',[[40,40],[220,40],[220,180],[40,180]])];w.commit();w.set_tool('edit')
    QTest.mouseDClick(c,Qt.MouseButton.LeftButton,pos=screen(c,40,40))
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,140,100))
    chosen=[];monkeypatch.setattr(c,'choose_reshape_parts',lambda:(chosen.append(True) or 'large'))
    move(c,220,180)
    move(c,220,180,Qt.KeyboardModifier.ShiftModifier,Qt.MouseButton.LeftButton)
    assert not chosen and c.reshape is not None
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,220,180))
    assert chosen and c.reshape is None


def test_notice_can_close_without_discarding_path(window):
    w=window;c=w.canvas;w.set_tool('polygon');c.draft=[[40,40],[140,40],[140,140]]
    before=copy.deepcopy(c.draft)
    w.show_operation_error('测试提示');assert w.operation_notice.isVisible()
    QTest.mouseClick(w.dismiss_operation_notice,Qt.MouseButton.LeftButton)
    assert not w.operation_notice.isVisible() and c.draft==before
    assert not w.operation_hint.text()


def test_new_annotations_have_no_record_ui_or_generated_records(window):
    w=window
    assert not w.findChildren(QTabWidget)
    for name in ['presence','confidence','review','quality_checks','risk_checks','note']:
        assert not hasattr(w,name)
    w.set_tool('point');QTest.mouseClick(w.canvas,Qt.MouseButton.LeftButton,pos=screen(w.canvas,80,80))
    assert 'clinical' not in json.loads(w.label_path().read_text())


def test_old_record_fields_survive_geometry_edit_without_changes(window):
    w=window;legacy={'presence':'uncertain','risks':['神经边界不清晰'],'review':'final','note':'合成历史数据','custom':{'a':1}}
    raw=w.doc.to_dict();raw['clinical']=copy.deepcopy(legacy)
    atomic_json(w.label_path(),raw);w.reload_annotation()
    w.set_tool('point');QTest.mouseClick(w.canvas,Qt.MouseButton.LeftButton,pos=screen(w.canvas,100,100))
    assert json.loads(w.label_path().read_text())['clinical']==legacy
