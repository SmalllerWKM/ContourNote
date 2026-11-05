import copy
import json
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from PySide6.QtCore import QPointF, Qt, QThreadPool
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox
from clinical_annotator.app import MainWindow
from clinical_annotator.data import Shape
from clinical_annotator.view_boundary import detect_view_boundary
from test_gui import screen, move


def window(qt_app, tmp_path):
    image = tmp_path / 'first.png'
    Image.new('RGB', (400, 300), '#888888').save(image)
    w = MainWindow(); w.show(); qt_app.processEvents(); assert w.open_path(image)
    w.register_category('target'); w.label_input.setCurrentText('target')
    return w


def test_edit_cut_ends_on_edge_and_preserves_metadata(qt_app, tmp_path, monkeypatch):
    w = window(qt_app, tmp_path); c = w.canvas
    w.doc.shapes = [Shape('target', [[40,40],[300,40],[300,240],[40,240]],
        description='original', extra={'custom':'metadata'})]
    w.commit(); w.set_tool('edit')
    original = copy.deepcopy(w.doc.shapes[0])
    QTest.mouseDClick(c, Qt.MouseButton.LeftButton, pos=screen(c,40,40))
    assert c.reshape == (0,0)
    QTest.mouseClick(c, Qt.MouseButton.LeftButton, pos=screen(c,150,140))
    monkeypatch.setattr(c, 'choose_reshape_parts', lambda: 'both')
    QTest.mouseClick(c, Qt.MouseButton.LeftButton, pos=screen(c,300,140))
    assert len(w.doc.shapes)==2 and not c.draft
    from shapely.geometry import Polygon
    assert abs(sum(Polygon(s.points).area for s in w.doc.shapes)-Polygon(original.points).area)<1
    assert all(s.description=='original' and s.extra==original.extra for s in w.doc.shapes)
    w.undo(); assert w.doc.shapes==[original]
    w.close()


def test_auto_close_undo_restores_all_vertices_and_disk_draft(qt_app, tmp_path):
    w=window(qt_app,tmp_path);c=w.canvas;w.set_tool('polygon')
    for x,y in [(40,40),(200,40),(200,200),(40,200)]:
        move(c,x,y,Qt.KeyboardModifier.ShiftModifier,Qt.MouseButton.LeftButton)
    before=copy.deepcopy(c.draft)
    move(c,42,42,Qt.KeyboardModifier.ShiftModifier,Qt.MouseButton.LeftButton)
    assert len(w.doc.shapes)==1 and not c.draft
    w.undo()
    assert not w.doc.shapes and c.draft==before
    assert json.loads(w.draft_path().read_text())['points']==before
    assert not json.loads(w.label_path().read_text())['shapes']
    w.undo(); assert c.draft==before[:-1]
    c.cancel_draft();w.close()


def test_round_view_padding_and_interior_black_hole(qt_app,tmp_path):
    image=Image.new('RGB',(400,400),'black');draw=ImageDraw.Draw(image)
    draw.ellipse((40,40,360,360),fill='#888888');draw.ellipse((180,180,220,220),fill='black')
    path=tmp_path/'circle.png';image.save(path)
    result=detect_view_boundary(path);assert result is not None
    valid,edge,sx,sy=result
    assert not valid[0,0] and valid[200,200]
    w=MainWindow();w.show();qt_app.processEvents();assert w.open_path(path);c=w.canvas
    w.register_category('target');w.label_input.setCurrentText('target');w.set_tool('polygon')
    c.add_sample(QPointF(356,200),True)
    assert 350 <= c.draft[-1][0] <= 358
    # Every accepted sample is stored verbatim, including >5000 points.
    c.snap_view_enabled=False
    c.draft=[[float(i%300),float(i//300)] for i in range(5001)]
    c.add_sample(QPointF(350,250),True);before=copy.deepcopy(c.draft)
    c.finish();assert w.doc.shapes[-1].points==before and len(before)==5002
    assert json.loads(w.label_path().read_text())['shapes'][-1]['points']==before
    w.close()


def test_large_project_json_reads_are_background_and_switch_is_local(qt_app,tmp_path,monkeypatch):
    w=window(qt_app,tmp_path)
    images=[w.doc.image]+[tmp_path/f'frame_{i:05}.png' for i in range(1001)]
    original=Path.read_text;threads=[]
    def read(path,*a,**kw):
        if path.name.startswith('frame_'):
            threads.append(threading.get_ident())
        return original(path,*a,**kw)
    for p in images[1:]:p.with_suffix('.json').write_text('{"shapes":[]}')
    monkeypatch.setattr(Path,'read_text',read)
    assert w.load_images(images)
    assert w.file_list.count()==1002
    for _ in range(100):
        qt_app.processEvents();QTest.qWait(2)
        if threads:break
    assert threads and all(t!=threading.get_ident() for t in threads)
    generation=w._index_generation
    w.switch_frame(0);assert generation==w._index_generation
    w.close();QThreadPool.globalInstance().waitForDone(3000)


def test_cut_cancel_and_outside_path_leave_original(qt_app,tmp_path,monkeypatch):
    w=window(qt_app,tmp_path);c=w.canvas
    original=Shape('target',[[40,40],[300,40],[300,240],[40,240]])
    w.doc.shapes=[copy.deepcopy(original)];w.commit();w.set_tool('edit')
    c.begin_reshape(QPointF(40,40));c.add_sample(QPointF(150,140),True)
    monkeypatch.setattr(c,'choose_reshape_parts',lambda:'cancel')
    assert c.reshape_boundary_hit(QPointF(300,140))
    assert w.doc.shapes==[original] and c.reshape is not None
    c.cancel_draft();c.begin_reshape(QPointF(40,40));c.add_sample(QPointF(350,20),True)
    c.reshape_boundary_hit(QPointF(300,140));assert w.doc.shapes==[original]
    c.cancel_draft();w.close()
