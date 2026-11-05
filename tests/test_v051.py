import copy,json
import numpy as np
import pytest
from PIL import Image,ImageDraw
from PySide6.QtCore import Qt,QPointF
from PySide6.QtTest import QTest
from clinical_annotator.app import MainWindow
from clinical_annotator.data import Shape,geometry
from test_gui import window,screen,move


def test_direct_two_endpoint_redraw_closes(window,monkeypatch):
    w=window;c=w.canvas
    w.doc.shapes=[Shape('测试类别',[[40,40],[220,40],[220,180],[40,180]])];w.commit();w.set_tool('edit')
    QTest.mouseDClick(c,Qt.MouseButton.LeftButton,pos=screen(c,40,40))
    choices=[];monkeypatch.setattr(c,'choose_reshape_parts',lambda:(choices.append(True) or 'large'))
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,220,180))
    assert choices and not c.draft and c.reshape is None


@pytest.mark.parametrize('tool',['polygon','point','line','scribble'])
def test_far_black_click_projects_to_boundary(qt_app,tmp_path,tool):
    im=Image.new('RGB',(400,400),'black');ImageDraw.Draw(im).ellipse((40,40,360,360),fill='#999999')
    path=tmp_path/'circle.png';im.save(path)
    w=MainWindow();w.show();qt_app.processEvents();w.open_path(path);w.register_category('target');w.label_input.setCurrentText('target');w.set_tool(tool)
    c=w.canvas
    QTest.mousePress(c,Qt.MouseButton.LeftButton,pos=screen(c,10,10))
    if tool=='point':points=w.doc.shapes[-1].points
    else:points=c.draft
    assert points and np.linalg.norm(np.array(points[0])-[10,10])>50
    from shapely.geometry import Point,Polygon
    boundary=Polygon(c.view_boundary[1])
    assert boundary.boundary.distance(Point(points[0]))<1e-6
    if tool=='scribble':QTest.mouseRelease(c,Qt.MouseButton.LeftButton,pos=screen(c,10,10))
    c.cancel_draft();w.close()


def test_invalid_reconnect_shows_reason_and_keeps_original(window,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    w=window;c=w.canvas;shape=Shape('测试类别',[[40,40],[220,40],[220,180],[40,180]])
    w.doc.shapes=[copy.deepcopy(shape)];w.commit();w.set_tool('edit')
    QTest.mouseDClick(c,Qt.MouseButton.LeftButton,pos=screen(c,40,40))
    warnings=[];monkeypatch.setattr(QMessageBox,'warning',lambda *a,**k:warnings.append(a[2]))
    # Following the same top edge encloses no new area.
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,150,40))
    assert warnings and w.doc.shapes==[shape] and c.draft


def test_physical_double_click_sequence_then_edge_click(window,monkeypatch):
    w=window;c=w.canvas;w.doc.shapes=[Shape('测试类别',[[40,40],[220,40],[220,180],[40,180]])];w.commit();w.set_tool('edit')
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,40,100))
    QTest.mouseDClick(c,Qt.MouseButton.LeftButton,pos=screen(c,40,100))
    QTest.mouseRelease(c,Qt.MouseButton.LeftButton,pos=screen(c,40,100))
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,140,110))
    chosen=[];monkeypatch.setattr(c,'choose_reshape_parts',lambda:(chosen.append(True) or 'large'))
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,220,100))
    assert chosen and c.reshape is None
