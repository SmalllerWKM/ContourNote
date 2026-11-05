import copy,math,time
import numpy as np
from PIL import Image,ImageDraw
from PySide6.QtCore import Qt,QPointF
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox
from clinical_annotator.data import Shape,geometry
from clinical_annotator.view_boundary import detect_view_boundary
from test_gui import window,screen,move


def test_unified_edit_double_edge_then_reconnect(window,monkeypatch):
    w=window;c=w.canvas
    original=Shape('测试类别',[[40,40],[220,40],[220,180],[40,180]],description='keep')
    w.doc.shapes=[copy.deepcopy(original)];w.commit();w.set_tool('edit')
    QTest.mouseDClick(c,Qt.MouseButton.LeftButton,pos=screen(c,40,100))
    assert c.reshape is not None and len(c.draft)==1
    assert w.doc.shapes==[original] # double-click uses a virtual boundary node
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,140,110))
    choices=[]
    monkeypatch.setattr(c,'choose_reshape_parts',lambda:(choices.append(True) or 'both'))
    move(c,220,100)
    assert not choices
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,220,100))
    assert choices and not c.draft and len(w.doc.shapes)==2
    assert abs(sum(geometry(s).area for s in w.doc.shapes)-25200)<1
    assert all(s.description=='keep' for s in w.doc.shapes)
    w.undo();assert w.doc.shapes==[original]


def test_single_click_edge_adds_draggable_node(window):
    w=window;c=w.canvas
    w.doc.shapes=[Shape('测试类别',[[40,40],[220,40],[220,180],[40,180]])];w.commit();w.set_tool('edit')
    QTest.mousePress(c,Qt.MouseButton.LeftButton,pos=screen(c,40,100))
    move(c,60,100,buttons=Qt.MouseButton.LeftButton)
    QTest.mouseRelease(c,Qt.MouseButton.LeftButton,pos=screen(c,60,100))
    assert c.reshape is None
    assert any(math.dist(p,[60,100])<1 for p in w.doc.shapes[0].points)


def test_right_click_closes_new_polygon_and_tab_toggles(window):
    w=window;c=w.canvas
    w.set_tool('edit');c.setFocus();QTest.keyClick(c,Qt.Key.Key_Tab)
    assert c.tool=='polygon'
    for x,y in [(40,40),(180,40),(180,180)]:QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,x,y))
    QTest.mouseClick(c,Qt.MouseButton.RightButton,pos=screen(c,180,180))
    assert len(w.doc.shapes)==1 and not c.draft
    QTest.keyClick(c,Qt.Key.Key_Tab);assert c.tool=='edit'
    assert not hasattr(w,'operation') and not hasattr(w,'cut_edit')


def test_fade_boundary_shrinks_and_handles_dark_spoke(tmp_path):
    y,x=np.indices((400,400));radius=np.hypot(x-200,y-200)
    level=np.where(radius<140,160,np.clip((170-radius)/30*160,0,160)).astype('uint8')
    level[40:200,190:210]=10
    im=np.repeat(level[:,:,None],3,axis=2);path=tmp_path/'fade.png';Image.fromarray(im).save(path)
    a=detect_view_boundary(path,0,.35);b=detect_view_boundary(path,8,.35)
    assert a is not None and b is not None
    assert a[0][120,200] # narrow dark tissue is not mistaken for outside
    ra=np.mean(np.hypot(a[1][:,0]-200,a[1][:,1]-200))
    rb=np.mean(np.hypot(b[1][:,0]-200,b[1][:,1]-200))
    assert 148<ra<165 and 7<ra-rb<9
    assert not b[0][200,365]


def test_external_boundary_redraw_also_prompts(window,monkeypatch):
    w=window;c=w.canvas;w.doc.shapes=[Shape('测试类别',[[80,60],[200,60],[200,180],[80,180]])];w.commit();w.set_tool('edit')
    QTest.mouseDClick(c,Qt.MouseButton.LeftButton,pos=screen(c,200,60))
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,260,120))
    choices=[];monkeypatch.setattr(c,'choose_reshape_parts',lambda:(choices.append(True) or 'large'))
    QTest.mouseClick(c,Qt.MouseButton.LeftButton,pos=screen(c,200,180))
    assert choices and geometry(w.doc.shapes[0]).area>14400 and not c.reshape_allow_both
