"""Compact desktop chrome and independently drawn monochrome tool icons."""
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMenu, QPushButton,
    QSlider, QSpinBox, QSplitter,
    QToolButton, QVBoxLayout, QWidget, QSizePolicy,
)

from .canvas import Canvas

STYLE = """
QMainWindow, QWidget { font-family: '.AppleSystemUIFont', sans-serif; font-size: 12px; color: #30343b; }
QMainWindow, QWidget#workspace { background: #fff; }
QFrame#topbar { background: #fafafa; border-bottom: 1px solid #dedfe2; }
QLabel#brand { font-size: 14px; font-weight: 600; color: #33383e; }
QLabel#section { font-size: 11px; color: #858a93; font-weight: 500; }
QLabel#muted { color: #888e97; font-size: 11px; }
QLabel#saved { color: #657061; font-size: 11px; }
QWidget#rail { background: #f8f8f9; border-right: 1px solid #e2e3e6; }
QToolButton { background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 5px; }
QToolButton:hover { background: #ededf0; }
QToolButton:checked { background: #e7edf7; border-color: #d1def2; color: #285b9d; }
QPushButton { background: #fff; border: 1px solid #dadde2; border-radius: 4px; padding: 5px 10px; }
QPushButton:hover { background: #f2f4f7; border-color: #adb9c9; }
QLineEdit, QComboBox, QSpinBox, QTextEdit { background: #fff; border: 1px solid #dfe1e6; border-radius: 3px; padding: 4px; selection-background-color: #dce8f8; selection-color: #223852; }
QListWidget { border: none; background: #fff; outline: none; }
QListWidget::item { padding: 5px 7px; min-height: 22px; border: none; border-radius: 3px; }
QListWidget::item:selected { background: #e9eff8; color: #21466f; }
QListWidget::item:hover:!selected { background: #f5f6f8; }
QGroupBox { border: none; margin-top: 14px; padding-top: 10px; }
QGroupBox::title { color: #858a93; subcontrol-origin: margin; }
QScrollArea { border: none; background: #fff; }
QSplitter::handle { background: #e8e9ec; }
QStatusBar { background: #fafafa; border-top: 1px solid #e3e4e7; color: #898f98; font-size: 11px; }
QMenu { background: white; border: 1px solid #dfe1e6; padding: 4px; }
QMenu::item { padding: 6px 22px; }
QMenu::item:selected { background: #e9eff8; }
"""


def icon(kind):
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(2, 2)
    p.setPen(QPen(QColor("#535b66"), 1.45, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    if kind == "polygon":
        pts = [(5, 6), (18, 4), (20, 17), (9, 20)]
        path = QPainterPath(QPointF(*pts[0]))
        for xy in pts[1:]: path.lineTo(QPointF(*xy))
        path.closeSubpath(); p.drawPath(path)
        p.setBrush(QColor("#fafafa"))
        for xy in pts: p.drawRect(QRectF(xy[0]-1.5, xy[1]-1.5, 3, 3))
    elif kind == "rectangle":
        p.drawRect(QRectF(4, 6, 16, 12))
        p.setBrush(QColor("#fafafa"))
        p.drawRect(QRectF(3, 5, 3, 3)); p.drawRect(QRectF(18, 16, 3, 3))
    elif kind == "point":
        p.drawEllipse(QPointF(12, 12), 4, 4)
        for a, b in [((12, 3), (12, 6)), ((12, 18), (12, 21)), ((3, 12), (6, 12)), ((18, 12), (21, 12))]:
            p.drawLine(QPointF(*a), QPointF(*b))
    elif kind == "line":
        p.drawLine(QPointF(5, 18), QPointF(19, 6))
        p.setBrush(QColor("#fafafa"))
        p.drawEllipse(QPointF(5, 18), 2, 2); p.drawEllipse(QPointF(19, 6), 2, 2)
    elif kind == "scribble":
        path = QPainterPath(QPointF(4, 16)); path.cubicTo(20, -4, 6, 26, 19, 6)
        p.drawPath(path)
    elif kind == "circle": p.drawEllipse(QRectF(4, 4, 16, 16))
    elif kind == "edit":
        path = QPainterPath(QPointF(6, 3))
        for xy in [(6, 19), (10, 15), (13, 21), (16, 20), (13, 14), (19, 13)]: path.lineTo(QPointF(*xy))
        path.closeSubpath(); p.drawPath(path)
    elif kind == "pan":
        path = QPainterPath(QPointF(5, 13)); path.lineTo(5, 9); path.quadTo(6.5, 7, 8, 9)
        path.lineTo(8, 5); path.quadTo(9.5, 3, 11, 5); path.lineTo(11, 10)
        path.lineTo(11, 4); path.quadTo(12.5, 2, 14, 4); path.lineTo(14, 10)
        path.lineTo(14, 6); path.quadTo(15.5, 4, 17, 6); path.lineTo(17, 12)
        path.quadTo(21, 10, 20, 14); path.lineTo(17, 21); path.lineTo(10, 21); path.closeSubpath()
        p.drawPath(path)
    elif kind in {"undo", "redo"}:
        if kind == "redo": p.translate(24, 0); p.scale(-1, 1)
        path = QPainterPath(QPointF(5, 9)); path.cubicTo(21, 4, 22, 21, 10, 19); p.drawPath(path)
        p.drawLine(QPointF(5, 9), QPointF(9, 4)); p.drawLine(QPointF(5, 9), QPointF(10, 13))
    elif kind in {"folder", "open"}:
        path = QPainterPath(QPointF(3, 7))
        for xy in [(3, 19), (21, 19), (21, 7), (12, 7), (10, 4), (3, 4)]: path.lineTo(QPointF(*xy))
        path.closeSubpath(); p.drawPath(path)
    elif kind in {"json", "save", "export"}:
        p.drawRoundedRect(QRectF(5, 3, 14, 18), 1, 1)
        if kind == "json":
            p.drawText(QRectF(5, 4, 14, 16), Qt.AlignmentFlag.AlignCenter, "{ }")
        elif kind == "save": p.drawRect(QRectF(8, 3, 8, 6)); p.drawRect(QRectF(8, 14, 8, 7))
        else:
            p.drawLine(QPointF(12, 7), QPointF(12, 17))
            p.drawLine(QPointF(8, 13), QPointF(12, 17)); p.drawLine(QPointF(16, 13), QPointF(12, 17))
    elif kind == "plus":
        p.drawLine(QPointF(5, 12), QPointF(19, 12)); p.drawLine(QPointF(12, 5), QPointF(12, 19))
    elif kind == "delete":
        p.drawLine(QPointF(4, 6), QPointF(20, 6)); p.drawRect(QRectF(7, 6, 10, 14))
        p.drawLine(QPointF(9, 3), QPointF(15, 3)); p.drawLine(QPointF(10, 10), QPointF(10, 16)); p.drawLine(QPointF(14, 10), QPointF(14, 16))
    elif kind == "eye":
        path = QPainterPath(QPointF(3, 12)); path.quadTo(12, 1, 21, 12); path.quadTo(12, 23, 3, 12); p.drawPath(path)
        p.drawEllipse(QPointF(12, 12), 3, 3)
    p.end()
    return QIcon(pixmap)


def tool(text, callback, kind=None):
    b = QToolButton()
    b.setText(text)
    if kind:
        b.setIcon(icon(kind)); b.setIconSize(QSize(18, 18))
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    b.clicked.connect(callback)
    return b


def label(text, section=False):
    w = QLabel(text)
    w.setObjectName("section" if section else "muted")
    return w


def separator():
    line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #e9e9ec;")
    return line


def build_window(w, tools, combo):
    w.setWindowTitle("ContourNote · 临绘")
    w.resize(1380, 900)
    w.setMinimumSize(900, 600)
    root = QWidget(); root.setObjectName("workspace")
    layout = QVBoxLayout(root); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
    w.setCentralWidget(root)
    bar = QFrame(); bar.setObjectName("topbar")
    top = QHBoxLayout(bar); top.setContentsMargins(14, 5, 12, 5); top.setSpacing(10)
    brand = QLabel("ContourNote"); brand.setObjectName("brand"); top.addWidget(brand); top.addSpacing(14)
    for text, callback, glyph in [("打开目录", w.open_folder, "folder"), ("打开图像", w.open_file, "open"),
                                   ("打开标注", w.open_annotation, "json"), ("保存", w.save_live, "save")]:
        top.addWidget(tool(text, callback, glyph))
    top.addStretch()
    w.autosave = QCheckBox("自动保存"); w.autosave.setChecked(True)
    w.autosave.toggled.connect(w.autosave_toggled); top.addWidget(w.autosave)
    top.addSpacing(12); top.addWidget(tool("导出", w.export_project, "export"))
    maximize = tool("最大化", w.toggle_maximized)
    maximize.setToolTip("最大化 / 还原窗口；F11 全屏")
    top.addWidget(maximize)
    layout.addWidget(bar)

    frame_bar = QFrame(); frame_bar.setObjectName("topbar")
    frame_row = QHBoxLayout(frame_bar); frame_row.setContentsMargins(12, 4, 12, 4); frame_row.setSpacing(8)
    w.previous_frame_button = tool("← 上一帧", lambda: w.navigate(-1))
    w.next_frame_button = tool("下一帧 →", lambda: w.navigate(1))
    w.copy_frame_button = tool("复制上一帧", w.copy_previous)
    w.propagate_frame_button = tool("复制到后续帧", w.propagate)
    for control in [w.previous_frame_button, w.next_frame_button, w.copy_frame_button]:
        frame_row.addWidget(control)
    frame_row.addWidget(label("复制到后第"))
    w.copy_frame_count = QSpinBox(); w.copy_frame_count.setRange(1, 1000000); w.copy_frame_count.setValue(1)
    w.copy_frame_count.setSuffix(" 帧"); w.copy_frame_count.setToolTip("连续复制后续 X 帧，X 默认为 1")
    frame_row.addWidget(w.copy_frame_count); frame_row.addWidget(w.propagate_frame_button)
    w.weak_copy = QCheckBox("仅复用弱标注"); w.weak_copy.setChecked(True); frame_row.addWidget(w.weak_copy)
    frame_row.addStretch(); layout.addWidget(frame_bar)
    play_bar = QFrame(); play_bar.setObjectName("topbar")
    play_row = QHBoxLayout(play_bar); play_row.setContentsMargins(12, 4, 12, 4)
    play_row.addWidget(label("图片放映"))
    w.slideshow_interval = QDoubleSpinBox(); w.slideshow_interval.setRange(0.1, 120); w.slideshow_interval.setDecimals(1)
    w.slideshow_interval.setSingleStep(0.1); w.slideshow_interval.setValue(1.0); w.slideshow_interval.setSuffix(" 秒 / 张")
    w.slideshow_interval.valueChanged.connect(w.update_slideshow_interval); play_row.addWidget(w.slideshow_interval)
    w.slideshow_loop = QCheckBox("循环"); play_row.addWidget(w.slideshow_loop)
    w.slideshow_button = QPushButton("开始放映"); w.slideshow_button.clicked.connect(w.toggle_slideshow); play_row.addWidget(w.slideshow_button)
    w.slideshow_status = label(""); play_row.addWidget(w.slideshow_status); play_row.addStretch()
    layout.addWidget(play_bar)

    body = QHBoxLayout(); body.setContentsMargins(0, 0, 0, 0); body.setSpacing(0); layout.addLayout(body, 1)
    rail = QWidget(); rail.setObjectName("rail")
    rl = QVBoxLayout(rail); rl.setContentsMargins(5, 8, 5, 8); rl.setSpacing(3)
    w.tool_buttons = {}
    for kind, text, key in tools:
        names = {"edit": "选择编辑", "polygon": "多边形", "rectangle": "矩形框", "point": "标记点", "line": "折线", "scribble": "涂鸦", "circle": "圆形", "pan": "平移"}
        b = tool(f"{names[kind]}  {key}", lambda checked=False, t=kind: w.set_tool(t), kind)
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        b.setIconSize(QSize(20, 20)); b.setMinimumHeight(max(38, b.sizeHint().height())); b.setCheckable(True)
        b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        b.setToolTip(f"{text}  {key}"); w.tool_buttons[kind] = b; rl.addWidget(b)
    rail.setFixedWidth(max(112, max(b.sizeHint().width() for b in w.tool_buttons.values())+14))
    rl.addWidget(separator()); rl.addWidget(tool("", w.undo, "undo")); rl.itemAt(rl.count()-1).widget().setToolTip("撤销 Ctrl+Z")
    rl.addWidget(tool("", w.redo, "redo")); rl.itemAt(rl.count()-1).widget().setToolTip("重做 Ctrl+Y")
    rl.addStretch()
    w.licenses_button = tool("开源许可", w.show_licenses)
    rl.addWidget(w.licenses_button)
    body.addWidget(rail)

    splitter = QSplitter(); body.addWidget(splitter, 1)
    middle = QWidget(); ml = QVBoxLayout(middle); ml.setContentsMargins(0, 0, 0, 0); ml.setSpacing(0)
    settings = QWidget(); sr = QHBoxLayout(settings); sr.setContentsMargins(12, 6, 12, 6)
    w.image_info = QLabel("未打开图像"); w.image_info.setObjectName("muted"); sr.addWidget(w.image_info, 1)
    w.image_info.setMinimumWidth(0); w.image_info.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    sr.addStretch()
    sr.addWidget(label("线宽"))
    w.outline_width = QDoubleSpinBox(); w.outline_width.setRange(0.5, 8); w.outline_width.setDecimals(1)
    w.outline_width.setSingleStep(0.5); w.outline_width.setValue(1.7); w.outline_width.setSuffix(" px")
    w.outline_width.setFixedWidth(76); w.outline_width.valueChanged.connect(w.set_outline_width); sr.addWidget(w.outline_width)
    drawing = QToolButton(); drawing.setText("绘制设置 ▾")
    menu = QMenu(drawing)
    from PySide6.QtWidgets import QWidgetAction
    panel = QWidget(); form = QFormLayout(panel)
    w.sample_spacing = QSpinBox(); w.sample_spacing.setRange(2, 40); w.sample_spacing.setValue(8); w.sample_spacing.setSuffix(" px")
    w.sample_spacing.valueChanged.connect(lambda v: setattr(w.canvas, "spacing", v))
    form.addRow("Shift 采点间距", w.sample_spacing)
    w.auto_close = QCheckBox("接近起点自动闭合"); w.auto_close.setChecked(True)
    w.auto_close.toggled.connect(lambda v: setattr(w.canvas, "auto_close_enabled", v)); form.addRow(w.auto_close)
    w.close_distance = QSpinBox(); w.close_distance.setRange(5,30); w.close_distance.setValue(12); w.close_distance.setSuffix(" px")
    w.close_distance.valueChanged.connect(lambda v: setattr(w.canvas,"close_distance",v)); form.addRow("闭合距离",w.close_distance)
    w.snap_view = QCheckBox("吸附有效视野边缘（含渐变过渡区）"); w.snap_view.setChecked(True)
    w.snap_view.toggled.connect(lambda v: (setattr(w.canvas,"snap_view_enabled",v),w.persist_categories() if not w.loading else None)); form.addRow(w.snap_view)
    w.view_inset = QSpinBox(); w.view_inset.setRange(0,30); w.view_inset.setValue(4); w.view_inset.setSuffix(" 原图 px")
    w.view_inset.valueChanged.connect(w.update_view_boundary); form.addRow("视野向内收缩",w.view_inset)
    w.view_transition = QSpinBox(); w.view_transition.setRange(15,70); w.view_transition.setValue(35); w.view_transition.setSuffix(" %")
    w.view_transition.valueChanged.connect(w.update_view_boundary); form.addRow("过渡区剔除强度",w.view_transition)
    action = QWidgetAction(menu); action.setDefaultWidget(panel); menu.addAction(action)
    drawing.setMenu(menu); drawing.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup); sr.addWidget(drawing)
    ml.addWidget(settings)
    w.operation_notice = QWidget()
    notice_row = QHBoxLayout(w.operation_notice); notice_row.setContentsMargins(0,0,4,0)
    w.operation_hint = QLabel(); w.operation_hint.setWordWrap(True)
    notice_row.addWidget(w.operation_hint,1)
    w.dismiss_operation_notice = tool("关闭提示",w.dismiss_notice)
    w.dismiss_operation_notice.setToolTip("关闭提示，保留当前草稿")
    notice_row.addWidget(w.dismiss_operation_notice)
    w.operation_hint.setStyleSheet("color:#8b5d21; padding:6px; background:#fff8ea;")
    w.operation_notice.hide(); ml.addWidget(w.operation_notice)
    w.canvas = Canvas()
    w.canvas.preferences_changed.connect(w.persist_categories)
    w.canvas.changed.connect(w.commit); w.canvas.draft_changed.connect(w.schedule_live)
    w.canvas.selection_changed.connect(w.sync_selection); w.canvas.rename_requested.connect(w.rename_selected)
    w.canvas.category_requested.connect(w.add_category)
    w.canvas.interaction_started.connect(w.pause_slideshow)
    w.canvas.operation_failed.connect(w.show_operation_error)
    w.canvas.reshape_failed.connect(w.show_operation_error)
    w.canvas.message.connect(w.show_workflow_status); w.canvas.zoom_changed.connect(w.on_zoom)
    ml.addWidget(w.canvas, 1)
    bottom = QHBoxLayout(); bottom.setContentsMargins(12, 5, 12, 5)
    w.workflow_status = label("就绪"); w.workflow_status.setWordWrap(True)
    bottom.addWidget(w.workflow_status, 1)
    bottom.addStretch(); bottom.addWidget(tool("适应", w.canvas.fit)); bottom.addWidget(tool("1:1", w.canvas.original_size))
    w.zoom_label = label("100%"); bottom.addWidget(w.zoom_label); ml.addLayout(bottom)
    splitter.addWidget(middle)

    right = QWidget(); right.setMinimumWidth(265); right.setMaximumWidth(370)
    marks = QWidget(); mr = QVBoxLayout(marks); mr.setContentsMargins(14, 12, 14, 10); mr.setSpacing(8)
    mr.addWidget(label("类别", True))
    category_row = QHBoxLayout(); category_row.setSpacing(5)
    w.label_input = QComboBox(); w.label_input.setEditable(True); w.label_input.setMinimumWidth(130)
    w.label_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    w.label_input.lineEdit().setPlaceholderText("输入或添加类别")
    w.label_input.currentTextChanged.connect(lambda s: setattr(w.canvas, "label", s.strip()))
    w.label_input.lineEdit().editingFinished.connect(w.register_typed_category)
    category_row.addWidget(w.label_input, 1)
    w.add_category_button = tool("", w.add_category, "plus"); w.add_category_button.setToolTip("添加类别")
    category_row.addWidget(w.add_category_button); mr.addLayout(category_row)
    scope_row = QHBoxLayout()
    w.scope = combo([("完整区域", False), ("弱提示", True)]); w.scope.currentIndexChanged.connect(w.update_scope)
    w.role = combo([("前景", False), ("背景", True)]); w.role.currentIndexChanged.connect(w.update_scope)
    scope_row.addWidget(w.scope, 1); scope_row.addWidget(w.role); mr.addLayout(scope_row)

    lists = QSplitter(Qt.Orientation.Vertical)
    shape_panel = QWidget(); sh = QVBoxLayout(shape_panel); sh.setContentsMargins(0, 5, 0, 0); sh.setSpacing(2)
    shape_heading = QHBoxLayout(); shape_heading.addWidget(label("标记", True)); shape_heading.addStretch()
    shape_heading.addWidget(tool("", w.rename_selected, "edit")); shape_heading.itemAt(shape_heading.count()-1).widget().setToolTip("修改类别")
    shape_heading.addWidget(tool("", w.canvas.delete_selected, "delete")); shape_heading.itemAt(shape_heading.count()-1).widget().setToolTip("删除标记")
    sh.addLayout(shape_heading)
    w.shape_list = QListWidget(); w.shape_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    w.shape_list.itemSelectionChanged.connect(w.list_selection); w.shape_list.itemChanged.connect(w.visibility_changed)
    sh.addWidget(w.shape_list, 1)
    display = QHBoxLayout(); eye = tool("", w.toggle_annotations, "eye"); eye.setToolTip("显示 / 隐藏 T"); display.addWidget(eye)
    display.addWidget(label("填充")); w.opacity = QSlider(Qt.Orientation.Horizontal); w.opacity.setRange(0, 80); w.opacity.setValue(22)
    w.opacity.valueChanged.connect(w.set_opacity); display.addWidget(w.opacity, 1); sh.addLayout(display)
    lists.addWidget(shape_panel)
    files_panel = QWidget(); fl = QVBoxLayout(files_panel); fl.setContentsMargins(0, 6, 0, 0); fl.setSpacing(5)
    fh = QHBoxLayout(); fh.addWidget(label("图像", True)); fh.addStretch()
    w.progress_label = label("0 / 0"); fh.addWidget(w.progress_label); fl.addLayout(fh)
    w.project_label = label("尚未打开目录"); w.project_label.setWordWrap(True); fl.addWidget(w.project_label)
    w.search = QLineEdit(); w.search.setPlaceholderText("查找图像"); w.search.textChanged.connect(w.filter_files); fl.addWidget(w.search)
    w.file_list = QListWidget(); w.file_list.setUniformItemSizes(True); w.file_list.currentRowChanged.connect(w.switch_frame); fl.addWidget(w.file_list, 1)
    lists.addWidget(files_panel); lists.setSizes([280, 250]); mr.addWidget(lists, 1)
    mr.addWidget(separator()); mr.addWidget(label("标注文件", True))
    w.path_label = QLabel("尚无标注文件"); w.path_label.setObjectName("muted"); w.path_label.setWordWrap(True)
    w.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse); mr.addWidget(w.path_label)
    w.file_mtime_label = label("修改时间  —"); mr.addWidget(w.file_mtime_label)
    state_row = QHBoxLayout(); w.save_status = label("未修改"); w.save_status.setObjectName("saved"); state_row.addWidget(w.save_status)
    state_row.addStretch(); w.reload_button = tool("重新载入", w.reload_annotation); state_row.addWidget(w.reload_button); mr.addLayout(state_row)
    file_row = QHBoxLayout(); file_row.addWidget(tool("打开标注…", w.open_annotation, "json")); file_row.addStretch()
    file_row.addWidget(tool("保存位置…", w.choose_label_dir)); mr.addLayout(file_row)
    right_layout = QVBoxLayout(right); right_layout.setContentsMargins(0,0,0,0); right_layout.addWidget(marks)

    splitter.addWidget(right)
    splitter.setSizes([990, 320]); splitter.setStretchFactor(0, 1)
    w.tool_buttons["edit"].setChecked(True); w.setStyleSheet(STYLE)
    rail.setFixedWidth(max(116, max(b.sizeHint().width() for b in w.tool_buttons.values())+14))
    for b in w.tool_buttons.values():
        b.setMinimumHeight(max(38, b.sizeHint().height()))
    w.statusBar().showMessage("就绪")
