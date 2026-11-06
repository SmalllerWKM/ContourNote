"""A small, independent painter-based annotation canvas."""
from __future__ import annotations

import copy
import hashlib
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QCheckBox, QMenu, QMessageBox, QWidget

from .data import PALETTE, Shape, polygon_points


class Canvas(QWidget):
    operation_failed = Signal(str)
    reshape_failed = Signal(str)
    preferences_changed = Signal()
    changed = Signal()
    draft_changed = Signal()
    selection_changed = Signal()
    zoom_changed = Signal(float)
    message = Signal(str)
    rename_requested = Signal()
    category_requested = Signal()
    interaction_started = Signal()

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(240, 180)
        self.doc = None
        self.image = QImage()
        self.scale = 1.0
        self.fit_mode = True
        self.stroke_width = 1.7
        self.offset = QPointF()
        self.tool = "edit"
        self.label = ""
        self.weak = False
        self.background = False
        self.opacity = 0.22
        self.spacing = 8
        self.selected = set()
        self.hidden = set()
        self.show_annotations = True
        self.draft = []
        self.hover = None
        self.space = False
        self.shift = False
        self.pan_anchor = None
        self.drag_start = None
        self.drag_original = None
        self.vertex = None
        self.operation = "new"
        self.reshape = None
        self.reshape_start_point = None
        self.auto_close_enabled = True
        self.close_distance = 12
        self.wait_for_shift_release = False
        self.reshape_preview = []
        self.reshape_alternative = None
        self.reshape_allow_both = True
        self.auto_closed = None
        self.view_boundary = None
        self.snap_view_enabled = True
        self.view_inset = 4
        self.view_transition = .35

    def set_document(self, doc):
        image = QImage(str(doc.image))
        if image.isNull():
            raise ValueError(f"无法显示图片：{doc.image}")
        self.clear_reshape_alternative()
        self.doc = doc
        self.auto_closed = None
        from .view_boundary import detect_view_boundary
        self.view_boundary = detect_view_boundary(doc.image, self.view_inset, self.view_transition)
        self.image = image
        self.selected.clear()
        self.hidden.clear()
        self.cancel_draft()
        self.fit()

    def fit(self):
        self.fit_mode = True
        if self.image.isNull():
            return
        self.scale = max(.01, min((self.width()-48)/self.image.width(), (self.height()-48)/self.image.height()))
        self.center_image()

    def original_size(self):
        self.fit_mode = False
        self.scale = 1.0
        self.center_image()

    def center_image(self):
        self.offset = QPointF((self.width()-self.image.width()*self.scale)/2,
                              (self.height()-self.image.height()*self.scale)/2)
        self.zoom_changed.emit(self.scale)
        self.update()

    def set_zoom(self, value, anchor=None):
        self.fit_mode = False
        anchor = anchor or QPointF(self.width()/2, self.height()/2)
        point = self.to_image(anchor, clamp=False)
        self.scale = max(.02, min(32., value))
        self.offset = anchor - point*self.scale
        self.zoom_changed.emit(self.scale)
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.image.isNull():
            return
        if self.fit_mode:
            self.fit()
        elif event.oldSize().isValid():
            self.offset += QPointF((event.size().width()-event.oldSize().width())/2,
                                   (event.size().height()-event.oldSize().height())/2)
            self.update()

    def to_image(self, point, clamp=True):
        p = (point-self.offset)/self.scale
        if clamp and self.doc:
            return QPointF(max(0., min(self.doc.width-1., p.x())), max(0., min(self.doc.height-1., p.y())))
        return p

    def on_image(self, position):
        if not self.doc:
            return False
        p = self.to_image(position, False)
        return 0 <= p.x() < self.doc.width and 0 <= p.y() < self.doc.height

    def color(self, shape):
        if shape.background:
            return QColor("#f98b83")
        n = int(hashlib.sha256(shape.label.encode()).hexdigest()[:8], 16)
        return QColor(PALETTE[n % len(PALETTE)])

    def path_for(self, shape):
        path = QPainterPath()
        points = shape.points
        if not points:
            return path
        if shape.shape_type == "circle":
            c, end = points
            r = math.dist(c, end)
            path.addEllipse(QPointF(*c), r, r)
        elif shape.shape_type == "rectangle":
            path.addRect(QRectF(QPointF(*points[0]), QPointF(*points[1])).normalized())
        elif shape.shape_type == "point":
            path.addEllipse(QPointF(*points[0]), 5/self.scale, 5/self.scale)
        else:
            path.moveTo(QPointF(*points[0]))
            for pt in points[1:]:
                path.lineTo(QPointF(*pt))
            if shape.shape_type == "polygon":
                path.closeSubpath()
        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#292b2f") if not self.image.isNull() else QColor("#f4f5f7"))
        if self.image.isNull():
            painter.setPen(QColor("#8c929b"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "打开图像或标注文件\n\nCtrl+O  图像    Ctrl+U  目录")
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.offset)
        painter.scale(self.scale, self.scale)
        painter.drawImage(QPointF(), self.image)
        if self.snap_view_enabled and self.view_boundary is not None and (self.tool == "polygon" or self.reshape is not None):
            painter.setPen(QPen(QColor("#54d7e5"), .9/self.scale, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolygon(QPolygonF([QPointF(float(x),float(y)) for x,y in self.view_boundary[1]]))
        if self.show_annotations and self.doc:
            for i, shape in enumerate(self.doc.shapes):
                if i in self.hidden:
                    continue
                color = self.color(shape)
                pen = QPen(color, (self.stroke_width + (0.7 if i in self.selected else 0))/self.scale)
                if shape.weak:
                    pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                fill = QColor(color)
                fill.setAlphaF(self.opacity)
                painter.setBrush(fill if polygon_points(shape) or shape.shape_type == "point" else Qt.BrushStyle.NoBrush)
                painter.drawPath(self.path_for(shape))
                if i in self.selected and self.tool == "edit":
                    for pt in shape.points:
                        painter.setPen(QPen(QColor("white"), 1/self.scale))
                        painter.setBrush(color)
                        painter.drawEllipse(QPointF(*pt), 4/self.scale, 4/self.scale)
        for points, color in self.reshape_preview:
            fill = QColor(color); fill.setAlphaF(.42)
            painter.setBrush(fill); painter.setPen(QPen(QColor(color), 2/self.scale))
            painter.drawPolygon(QPolygonF([QPointF(*p) for p in points]))
        if self.draft:
            painter.setPen(QPen(QColor("#ffcf79"), self.stroke_width/self.scale))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath(QPointF(*self.draft[0]))
            if self.tool in {"rectangle", "circle"} and self.hover:
                if self.tool == "rectangle":
                    path.addRect(QRectF(QPointF(*self.draft[0]), self.hover).normalized())
                else:
                    path.addEllipse(QPointF(*self.draft[0]), math.dist(self.draft[0], [self.hover.x(), self.hover.y()]),
                                    math.dist(self.draft[0], [self.hover.x(), self.hover.y()]))
            else:
                for pt in self.draft[1:]:
                    path.lineTo(QPointF(*pt))
                if self.hover:
                    path.lineTo(self.hover)
            painter.drawPath(path)
            for pt in self.draft:
                painter.setBrush(QColor("#ffcf79"))
                painter.drawEllipse(QPointF(*pt), 2.5/self.scale, 2.5/self.scale)
            if self.tool == "polygon" and len(self.draft) >= 3 and self.auto_close_enabled:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor("#bdcce0"), 1/self.scale, Qt.PenStyle.DashLine))
                painter.drawEllipse(QPointF(*self.draft[0]), self.close_distance/self.scale, self.close_distance/self.scale)

    def change_tool(self, tool):
        self.clear_reshape_alternative()
        self.cancel_draft()
        self.tool = tool
        self.setCursor(Qt.CursorShape.OpenHandCursor if tool == "pan" else
                       Qt.CursorShape.ArrowCursor if tool == "edit" else Qt.CursorShape.CrossCursor)
        self.setFocus()
        self.update()

    def cancel_draft(self):
        self.draft = []
        self.reshape = None
        self.reshape_start_point = None
        self.hover = None
        self.draft_changed.emit()
        self.update()

    def maybe_auto_close(self, point):
        if not self.auto_close_enabled or self.tool != "polygon" or self.reshape is not None or len(self.draft) < 3:
            return False
        radius = self.close_distance
        if math.dist(self.draft[0], [point.x(), point.y()])*self.scale > radius:
            return False
        distances = [math.dist(a, b)*self.scale for a, b in zip(self.draft, self.draft[1:])]
        if sum(distances) < radius*3 or max(math.dist(self.draft[0], p)*self.scale for p in self.draft) < radius*1.5:
            return False
        from shapely.geometry import Polygon
        region = Polygon(self.draft)
        if not region.is_valid or region.area*self.scale*self.scale < 16:
            return False
        before = self.doc.snapshot()
        selected = set(self.selected)
        points = copy.deepcopy(self.draft)
        self.finish()
        if not self.draft:
            self.auto_closed = (before, points, self.doc.snapshot(), selected)
            self.wait_for_shift_release = True
            self.message.emit("轮廓已自动闭合。松开 Shift 后可开始下一个区域。")
            return True
        return False

    def constrain_to_view(self, point):
        if not self.snap_view_enabled or self.view_boundary is None:
            return point
        import numpy as np
        valid, edge, sx, sy = self.view_boundary
        xy = np.array([point.x(), point.y()])
        direction = np.roll(edge, -1, axis=0)-edge
        t = np.clip(((xy-edge)*direction).sum(axis=1)/np.maximum((direction**2).sum(axis=1),1e-12),0,1)
        projected = edge + t[:,None]*direction
        distances = ((projected-xy)**2).sum(axis=1)
        nearest = int(distances.argmin())
        x,y=int(point.x()/sx),int(point.y()/sy)
        outside = not (0<=x<valid.shape[1] and 0<=y<valid.shape[0] and valid[y,x])
        if outside or distances[nearest]**.5*self.scale<=10:
            return QPointF(*projected[nearest])
        return point

    def add_sample(self, point, force=False):
        point = self.constrain_to_view(point)
        xy = [point.x(), point.y()]
        if not self.draft or math.dist(xy, self.draft[-1])*self.scale >= (0.5 if force else self.spacing):
            self.draft.append(xy)
            self.draft_changed.emit()
            self.update()

    def finish(self):
        if not self.doc:
            return
        if self.reshape is not None:
            self.message.emit("局部重画：请点击同一轮廓的任意边界位置完成，Esc 取消。")
            return
        self.auto_closed = None
        kind = self.tool
        if kind == "scribble":
            kind = "linestrip"
        minimum = 3 if kind == "polygon" else 1 if kind == "point" else 2
        if len(self.draft) < minimum:
            self.message.emit(f"至少需要 {minimum} 个点，Esc 可取消。")
            return
        if kind in {"rectangle", "circle"} and math.dist(self.draft[0], self.draft[-1]) < 1:
            self.cancel_draft()
            return
        if kind == "rectangle" and (abs(self.draft[-1][0]-self.draft[0][0]) < 1 or abs(self.draft[-1][1]-self.draft[0][1]) < 1):
            self.cancel_draft()
            self.message.emit("矩形的宽和高至少需要 1 个原图像素。")
            return
        if kind == "line" and len(self.draft) > 2:
            kind = "linestrip"
        if not self.label.strip():
            self.category_requested.emit()
            if not self.label.strip():
                self.message.emit("请先输入或添加类别；当前路径已保留。")
                return
        shape = Shape(self.label.strip(), copy.deepcopy(self.draft), kind,
                      flags={"weak": self.weak or kind in {"point", "line", "linestrip"},
                             "background": self.background})
        self.doc.shapes.append(shape)
        self.selected = {len(self.doc.shapes)-1}
        self.cancel_draft()
        self.changed.emit()
        self.selection_changed.emit()

    def begin_reshape(self, point, allow_edge=False):
        best = None
        for i, s in enumerate(self.doc.shapes):
            if s.shape_type != "polygon" or s.weak or i in self.hidden:
                continue
            for j, xy in enumerate(s.points):
                distance = math.dist(xy, [point.x(), point.y()])*self.scale
                if distance < 9 and (best is None or distance < best[0]):
                    best = (distance, i, j)
        self.reshape_start_point = None
        if best is None and allow_edge:
            for i, shape in enumerate(self.doc.shapes):
                if shape.shape_type != "polygon" or shape.weak or i in self.hidden:
                    continue
                for j,a in enumerate(shape.points):
                    distance,q = self.edge_projection(point,a,shape.points[(j+1)%len(shape.points)])
                    if distance*self.scale < 9 and (best is None or distance<best[0]):
                        best=(distance,i,j)
                        self.reshape_start_point=q
        if best is None:
            self.message.emit("请双击已有完整多边形的节点或边界，开始重画。")
            return
        _, i, j = best
        self.reshape = (i, j)
        self.selected = {i}
        self.draft = [list(self.reshape_start_point or self.doc.shapes[i].points[j])]
        self.selection_changed.emit()
        self.draft_changed.emit()
        self.message.emit("局部重画：沿新边界点选或 Shift＋左键拖动采点，最后点击同一轮廓的任意边界位置。")

    def clear_reshape_alternative(self):
        self.reshape_alternative = None
        self.reshape_preview = []
        self.update()

    def choose_reshape_parts(self):
        # Default is committed immediately; the canvas offers a non-modal alternative.
        return "large"

    def alternative_hit(self, point):
        if not self.reshape_alternative:
            return False
        i, expected, smaller = self.reshape_alternative
        if not self.doc or i >= len(self.doc.shapes) or self.doc.shapes[i] != expected:
            self.clear_reshape_alternative()
            return False
        return self.path_for(smaller).contains(point)

    def reshape_boundary_hit(self, point, notify=False):
        if self.reshape is None:
            return False
        i, start = self.reshape
        if not 0 <= i < len(self.doc.shapes):
            self.cancel_draft()
            return False
        source = self.doc.shapes[i]
        best = None
        for j, a in enumerate(source.points):
            b = source.points[(j+1) % len(source.points)]
            distance, q = self.edge_projection(point, a, b)
            if distance*self.scale <= 12 and math.dist(q, self.draft[0])*self.scale > 1:
                if best is None or distance < best[0]:
                    best = (distance, j, q)
        if best is None:
            return False
        _, j, q = best
        self._reshape_error = None
        self.finish_reshape(j, q)

        return True

    def finish_reshape(self, end_index, end_point=None):
        from shapely.geometry import Polygon
        from .data import simple_polygons
        i, start = self.reshape
        source = copy.deepcopy(self.doc.shapes[i])
        start_xy = list(self.reshape_start_point or source.points[start])
        end_xy = list(end_point or source.points[end_index])
        ring=[]
        for j,a in enumerate(source.points):
            b=source.points[(j+1)%len(source.points)]
            ring.append(a)
            additions=[]
            for xy in [start_xy,end_xy]:
                distance,q=self.edge_projection(QPointF(*xy),a,b)
                if distance<1e-7 and math.dist(q,a)>1e-7 and math.dist(q,b)>1e-7:
                    additions.append(q)
            for q in sorted(additions,key=lambda q:math.dist(a,q)):
                if math.dist(ring[-1],q)>1e-7:
                    ring.append(q)
        source.points=ring
        start=min(range(len(ring)),key=lambda j:math.dist(ring[j],start_xy))
        end_index=min(range(len(ring)),key=lambda j:math.dist(ring[j],end_xy))
        if start == end_index or not self.draft:
            self._reshape_error = "终点与起点重合，请接到原轮廓的另一处边界。"
            self.message.emit(self._reshape_error)
            self.reshape_failed.emit(self._reshape_error)
            return
        n = len(source.points)
        def walk(step):
            current = end_index
            points = []
            for _ in range(n+1):
                points.append(source.points[current])
                if current == start:
                    break
                current = (current+step) % n
            return points
        tail = copy.deepcopy(self.draft[1:])
        if tail and math.dist(tail[-1], end_xy)*self.scale <= 12:
            tail[-1] = end_xy
        paths = [walk(step)+tail for step in [1, -1]]
        if any(len(path)<3 for path in paths):
            self._reshape_error = "新路径沿原边线重合，没有围出区域；请先画入区域内部或外侧，再接回另一处边界。"
            self.message.emit(self._reshape_error)
            self.reshape_failed.emit(self._reshape_error)
            return
        candidates = [Polygon(path) for path in paths]
        if any(not g.is_valid or g.area < 1 for g in candidates):
            self._reshape_error = "新边界与原边界无法组成两个有效区域：请检查是否自交、反复跨越原轮廓或沿原边线重画。"
            self.message.emit(self._reshape_error)
            self.reshape_failed.emit(self._reshape_error)
            return
        larger, smaller = sorted(candidates, key=lambda g: g.area, reverse=True)
        base = Polygon(source.points)
        self.reshape_allow_both = larger.intersection(smaller).area < .001
        self.reshape_preview = [(list(smaller.exterior.coords), "#92979f")]
        self.update()
        try:
            choice = self.choose_reshape_parts()
        finally:
            self.reshape_preview = []
            self.update()
        if choice == "cancel":
            return
        geometries = [larger, smaller] if choice == "both" and self.reshape_allow_both else [larger if choice == "large" else smaller]
        import uuid
        replacements = []
        for g in geometries:
            group = source.group_id if source.group_id is not None else int(uuid.uuid4().hex[:12], 16)
            for part in simple_polygons(g):
                replacements.append(Shape(source.label, [list(p) for p in list(part.exterior.coords)[:-1]],
                                          group_id=group, flags=dict(source.flags), description=source.description, extra=copy.deepcopy(source.extra)))
        self.doc.shapes[i:i+1] = replacements
        self.selected = set(range(i, i+len(replacements)))
        self.hidden.clear()
        self.cancel_draft()
        self.changed.emit()
        self.selection_changed.emit()
        if choice == "large" and len(replacements) == 1:
            alternate = copy.deepcopy(replacements[0])
            alternate.points = [list(p) for p in list(smaller.exterior.coords)[:-1]]
            self.reshape_alternative = (i, copy.deepcopy(replacements[0]), alternate)
            self.reshape_preview = [(alternate.points, "#92979f")]
            self.message.emit("已默认保留大块；如需小块，请双击灰色区域。")
            self.update()

    @staticmethod
    def edge_projection(p, a, b):
        dx, dy = b[0]-a[0], b[1]-a[1]
        t = max(0., min(1., ((p.x()-a[0])*dx+(p.y()-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
        q = [a[0]+t*dx, a[1]+t*dy]
        return math.dist([p.x(), p.y()], q), q

    def nearest_vertex(self, point):
        best = None
        for i in self.selected:
            if i >= len(self.doc.shapes) or i in self.hidden:
                continue
            for j, xy in enumerate(self.doc.shapes[i].points):
                distance = math.dist([point.x(), point.y()], xy)*self.scale
                if distance < 9 and (best is None or distance < best[0]):
                    best = (distance, i, j)
        return (best[1], best[2]) if best else None

    def hit(self, point):
        if not self.show_annotations:
            return None
        for i in reversed(range(len(self.doc.shapes))):
            if i in self.hidden:
                continue
            s = self.doc.shapes[i]
            if self.path_for(s).contains(point):
                return i
            pts = s.points
            if any(math.dist([point.x(), point.y()], p)*self.scale < 9 for p in pts):
                return i
            pairs = list(zip(pts, pts[1:]))
            if s.shape_type == "polygon":
                pairs.append((pts[-1], pts[0]))
            if any(self.edge_projection(point, a, b)[0]*self.scale < 7 for a, b in pairs):
                return i
        return None

    def mousePressEvent(self, event):
        self.interaction_started.emit()
        self.setFocus()
        if not self.doc:
            return
        p = self.to_image(event.position())
        if self.reshape_alternative and event.button() == Qt.MouseButton.LeftButton:
            if self.alternative_hit(p):
                return
            self.clear_reshape_alternative()
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and (
                self.space or self.tool == "pan" or event.modifiers() & Qt.KeyboardModifier.AltModifier)):
            self.pan_anchor = event.position()
            self.fit_mode = False
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() == Qt.MouseButton.RightButton:
            if self.reshape is not None:
                if not self.reshape_boundary_hit(p, notify=True):
                    self.message.emit("请将新边界接回原轮廓；右键终点也需落在原边界。")
                return
            if self.draft:
                self.finish()
            else:
                self.context_menu(event, p)
            return
        if event.button() != Qt.MouseButton.LeftButton or not self.on_image(event.position()):
            return
        self.wait_for_shift_release = False
        if self.reshape is not None:
            if not self.reshape_boundary_hit(p, notify=True):
                self.add_sample(p, True)
            self.update()
            return
        if self.tool == "edit":
            target = self.hit(p)
            if target is not None and target not in self.selected:
                self.selected = {target}
                self.selection_changed.emit()
            self.vertex = self.nearest_vertex(p)
            if not self.vertex and target is not None:
                shape=self.doc.shapes[target]
                if shape.shape_type=="polygon":
                    best=min(((*self.edge_projection(p,a,shape.points[(j+1)%len(shape.points)]),j)
                              for j,a in enumerate(shape.points)),key=lambda v:v[0])
                    distance,q,j=best
                    if distance*self.scale<9:
                        shape.points.insert(j+1,q)
                        self.vertex=(target,j+1)
                        self.changed.emit()
            if not self.vertex and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                for i in self.selected:
                    s = self.doc.shapes[i]
                    if s.shape_type not in {"polygon", "linestrip"}:
                        continue
                    pairs = list(zip(s.points, s.points[1:]))
                    if s.shape_type == "polygon":
                        pairs.append((s.points[-1], s.points[0]))
                    for j, (a, b) in enumerate(pairs):
                        distance, q = self.edge_projection(p, a, b)
                        if distance*self.scale < 9:
                            s.points.insert(j+1, q)
                            self.changed.emit()
                            self.update()
                            return
            if not self.vertex:
                target = self.hit(p)
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if target is not None:
                        self.selected.symmetric_difference_update({target})
                else:
                    if target not in self.selected:
                        self.selected = {target} if target is not None else set()
                self.selection_changed.emit()
            self.drag_start = p
            self.drag_original = copy.deepcopy(self.doc.shapes)
            self.update()
            return
        if self.tool == "polygon":
            p = self.constrain_to_view(p)
        if self.tool == "point":
            p = self.constrain_to_view(p)
            self.draft = [[p.x(), p.y()]]
            self.finish()
        elif self.tool in {"rectangle", "circle", "scribble"}:
            p = self.constrain_to_view(p)
            self.draft = [[p.x(), p.y()]]
            self.hover = p
            self.draft_changed.emit()
        elif self.tool in {"polygon", "line", "linestrip"}:
            if self.tool == "polygon" and len(self.draft) >= 3 and math.dist(self.draft[0], [p.x(), p.y()])*self.scale < self.close_distance:
                self.finish()
            else:
                self.add_sample(p, True)
        self.update()

    def mouseMoveEvent(self, event):
        if not self.doc:
            return
        p = self.to_image(event.position())
        self.hover = self.constrain_to_view(p) if self.tool in {"polygon", "line", "linestrip", "scribble", "rectangle", "circle"} or self.reshape is not None else p
        if self.tool == "polygon" and self.reshape is None:
            p = self.hover
        if not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.wait_for_shift_release = False
        if self.pan_anchor is not None:
            self.offset += event.position()-self.pan_anchor
            self.pan_anchor = event.position()
        elif self.drag_start is not None and self.tool == "edit" and event.buttons() & Qt.MouseButton.LeftButton:
            if self.vertex:
                i, j = self.vertex
                p = self.constrain_to_view(p)
                self.doc.shapes[i].points[j] = [p.x(), p.y()]
            elif self.selected:
                dx, dy = p.x()-self.drag_start.x(), p.y()-self.drag_start.y()
                all_points = [pt for i in self.selected for pt in self.drag_original[i].points]
                dx = max(-min(x for x, y in all_points), min(dx, self.doc.width-1-max(x for x, y in all_points)))
                dy = max(-min(y for x, y in all_points), min(dy, self.doc.height-1-max(y for x, y in all_points)))
                for i in self.selected:
                    self.doc.shapes[i].points = [[x+dx, y+dy] for x, y in self.drag_original[i].points]
            self.draft_changed.emit()  # timer saves in-progress drags too
        elif self.tool == "scribble" and self.draft and event.buttons() & Qt.MouseButton.LeftButton:
            self.add_sample(p)
        elif (self.tool in {"polygon", "line", "linestrip"} or self.reshape is not None) and (
                event.modifiers() & Qt.KeyboardModifier.ShiftModifier) and (
                event.buttons() & Qt.MouseButton.LeftButton) and self.on_image(event.position()):
            if not self.wait_for_shift_release:
                if self.reshape is not None:
                    # A deliberate click, never hover/drag proximity, confirms the end.
                    self.add_sample(p)
                elif not self.maybe_auto_close(p):
                    self.add_sample(p)
        elif self.tool == "polygon" and self.draft and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier and self.on_image(event.position()):
            self.maybe_auto_close(p)
        self.update()

    def mouseReleaseEvent(self, event):
        if self.pan_anchor is not None:
            self.pan_anchor = None
            self.setCursor(Qt.CursorShape.OpenHandCursor if self.space or self.tool == "pan" else Qt.CursorShape.CrossCursor if self.tool != "edit" else Qt.CursorShape.ArrowCursor)
        elif self.drag_start is not None:
            if self.drag_original != self.doc.shapes:
                self.changed.emit()
            self.drag_start = self.drag_original = self.vertex = None
        elif event.button() == Qt.MouseButton.LeftButton and self.draft and self.tool in {"rectangle", "circle", "scribble"}:
            p = self.to_image(event.position())
            self.add_sample(p, True)
            if len(self.draft) >= 2:
                self.finish()
            else:
                self.cancel_draft()
        self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.alternative_hit(self.to_image(event.position())):
            i, expected, smaller = self.reshape_alternative
            self.doc.shapes[i] = copy.deepcopy(smaller)
            self.clear_reshape_alternative()
            self.changed.emit()
            self.selection_changed.emit()
            self.message.emit("已切换为保留小块。")
            event.accept()
            return
        if self.tool == "edit" and self.doc and event.button()==Qt.MouseButton.LeftButton:
            self.drag_start=self.drag_original=self.vertex=None
            if self.reshape is None:
                self.begin_reshape(self.to_image(event.position()), allow_edge=True)
            event.accept()
            return
        if self.tool in {"polygon", "line", "linestrip"} and event.button() == Qt.MouseButton.LeftButton:
            self.finish()

    def context_menu(self, event, point):
        vertex = self.nearest_vertex(point)
        target = self.hit(point)
        if target is None:
            return
        if vertex is None:
            self.selected = {target}
        self.selection_changed.emit()
        menu = QMenu(self)
        remove_vertex = menu.addAction("删除此节点") if vertex else None
        rename = menu.addAction("修改类别…")
        delete = menu.addAction("删除选中标记")
        action = menu.exec(event.globalPosition().toPoint())
        if remove_vertex and action == remove_vertex:
            i, j = vertex
            s = self.doc.shapes[i]
            minimum = 3 if s.shape_type == "polygon" else 2
            if s.shape_type in {"polygon", "linestrip"} and len(s.points) > minimum:
                s.points.pop(j)
            else:
                self.selected = {i}
                self.delete_selected()
                return
            self.changed.emit()
        elif action == rename:
            self.rename_requested.emit()
        elif action == delete:
            self.delete_selected()
        self.update()

    def delete_selected(self):
        if self.doc and self.selected:
            self.cancel_draft()
            self.doc.shapes = [s for i, s in enumerate(self.doc.shapes) if i not in self.selected]
            self.selected.clear()
            self.hidden.clear()
            self.changed.emit()
            self.selection_changed.emit()
            self.update()

    def wheelEvent(self, event):
        self.interaction_started.emit()
        self.set_zoom(self.scale * (1.15 if event.angleDelta().y() > 0 else 1/1.15), event.position())
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.space = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.clear_reshape_alternative()
            if self.drag_original is not None:
                self.doc.shapes = self.drag_original
                self.drag_start = self.drag_original = self.vertex = None
            self.cancel_draft()
            self.draft_changed.emit()
        elif event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter} and self.draft:
            self.finish()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Shift:
            self.wait_for_shift_release = False
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.space = False
            self.setCursor(Qt.CursorShape.OpenHandCursor if self.tool == "pan" else Qt.CursorShape.ArrowCursor if self.tool == "edit" else Qt.CursorShape.CrossCursor)
        super().keyReleaseEvent(event)

    def focusOutEvent(self, event):
        self.space = False
        self.pan_anchor = None
        super().focusOutEvent(event)
