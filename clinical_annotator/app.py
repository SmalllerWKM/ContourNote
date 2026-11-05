from __future__ import annotations

import argparse
import base64
import copy
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSignalBlocker, QThreadPool, QTimer, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QInputDialog, QLineEdit, QListWidgetItem, QMainWindow,
    QMessageBox, QSpinBox, QTextEdit, QVBoxLayout,
)

from .data import (
    IMAGE_EXTENSIONS, Shape, atomic_json, export_dataset,
    load_document, validate_document,
)

TOOLS = [("edit", "选择 / 编辑", "E"), ("polygon", "轮廓", "A"),
         ("rectangle", "框", "B"), ("point", "点", "P"),
         ("line", "线", "L"), ("scribble", "涂鸦", "G"),
         ("circle", "圆", "C"), ("pan", "小手", "H")]


def combo(options):
    c = QComboBox()
    for label, value in options:
        c.addItem(label, value)
    return c


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("临绘 ContourNote · 人工标注工作台")
        self.resize(1480, 940)
        self._index_generation = 0
        self._index_job = None
        self.images = []
        self.current = -1
        self.label_dir = None
        self.label_overrides = {}
        self.history = []
        self.history_index = -1
        self.loading = False
        self.dirty = False
        self.last_error = ""
        self._saved_content = None
        self._saved_path = None
        self._disk_signature = None
        self._saved_draft = None
        self.external_change = False
        self._shortcuts = []
        self._slideshow_advancing = False
        self.slideshow_timer = QTimer(self)
        self.slideshow_timer.setInterval(1000)
        self.slideshow_timer.timeout.connect(self.slideshow_tick)
        self.draft_timer = QTimer(self)
        self.draft_timer.setSingleShot(True)
        self.draft_timer.setInterval(220)
        self.draft_timer.timeout.connect(self.auto_flush)
        self.build_ui()
        self.bind_shortcuts()
        self.file_timer = QTimer(self)
        self.file_timer.setInterval(600)
        self.file_timer.timeout.connect(self.refresh_file_state)
        self.file_timer.start()

    @property
    def doc(self):
        return self.canvas.doc

    def build_ui(self):
        from .ui import build_window
        build_window(self, TOOLS, combo)

    def toggle_maximized(self):
        self.showNormal() if self.isMaximized() or self.isFullScreen() else self.showMaximized()

    def toggle_fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def set_outline_width(self, value):
        self.canvas.stroke_width = float(value)
        self.canvas.update()
        if not self.loading:
            self.persist_categories()

    def update_slideshow_interval(self, value):
        self.slideshow_timer.setInterval(max(100, round(float(value)*1000)))
        if self.slideshow_timer.isActive():
            self.slideshow_status.setText(f"放映中 · {value:.1f} 秒/张")
        if not self.loading:
            self.persist_categories()

    def pause_slideshow(self):
        active = self.slideshow_timer.isActive()
        self.slideshow_timer.stop()
        if hasattr(self, "slideshow_button"):
            self.slideshow_button.setText("开始放映")
            if active:
                self.slideshow_status.setText("已暂停")

    def toggle_slideshow(self):
        if self.slideshow_timer.isActive():
            self.pause_slideshow()
            return
        if not self.images or self.current < 0:
            self.statusBar().showMessage("请先打开图像目录。", 5000)
            return
        self.refresh_file_state()
        if self.canvas.draft or self.dirty or self.last_error or self.external_change:
            self.statusBar().showMessage("请先完成当前路径并保存修改，再开始放映。", 6000)
            return
        self.slideshow_timer.start(round(self.slideshow_interval.value()*1000))
        self.slideshow_button.setText("暂停放映")
        self.slideshow_status.setText(f"放映中 · {self.slideshow_interval.value():.1f} 秒/张")

    def slideshow_tick(self):
        self.refresh_file_state()
        if not self.doc or self.canvas.draft or self.dirty or self.last_error or self.external_change:
            self.pause_slideshow()
            return
        visible = [i for i in range(len(self.images)) if not self.file_list.item(i).isHidden()]
        following = [i for i in visible if i > self.current]
        if not following and (not self.slideshow_loop.isChecked() or not visible):
            self.pause_slideshow()
            self.slideshow_status.setText("放映结束")
            return
        target = following[0] if following else visible[0]
        previous = self.current
        interval = self.slideshow_timer.interval()
        # A load-error or recovery dialog must never admit another timer tick.
        self.slideshow_timer.stop()
        self._slideshow_advancing = True
        try:
            self.file_list.setCurrentRow(target)
        finally:
            self._slideshow_advancing = False
        if (self.current == previous and target != previous) or self.canvas.draft or self.last_error:
            self.pause_slideshow()
            self.slideshow_status.setText("放映已暂停")
        else:
            self.slideshow_timer.start(interval)

    def category_settings_path(self):
        return self.images[0].parent / ".contour-note" / "categories.json" if self.images else None

    def register_category(self, name):
        name = name.strip()
        if name and self.label_input.findText(name) < 0:
            self.label_input.addItem(name)
        return name

    def persist_categories(self):
        path = self.category_settings_path()
        if path:
            try:
                atomic_json(path, {"categories": [self.label_input.itemText(i) for i in range(self.label_input.count())],
                                   "last_label": self.label_input.currentText().strip(),
                                   "stroke_width": self.canvas.stroke_width,
                                   "slideshow_interval": self.slideshow_interval.value(),
                                   "view_inset": self.view_inset.value(),
                                   "view_transition": self.view_transition.value(),
                                   "snap_view": self.canvas.snap_view_enabled})
            except OSError as exc:
                self.statusBar().showMessage(f"类别配置未能保存：{exc}", 6000)

    def register_typed_category(self):
        text = self.label_input.currentText().strip()
        if text:
            self.register_category(text)
            self.label_input.setCurrentText(text)
            self.persist_categories()

    def add_category(self):
        self.pause_slideshow()
        name, ok = QInputDialog.getText(self, "添加类别", "输入类别名称：")
        if ok and name.strip():
            self.register_category(name)
            self.label_input.setCurrentText(name.strip())
            self.persist_categories()
            self.canvas.setFocus()

    def load_categories(self):
        with QSignalBlocker(self.view_inset), QSignalBlocker(self.view_transition):
            self.view_inset.setValue(4)
            self.view_transition.setValue(35)
        self.canvas.view_inset=4
        self.canvas.view_transition=.35
        self.snap_view.setChecked(True)
        names = []
        last = ""
        path = self.category_settings_path()
        if path and path.exists():
            try:
                saved = json.loads(path.read_text(encoding="utf-8"))
                names.extend(n for n in saved.get("categories", []) if isinstance(n, str) and n.strip())
                last = saved.get("last_label", "")
                self.snap_view.setChecked(bool(saved.get("snap_view", True)))
                with QSignalBlocker(self.view_inset), QSignalBlocker(self.view_transition):
                    self.view_inset.setValue(int(saved.get("view_inset", 4)))
                    self.view_transition.setValue(int(saved.get("view_transition", 35)))
                self.canvas.view_inset = self.view_inset.value()
                self.canvas.view_transition = self.view_transition.value()/100
                width = saved.get("stroke_width", 1.7)
                if isinstance(width, (int, float)) and math.isfinite(width):
                    with QSignalBlocker(self.outline_width):
                        self.outline_width.setValue(width)
                    self.canvas.stroke_width = self.outline_width.value()
                interval = saved.get("slideshow_interval", 1.0)
                if isinstance(interval, (int, float)) and math.isfinite(interval):
                    with QSignalBlocker(self.slideshow_interval):
                        self.slideshow_interval.setValue(interval)
                    self.slideshow_timer.setInterval(round(self.slideshow_interval.value()*1000))
            except (ValueError, OSError):
                pass
        for image in self.images if len(self.images) <= 100 else []:
            target = self.label_path(image)
            if target.exists():
                try:
                    raw = json.loads(target.read_text(encoding="utf-8"))
                    names.extend(s["label"] for s in raw.get("shapes", []) if isinstance(s.get("label"), str) and s["label"].strip())
                except (ValueError, OSError, TypeError):
                    continue
        with QSignalBlocker(self.label_input):
            self.label_input.clear()
            for name in names:
                self.register_category(name)
            if last in names:
                self.label_input.setCurrentText(last)
        self.canvas.label = self.label_input.currentText().strip()

    def content(self):
        return json.dumps(self.doc.to_dict(self.label_path()), ensure_ascii=False, sort_keys=True) if self.doc else None

    @staticmethod
    def file_signature(path):
        try:
            stat = path.stat()
            return stat.st_mtime_ns, stat.st_size, stat.st_ino
        except FileNotFoundError:
            return None

    def remember_disk_state(self):
        self._saved_path = self.label_path()
        self._saved_content = self.content()
        self._disk_signature = self.file_signature(self._saved_path)
        self.external_change = False
        self.dirty = False
        self._saved_draft = None
        self.refresh_file_state()

    def refresh_file_state(self):
        if not self.doc:
            self.file_mtime_label.setText("修改时间  —")
            return
        path = self.label_path()
        signature = self.file_signature(path)
        self.path_label.setText(path.name)
        self.path_label.setToolTip(str(path))
        if signature:
            stamp = datetime.fromtimestamp(signature[0] / 1_000_000_000)
            self.file_mtime_label.setText("修改时间  " + stamp.strftime("%Y-%m-%d %H:%M:%S.") + f"{signature[0]//1_000_000%1000:03d}")
            self.file_mtime_label.setToolTip(stamp.isoformat(timespec="milliseconds") + "\n来自文件系统的实际修改时间")
        else:
            self.file_mtime_label.setText("修改时间  尚未保存")
        if path == self._saved_path and signature != self._disk_signature:
            self.external_change = True
        modified = self.content() != self._saved_content
        self.dirty = modified
        if self.last_error:
            self.save_status.setText("保存失败")
            self.save_status.setStyleSheet("color: #bd4a3e;")
        elif self.external_change:
            self.save_status.setText("文件已在外部更改")
            self.save_status.setStyleSheet("color: #a46c20;")
        elif modified:
            self.save_status.setText("未保存的修改")
            self.save_status.setStyleSheet("color: #a46c20;")
        elif self.canvas.draft:
            self.save_status.setText("绘制草稿已保存" if self.autosave.isChecked() and self._saved_draft else "绘制中 · 未完成")
            self.save_status.setStyleSheet("color: #7c838e;")
        else:
            self.save_status.setText("已保存 · 无新修改" if signature else "尚未保存")
            self.save_status.setStyleSheet("color: #657061;")

    def autosave_toggled(self, checked):
        self.draft_timer.stop()
        if checked:
            self.auto_flush()
        else:
            self.refresh_file_state()

    def auto_flush(self):
        if not self.doc or self.loading:
            return True
        self.refresh_file_state()
        if not self.autosave.isChecked() or self.external_change:
            return False
        if not self.dirty and not self.canvas.draft and not self._saved_draft:
            return True
        return self.save_live()

    def bind_shortcuts(self):
        shortcuts = [(key, lambda t=kind: self.set_tool(t)) for kind, _, key in TOOLS]
        shortcuts += [("Ctrl+N", lambda: self.set_tool("polygon")), ("Ctrl+R", lambda: self.set_tool("rectangle")),
                      ("Ctrl+J", lambda: self.set_tool("edit")), ("Ctrl+Z", self.undo),
                      ("Ctrl+Y", self.redo), ("Ctrl+Shift+Z", self.redo), ("Ctrl+S", self.save_live),
                      ("Ctrl+O", self.open_file), ("Ctrl+U", self.open_folder),
                      ("Delete", self.canvas.delete_selected), ("Backspace", self.canvas.delete_selected),
                      ("F", self.canvas.fit), ("Ctrl+F", self.canvas.fit),
                      ("1", self.canvas.original_size), ("Ctrl+0", self.canvas.original_size),
                      ("T", self.toggle_annotations), ("Ctrl+E", self.rename_selected),
                      ("Ctrl+D", self.duplicate_selected),
                      ("Ctrl+C", self.copy_selected), ("Ctrl+V", self.paste_selected),
                      ("Ctrl++", lambda: self.canvas.set_zoom(self.canvas.scale*1.15)),
                      ("Ctrl+=", lambda: self.canvas.set_zoom(self.canvas.scale*1.15)),
                      ("Ctrl+-", lambda: self.canvas.set_zoom(self.canvas.scale/1.15)),
                      ("F1", self.show_help)]
        shortcuts += [("Tab", self.toggle_edit_polygon), ("F5", self.toggle_slideshow), ("F11", self.toggle_fullscreen)]
        shortcuts += [(key, lambda: self.navigate(-1)) for key in ["Left", "Up", "W"]]
        shortcuts += [(key, lambda: self.navigate(1)) for key in ["Right", "Down", "D"]]
        for key, callback in shortcuts:
            short = QShortcut(QKeySequence(key), self.canvas if key == "Tab" else self)
            if key == "Tab":
                short.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            short.activated.connect(lambda fn=callback: self.shortcut_action(fn))
            self._shortcuts.append(short)

    def shortcut_action(self, callback):
        # Annotation keys must not steal characters or editing commands from fields.
        focus = QApplication.focusWidget()
        if isinstance(focus, (QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox)) and callback not in {
                self.save_live, self.open_file, self.open_folder, self.open_annotation, self.show_help,
                self.toggle_slideshow, self.toggle_fullscreen}:
            return
        callback()

    def set_tool(self, kind):
        self.pause_slideshow()
        if self.canvas.draft and not self.resolve_draft():
            return
        self.canvas.change_tool(kind)
        for name, b in self.tool_buttons.items():
            b.setChecked(name == kind)
        if kind in {"point", "rectangle", "line", "scribble"}:
            self.scope.setCurrentIndex(1)
        elif kind in {"polygon", "circle"}:
            self.scope.setCurrentIndex(0)
            self.role.setCurrentIndex(0)
        self.canvas.operation = "new"
        self.update_scope()
        self.statusBar().showMessage("编辑：单击边界拖动节点，双击边界重画；Tab 切换编辑/多边形；右键或 Enter 完成。", 9000)

    def update_view_boundary(self):
        self.canvas.view_inset = self.view_inset.value()
        self.canvas.view_transition = self.view_transition.value()/100
        if self.doc:
            from .view_boundary import detect_view_boundary
            self.canvas.view_boundary = detect_view_boundary(self.doc.image, self.canvas.view_inset, self.canvas.view_transition)
            self.canvas.update()
        if not self.loading:
            self.persist_categories()

    def toggle_edit_polygon(self):
        self.set_tool("polygon" if self.canvas.tool == "edit" else "edit")

    def show_operation_error(self, text):
        self.operation_hint.setText(text + " 当前路径已保留，可 Ctrl+Z 撤回点后调整，或 Esc 取消。")
        self.operation_notice.show()

    def dismiss_notice(self):
        self.operation_notice.hide()
        self.operation_hint.clear()
        self.canvas.setFocus()

    def update_scope(self):
        weak = bool(self.scope.currentData())
        if self.canvas.tool in {"point", "line", "scribble"}:
            weak = True
            if self.scope.currentIndex() != 1:
                self.scope.setCurrentIndex(1)
        self.canvas.weak = weak
        self.role.setEnabled(weak)
        self.canvas.background = weak and bool(self.role.currentData())

    def on_zoom(self, scale):
        self.zoom_label.setText(f"{scale*100:.0f}%")

    def set_opacity(self, value):
        self.canvas.opacity = value/100
        self.canvas.update()

    def toggle_annotations(self):
        self.canvas.show_annotations = not self.canvas.show_annotations
        self.canvas.update()

    def label_path(self, image=None):
        image = image or self.doc.image
        if image in self.label_overrides:
            return self.label_overrides[image]
        return (self.label_dir / f"{image.stem}.json") if self.label_dir else image.with_suffix(".json")

    def draft_path(self):
        target = self.label_path()
        return target.parent / ".contour-drafts" / target.name

    def schedule_live(self):
        if not self.canvas.draft:
            self.operation_notice.hide()
        if not self.loading and self.doc:
            if self.autosave.isChecked() and not self.draft_timer.isActive():
                self.draft_timer.start()
            self.save_status.setText("绘制中 · 待保存" if self.canvas.draft else "修改中 · 待保存")
            if self.canvas.drag_start is not None:
                self.dirty = True

    def save_live(self):
        self.draft_timer.stop()
        if not self.doc or self.loading:
            return True
        target = self.label_path()
        self.refresh_file_state()
        if self.external_change:
            choice = QMessageBox.question(self, "标注文件已在外部更改", "文件被其他程序修改。是否用当前画布内容覆盖？选择否后可点击“重新载入”读取外部修改。旧文件将备份。")
            if choice != QMessageBox.StandardButton.Yes:
                self.last_error = "文件存在外部修改，请先重新载入或确认覆盖。"
                self.refresh_file_state()
                return False
        content = self.content()
        try:
            if content != self._saved_content or target != self._saved_path or not target.exists() or self.external_change:
                atomic_json(target, self.doc.to_dict(target), backup=target.exists())
                self._saved_content = content
                self._saved_path = target
                self._disk_signature = self.file_signature(target)
                self.external_change = False
            if self.canvas.draft:
                value = {"tool": self.canvas.tool, "points": self.canvas.draft,
                         "label": self.canvas.label, "weak": self.canvas.weak, "background": self.canvas.background,
                         "operation": "new", "selected": sorted(self.canvas.selected),
                         "reshape_start": self.canvas.reshape_start_point,
                         "reshape": self.canvas.reshape}
                draft_content = json.dumps(value, sort_keys=True)
                if draft_content != self._saved_draft:
                    atomic_json(self.draft_path(), value)
                    self._saved_draft = draft_content
            else:
                if self.draft_path().exists():
                    self.draft_path().unlink()
                self._saved_draft = None
        except Exception as exc:
            self.last_error = str(exc)
            self.refresh_file_state()
            self.statusBar().showMessage(f"保存失败：{target} — {exc}")
            return False
        self.dirty = False
        self.last_error = ""
        self.refresh_file_state()
        self.update_file_status()
        return True

    def commit(self):
        if self.loading or not self.doc:
            return
        self.dismiss_notice()
        snapshot = self.doc.snapshot()
        if not self.history or snapshot != self.history[self.history_index]:
            self.history = self.history[:self.history_index+1] + [snapshot]
            self.history = self.history[-80:]
            self.history_index = len(self.history)-1
        self.dirty = True
        for shape in self.doc.shapes:
            self.register_category(shape.label)
        self.rebuild_shapes()
        self.update_file_status()
        self.canvas.update()
        self.auto_flush()

    def undo(self):
        closed = self.canvas.auto_closed
        if closed and self.canvas.tool == "polygon" and not self.canvas.draft and self.doc.snapshot() == closed[2]:
            self.canvas.auto_closed = None
            if self.history_index > 0:
                self.history_index -= 1
            self.restore_history()
            self.canvas.draft = copy.deepcopy(closed[1])
            self.canvas.selected = set(closed[3])
            self.sync_selection()
            self.canvas.wait_for_shift_release = False
            self.canvas.draft_changed.emit()
            self.canvas.update()
            self.auto_flush()
            return
        self.canvas.auto_closed = None
        if self.canvas.draft:
            self.canvas.draft.pop()
            if not self.canvas.draft:
                self.canvas.reshape = None
            self.canvas.update()
            self.auto_flush()
            return
        if self.doc and self.history_index > 0:
            self.history_index -= 1
            self.restore_history()

    def redo(self):
        if self.doc and self.history_index < len(self.history)-1:
            self.history_index += 1
            self.restore_history()

    def restore_history(self):
        self.doc.restore(self.history[self.history_index])
        self.canvas.selected.clear()
        self.canvas.hidden.clear()
        self.rebuild_shapes()
        self.canvas.update()
        self.dirty = True
        self.auto_flush()

    def rebuild_shapes(self):
        with QSignalBlocker(self.shape_list):
            self.shape_list.clear()
            if self.doc:
                for i, s in enumerate(self.doc.shapes):
                    mode = "背景提示" if s.background else "弱提示" if s.weak else "完整"
                    kind = {"polygon": "轮廓", "rectangle": "框", "point": "点", "line": "线", "linestrip": "折线", "circle": "圆"}.get(s.shape_type, s.shape_type)
                    item = QListWidgetItem(f"{s.label}   ·   {kind}")
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Unchecked if i in self.canvas.hidden else Qt.CheckState.Checked)
                    item.setToolTip(f"{mode} · {kind} · {len(s.points)} 个节点")
                    self.shape_list.addItem(item)
                    item.setSelected(i in self.canvas.selected)

    def sync_selection(self):
        with QSignalBlocker(self.shape_list):
            for i in range(self.shape_list.count()):
                self.shape_list.item(i).setSelected(i in self.canvas.selected)
        self.canvas.update()

    def list_selection(self):
        self.canvas.selected = {self.shape_list.row(i) for i in self.shape_list.selectedItems()}
        self.canvas.update()

    def visibility_changed(self, item):
        i = self.shape_list.row(item)
        if item.checkState() == Qt.CheckState.Unchecked:
            self.canvas.hidden.add(i)
        else:
            self.canvas.hidden.discard(i)
        self.canvas.update()

    def rename_selected(self):
        self.pause_slideshow()
        if not self.doc or not self.canvas.selected:
            return
        value, ok = QInputDialog.getText(self, "修改类别", "类别名称", text=self.doc.shapes[min(self.canvas.selected)].label)
        if ok and value.strip():
            for i in self.canvas.selected:
                self.doc.shapes[i].label = value.strip()
            if self.label_input.findText(value.strip()) < 0:
                self.label_input.addItem(value.strip())
            self.label_input.setCurrentText(value.strip())
            self.commit()

    def duplicate_selected(self):
        if not self.doc:
            return
        copies = []
        for i in sorted(self.canvas.selected):
            s = copy.deepcopy(self.doc.shapes[i])
            s.extra.pop("contour_note_id", None)
            s.group_id = None
            copies.append(s)
        self.doc.shapes.extend(copies)
        self.canvas.selected = set(range(len(self.doc.shapes)-len(copies), len(self.doc.shapes)))
        if copies:
            self.commit()

    def copy_selected(self):
        if self.doc and self.canvas.selected:
            value = {"contour_note_clipboard": True, "width": self.doc.width, "height": self.doc.height,
                     "shapes": [self.doc.shapes[i].to_dict() for i in sorted(self.canvas.selected)]}
            QApplication.clipboard().setText(json.dumps(value, ensure_ascii=False))
            self.statusBar().showMessage("已复制标记，可在相同尺寸图像中粘贴。", 4000)

    def paste_selected(self):
        if not self.doc:
            return
        try:
            value = json.loads(QApplication.clipboard().text())
            if not value.get("contour_note_clipboard"):
                return
            if (value["width"], value["height"]) != (self.doc.width, self.doc.height):
                raise ValueError("来源和当前图像尺寸不同，不能直接粘贴坐标。")
            shapes = [Shape.from_dict(s) for s in value["shapes"]]
            for shape in shapes:
                shape.extra.pop("contour_note_id", None)
                shape.group_id = None
            self.doc.shapes.extend(shapes)
            self.canvas.selected = set(range(len(self.doc.shapes)-len(shapes), len(self.doc.shapes)))
            self.commit()
        except Exception as exc:
            self.statusBar().showMessage(f"粘贴失败：{exc}", 6000)

    def resolve_draft(self):
        if not self.canvas.draft:
            return True
        choice = QMessageBox.question(self, "尚有未完成路径", "当前路径尚未完成。选择“是”完成，“否”放弃，或取消切换。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        if choice == QMessageBox.StandardButton.Cancel:
            return False
        if choice == QMessageBox.StandardButton.Yes:
            self.canvas.finish()
            return not self.canvas.draft
        self.canvas.cancel_draft()
        if self.draft_path().exists():
            self.draft_path().unlink()
        self._saved_draft = None
        if self.autosave.isChecked():
            return self.auto_flush()
        return True

    def can_leave(self):
        if not self.resolve_draft():
            return False
        self.refresh_file_state()
        if not self.autosave.isChecked() and self.dirty:
            choice = QMessageBox.question(self, "有未保存的修改", "自动保存已关闭。是否保存当前标注？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if choice == QMessageBox.StandardButton.Cancel:
                return False
            if choice == QMessageBox.StandardButton.No:
                if self.draft_path().exists():
                    self.draft_path().unlink()
                return True
        elif not self.autosave.isChecked():
            return True
        if self.external_change and not self.dirty:
            return True
        if not self.dirty and not self.last_error:
            return True
        if not self.save_live():
            QMessageBox.critical(self, "保存失败，未切换图像", self.last_error)
            return False
        return True

    def open_folder(self):
        self.pause_slideshow()
        folder = QFileDialog.getExistingDirectory(self, "打开图像项目")
        if folder:
            self.open_path(Path(folder))

    def open_file(self):
        self.pause_slideshow()
        name, _ = QFileDialog.getOpenFileName(self, "打开图像", "", "图像 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)")
        if name:
            self.open_path(Path(name))

    def open_annotation(self):
        self.pause_slideshow()
        name, _ = QFileDialog.getOpenFileName(self, "打开 Labelme 标注文件", str(self.doc.image.parent) if self.doc else "", "Labelme 标注 (*.json)")
        if name:
            self.open_path(Path(name))

    def reload_annotation(self):
        if not self.doc or not self.label_path().exists():
            return
        self.refresh_file_state()
        if self.dirty or self.canvas.draft:
            if QMessageBox.question(self, "重新载入标注", "重新载入将放弃当前未保存的修改和绘制草稿，是否继续？") != QMessageBox.StandardButton.Yes:
                return
        try:
            doc = load_document(self.doc.image, self.label_path())
            scale, offset = self.canvas.scale, self.canvas.offset
            self.loading = True
            self.canvas.set_document(doc)
            self.canvas.scale, self.canvas.offset = scale, offset
            self.loading = False
            self.history, self.history_index = [doc.snapshot()], 0
            self.last_error = ""
            for shape in doc.shapes:
                self.register_category(shape.label)
            self.rebuild_shapes()
            self.remember_disk_state()
            self.update_file_status()
        except Exception as exc:
            self.loading = False
            QMessageBox.critical(self, "重新载入失败", str(exc))

    def open_path(self, path):
        path = path.resolve()
        try:
            if path.is_dir():
                return self.load_images(sorted(p for p in path.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS))
            if path.suffix.lower() == ".json":
                data = json.loads(path.read_text(encoding="utf-8"))
                raw_path = str(data.get("imagePath", "")).replace("\\", "/")
                image = (path.parent / raw_path).resolve()
                if not image.is_file():
                    image = (path.parent / Path(raw_path).name).resolve()
                if not image.is_file() and data.get("imageData"):
                    image = path.parent / ".contour-images" / f"{path.stem}.png"
                    image.parent.mkdir(exist_ok=True)
                    image.write_bytes(base64.b64decode(data["imageData"]))
                if not image.is_file():
                    raise ValueError("JSON 引用的图片不存在，请恢复 imagePath 指向的图片。")
                load_document(image, path)
                if self.doc and not self.can_leave():
                    return False
                previous_override = self.label_overrides.get(image)
                self.label_overrides[image] = path
                success = self.load_images([image], leave_checked=True)
                if not success:
                    if previous_override is None:
                        self.label_overrides.pop(image, None)
                    else:
                        self.label_overrides[image] = previous_override
                return success
            return self.load_images([path])
        except Exception as exc:
            QMessageBox.critical(self, "打开失败", str(exc))
            return False

    def load_images(self, images, leave_checked=False):
        self.pause_slideshow()
        if not images:
            QMessageBox.information(self, "没有图片", "目录中未找到支持的图像。")
            return False
        targets = [self.label_path(image) for image in images]
        if len(set(targets)) != len(targets):
            QMessageBox.warning(self, "同名标签冲突", "图片存在相同文件名主体（例如 case.jpg 和 case.png），会对应同一个 JSON。请分开放入不同文件夹。")
            return False
        if self.doc and not leave_checked and not self.can_leave():
            return False
        # Preflight before replacing the current working document.
        try:
            load_document(images[0], self.label_path(images[0]))
        except Exception as exc:
            QMessageBox.critical(self, "无法加载首张图片", str(exc))
            return False
        self.images = images
        self.current = -1
        self.loading = True
        self.load_categories()
        with QSignalBlocker(self.file_list):
            self.file_list.clear()
            self.file_list.addItems([image.name for image in images])
        self.loading = False
        self.refresh_all_file_status()
        self.project_label.setText(images[0].parent.name)
        self.project_label.setToolTip(str(images[0].parent))
        self.search.clear()
        self.file_list.setCurrentRow(0)
        return self.current == 0

    def switch_frame(self, index):
        if self.loading or index < 0 or index >= len(self.images) or index == self.current:
            return
        if not self._slideshow_advancing:
            self.pause_slideshow()
        if self.doc and self.current >= 0 and not self.can_leave():
            with QSignalBlocker(self.file_list):
                self.file_list.setCurrentRow(self.current)
            return
        try:
            doc = load_document(self.images[index], self.label_path(self.images[index]))
            self.loading = True
            self.canvas.set_document(doc)
        except Exception as exc:
            self.loading = False
            QMessageBox.critical(self, "加载失败，原文件未修改", str(exc))
            with QSignalBlocker(self.file_list):
                self.file_list.setCurrentRow(self.current)
            return
        self.current = index
        self.history = [doc.snapshot()]
        self.history_index = 0
        self.dirty = False
        self.loading = False
        self.last_error = ""
        for shape in doc.shapes:
            if self.label_input.findText(shape.label) < 0:
                self.label_input.addItem(shape.label)
        self.rebuild_shapes()
        self.image_info.setText(f"{doc.image.name}  ·  {doc.width} × {doc.height}")
        self.image_info.setToolTip(self.image_info.text())
        self.remember_disk_state()
        self.progress_label.setText(f"{index+1} / {len(self.images)} 张")
        draft = self.draft_path()
        if draft.exists():
            try:
                value = json.loads(draft.read_text(encoding="utf-8"))
                if value.get("operation", "new") != "new":
                    raise ValueError("发现旧版补画/扣除草稿，已保留原草稿文件；请在旧版完成后再打开，避免被当作新区域保存。")
                if value.get("tool") not in {"polygon", "rectangle", "circle", "point", "line", "linestrip", "scribble", "edit"}:
                    raise ValueError("草稿工具类型无效")
                if not isinstance(value.get("points"), list) or not value["points"] or not all(
                    isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in p)
                    and 0 <= p[0] < doc.width and 0 <= p[1] < doc.height for p in value["points"]):
                    raise ValueError("草稿坐标无效")
                if value.get("tool") == "edit":
                    reshape = value.get("reshape")
                    if not (isinstance(reshape, list) and len(reshape) == 2 and
                            all(isinstance(v, int) for v in reshape) and
                            0 <= reshape[0] < len(doc.shapes) and
                            0 <= reshape[1] < len(doc.shapes[reshape[0]].points)):
                        raise ValueError("切分草稿缺少有效的原轮廓")
                if QMessageBox.question(self, "恢复未完成路径", "发现上次未完成的绘制草稿，是否恢复？") == QMessageBox.StandardButton.Yes:
                    self.set_tool(value["tool"])
                    self.canvas.draft = value["points"]
                    self.canvas.label = value.get("label", self.canvas.label)
                    self.label_input.setCurrentText(self.canvas.label)
                    self.scope.setCurrentIndex(1 if value.get("weak") else 0)
                    self.role.setCurrentIndex(1 if value.get("background") else 0)
                    self.canvas.operation = "new"
                    self.canvas.selected = {i for i in value.get("selected", []) if isinstance(i, int) and 0 <= i < len(doc.shapes)}
                    reshape = value.get("reshape")
                    if reshape and len(reshape) == 2 and 0 <= reshape[0] < len(doc.shapes) and 0 <= reshape[1] < len(doc.shapes[reshape[0]].points):
                        self.canvas.reshape = tuple(reshape)
                        point = value.get("reshape_start")
                        if isinstance(point, list) and len(point)==2 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in point):
                            self.canvas.reshape_start_point = point
                    self.sync_selection()
                    self.canvas.update()
                else:
                    draft.unlink()
            except Exception as exc:
                QMessageBox.warning(self, "草稿恢复失败", str(exc))
        self.update_file_status()
        self.refresh_file_state()
        self.canvas.setFocus()

    def navigate(self, step):
        if not self._slideshow_advancing:
            self.pause_slideshow()
        index = self.current+step
        while 0 <= index < len(self.images) and self.file_list.item(index).isHidden():
            index += step
        if 0 <= index < len(self.images):
            self.file_list.setCurrentRow(index)

    @staticmethod
    def payload_is_annotated(payload):
        return bool(payload.get("shapes") or payload.get("flags"))

    def update_file_status(self, index=None):
        index = self.current if index is None else index
        if not 0 <= index < self.file_list.count():
            return
        image = self.images[index]
        try:
            if self.doc and index == self.current and image == self.doc.image:
                data = self.doc.to_dict()
            else:
                path = self.label_path(image)
                data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            completed = self.payload_is_annotated(data)
            item = self.file_list.item(index)
            item.setText(("✓  " if completed else "") + image.name)
            item.setToolTip(f"{'已标注' if completed else '未标注'} · {len(data.get('shapes', []))} 个标记\n{image}")
        except (OSError, ValueError, TypeError):
            self.file_list.item(index).setText(image.name)
            self.file_list.item(index).setToolTip("标注文件无法读取，请检查 JSON。")

    def refresh_all_file_status(self):
        self._index_generation += 1
        if self._index_job:
            self._index_job.cancelled.set()
        if len(self.images) <= 100:
            for index in range(self.file_list.count()):
                self.update_file_status(index)
            return
        from .indexing import AnnotationIndex
        self._index_job = AnnotationIndex(self._index_generation,
            [self.label_path(image) for image in self.images], self.payload_is_annotated)
        self._index_job.signals.batch.connect(self.apply_index_batch)
        QThreadPool.globalInstance().start(self._index_job)
        self.statusBar().showMessage(f"后台读取标注状态与类别：0 / {len(self.images)}，可立即标注")

    def apply_index_batch(self, generation, results, done):
        if generation != self._index_generation:
            return
        for index, completed, count, names, error in results:
            if index != self.current:
                item = self.file_list.item(index)
                item.setText(("✓  " if completed else "") + self.images[index].name)
                item.setToolTip("标注文件无法读取，请检查 JSON。" if error else
                                f"{'已标注' if completed else '未标注'} · {count} 个标记\n{self.images[index]}")
            for name in names:
                self.register_category(name)
        self.statusBar().showMessage(f"标注索引：{done} / {len(self.images)}")

    def filter_files(self, text):
        for i, image in enumerate(self.images):
            self.file_list.item(i).setHidden(text.lower() not in image.name.lower())

    def choose_label_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "选择 JSON 保存目录")
        if not folder:
            return
        chosen = Path(folder)
        if len({p.stem for p in self.images}) != len(self.images):
            QMessageBox.warning(self, "文件名冲突", "存在同名图片，请分别打开后保存，避免标签相互覆盖。")
            return
        completed = 0
        try:
            documents = [self.doc if self.doc and p == self.doc.image else load_document(p, self.label_path(p)) for p in self.images]
            conflicts = [d for d in documents if (chosen / f"{d.image.stem}.json").exists()
                         and chosen / f"{d.image.stem}.json" != self.label_path(d.image)]
            if conflicts and QMessageBox.question(self, "目标已有标注", f"目标目录有 {len(conflicts)} 个同名 JSON，是否用当前项目内容替换？原文件会备份。") != QMessageBox.StandardButton.Yes:
                return
            for doc in documents:
                path = chosen / f"{doc.image.stem}.json"
                atomic_json(path, doc.to_dict(path), backup=True)
                completed += 1
            self.label_dir = chosen
            self.label_overrides.clear()
            self.dirty = True
            self.save_live()
        except Exception as exc:
            QMessageBox.critical(self, "切换保存目录失败", f"已复制 {completed} 个 JSON；当前保存路径保持原设置。\n{exc}")

    def copy_previous(self):
        self.pause_slideshow()
        if self.current <= 0:
            return
        if not self.can_leave():
            return
        try:
            previous = load_document(self.images[self.current-1], self.label_path(self.images[self.current-1]))
            self.copy_into(previous, self.doc, bool(self.weak_copy.isChecked()))
            self.commit()
        except Exception as exc:
            QMessageBox.warning(self, "复制失败", str(exc))

    def copy_into(self, source, target, weak_only):
        if (source.width, source.height) != (target.width, target.height):
            raise ValueError("图片尺寸不同，停止复制；请先确认坐标对应关系。")
        selected = [s for s in source.shapes if not weak_only or s.weak]
        if not selected:
            raise ValueError("来源帧没有可复制的标注。")
        if QMessageBox.question(self, "复用相邻帧标签", "将替换目标帧相同范围的标注。仅复制坐标，不会自动跟踪，请逐帧复核。是否继续？") != QMessageBox.StandardButton.Yes:
            raise ValueError("已取消复制")
        target.shapes = ([s for s in target.shapes if not s.weak] if weak_only else []) + copy.deepcopy(selected)

    def propagate(self):
        self.pause_slideshow()
        if not self.doc or self.current >= len(self.images)-1 or not self.can_leave():
            return
        count, ok = QInputDialog.getInt(self, "传播标签", "复制到后续多少帧？", 1, 1, len(self.images)-self.current-1)
        if not ok:
            return
        weak = self.weak_copy.isChecked()
        selected = [s for s in self.doc.shapes if not weak or s.weak]
        if not selected:
            QMessageBox.information(self, "没有可传播标记", "请先创建相应标记。")
            return
        if QMessageBox.question(self, "确认传播", f"将替换后 {count} 帧的{'弱标注（保留完整轮廓）' if weak else '全部标记'}，原 JSON 会备份。仅复制坐标，请逐帧复核。") != QMessageBox.StandardButton.Yes:
            return
        completed = 0
        try:
            targets = [load_document(p, self.label_path(p)) for p in self.images[self.current+1:self.current+count+1]]
            if any((d.width, d.height) != (self.doc.width, self.doc.height) for d in targets):
                raise ValueError("后续图片尺寸不一致，未写入任何传播标签。")
            for target in targets:
                target.shapes = ([s for s in target.shapes if not s.weak] if weak else []) + copy.deepcopy(selected)
                path = self.label_path(target.image)
                atomic_json(path, target.to_dict(path), backup=True)
                completed += 1
            self.refresh_all_file_status()
            QMessageBox.information(self, "传播完成", f"已复制到 {completed} 帧，请逐帧人工复核。")
        except Exception as exc:
            QMessageBox.warning(self, "传播停止", f"已写入 {completed} 帧；{exc}")

    def export_project(self):
        self.pause_slideshow()
        if not self.images or not self.can_leave():
            return
        folder = QFileDialog.getExistingDirectory(self, "选择导出根目录（将新建独立子目录）")
        if not folder:
            return
        destination = Path(folder) / time.strftime("ContourNote_export_%Y%m%d_%H%M%S")
        if destination.exists():
            destination = destination.with_name(destination.name + f"_{time.time_ns()%100000}")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            docs = [copy.deepcopy(self.doc) if self.doc and p == self.doc.image and not self.external_change
                    else load_document(p, self.label_path(p)) for p in self.images]
            result = export_dataset(docs, destination)
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "导出完成", f"{destination}\n\n{len(docs)} 张图片，{len(result['annotations'])} 个 COCO 区域/框。\n包含 Labelme JSON、COCO、语义 Mask、弱提示 Mask 和类别映射。\n点/线仅进入弱标注文件，弱框的 COCO segmentation 为空。")

    def show_help(self):
        QMessageBox.information(self, "快捷键与操作", "A 轮廓 · E 编辑 · B 框 · P 点 · L 线 · G 涂鸦 · C 圆 · H 小手\n"
            "Shift＋鼠标左键拖动：轮廓/线连续采点；松开左键停止，右键或 Enter 完成\n"
            "轮廓接近起点自动闭合；绘制设置中可调整闭合距离或关闭\n"
            "编辑时 Shift＋点击边线：增加节点；右键节点：删除节点\n"
            "选择编辑：单击边界拖动节点；双击节点/边线开始重画，接回原边界完成\n"
            "空格＋左键 / 中键 / Alt＋左键：平移；滚轮：缩放\n"
            "W / ← / ↑ 上一帧；D / → / ↓ 下一帧\n"
            "F / Ctrl+F 适应窗口；1 / Ctrl+0 原始大小；T 显隐\n"
            "Tab 切换选择编辑 / 多边形；右键或 Enter 完成\n"
            "Ctrl+Z 撤销（绘制时撤一个点）；Ctrl+Y 重做\n"
            "Ctrl+S 保存；Ctrl+E 改类别；Ctrl+D 复制选区；Ctrl+C/V 复制粘贴；Delete 删除\n"
            "Ctrl+N 轮廓；Ctrl+R 框；Ctrl+J 编辑；Ctrl+O 打开；Ctrl+U 文件夹\n"
            "Esc 取消草稿；多选使用 Ctrl＋点击或标记列表\n"
            "顶部可开关自动保存；侧栏显示磁盘文件真实修改时间\n"
            "F5 放映/暂停，图片放映菜单设置速度；F11 全屏\n"
            "macOS 的 Ctrl 组合使用 Command；为保留医生习惯，A 用于轮廓，上一帧使用 W。\n"
            "填充透明度和显隐仅影响显示，导出仍包含标记。")

    def closeEvent(self, event):
        self.pause_slideshow()
        if self.can_leave():
            self._index_generation += 1
            if self._index_job:
                self._index_job.cancelled.set()
            event.accept()
        else:
            event.ignore()


def main():
    parser = argparse.ArgumentParser(description="临绘 ContourNote — 纯人工医学图像标注")
    parser.add_argument("path", nargs="?", help="图像文件夹、图片或 Labelme JSON")
    parser.add_argument("--self-test", metavar="OUTPUT", help=argparse.SUPPRESS)
    args = parser.parse_args()
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("ContourNote")
    app.setOrganizationName("ContourNote")
    window = MainWindow()
    window.showMaximized()
    if args.self_test:
        from .runtime_check import run_check
        QTimer.singleShot(500, lambda: run_check(app, window, Path(args.self_test)))
    elif args.path:
        QTimer.singleShot(0, lambda: window.open_path(Path(args.path)))
    sys.exit(app.exec())
