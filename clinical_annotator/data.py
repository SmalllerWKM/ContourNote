"""Labelme-compatible documents, loss-aware exports, and atomic persistence."""
from __future__ import annotations

import base64
import copy
import io
import json
import math
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, box
from shapely.ops import triangulate, unary_union

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
SHAPES = {"polygon", "rectangle", "circle", "point", "line", "linestrip"}
PALETTE = ["#34d3b0", "#ffbd69", "#85a9ff", "#f58ab0", "#b39bfa", "#79cee3"]


def atomic_json(path: Path, value: dict, backup: bool = False):
    """Same-filesystem replace: readers see either the previous or new file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if backup and path.exists():
            # Copy through a separate atomic write to keep a recoverable last version.
            old = json.loads(path.read_text(encoding="utf-8"))
            atomic_json(path.with_suffix(path.suffix + ".bak"), old)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@dataclass
class Shape:
    label: str
    points: list[list[float]]
    shape_type: str = "polygon"
    group_id: int | None = None
    flags: dict = field(default_factory=dict)
    description: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def weak(self):
        return self.shape_type in {"point", "line", "linestrip"} or bool(self.flags.get("weak", False))

    @property
    def background(self):
        return bool(self.flags.get("background", False))

    @property
    def uid(self):
        return self.extra.setdefault("contour_note_id", uuid.uuid4().hex)

    def to_dict(self):
        return {**copy.deepcopy(self.extra), "label": self.label,
                "points": [[float(x), float(y)] for x, y in self.points],
                "group_id": self.group_id, "shape_type": self.shape_type,
                "flags": dict(self.flags), "description": self.description}

    @classmethod
    def from_dict(cls, data):
        kind = data.get("shape_type", "polygon")
        if kind not in SHAPES:
            raise ValueError(f"暂不支持 {kind} 形状。原文件不会被覆盖，请使用多边形/点/线/框/圆。")
        pts = data.get("points", [])
        minimum = {"polygon": 3, "point": 1}.get(kind, 2)
        if len(pts) < minimum or (kind in {"rectangle", "circle", "line"} and len(pts) != 2):
            raise ValueError(f"{kind} 的点数无效")
        if not all(len(p) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in p) for p in pts):
            raise ValueError("标注坐标必须是有限数值")
        flags = data.get("flags") or {}
        if not all(isinstance(k, str) and isinstance(v, bool) for k, v in flags.items()):
            raise ValueError("Labelme flags 必须为布尔值")
        known = {"label", "points", "shape_type", "group_id", "flags", "description"}
        group_id = data.get("group_id")
        if group_id is not None and (not isinstance(group_id, int) or isinstance(group_id, bool)):
            raise ValueError("Labelme group_id 必须是整数或 null")
        if not isinstance(data.get("label"), str) or not data["label"].strip() or not isinstance(data.get("description") or "", str):
            raise ValueError("类别和描述必须是文本")
        return cls(data["label"], copy.deepcopy(pts), kind,
                   group_id, dict(flags), data.get("description") or "",
                   {k: copy.deepcopy(v) for k, v in data.items() if k not in known})


@dataclass
class Document:
    image: Path
    width: int
    height: int
    shapes: list[Shape] = field(default_factory=list)
    clinical: dict = field(default_factory=dict)  # Opaque compatibility data from old files.
    flags: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)

    def to_dict(self, target: Path | None = None):
        image_path = os.path.relpath(self.image, target.parent) if target else self.image.name
        return {**copy.deepcopy(self.extra), "version": "5.5.0", "flags": dict(self.flags),
                "shapes": [s.to_dict() for s in self.shapes], "imagePath": image_path,
                "imageData": None, "imageHeight": self.height, "imageWidth": self.width,
                **({"clinical": copy.deepcopy(self.clinical)} if self.clinical else {})}

    def snapshot(self):
        return copy.deepcopy((self.shapes, self.clinical, self.flags, self.extra))

    def restore(self, value):
        self.shapes, self.clinical, self.flags, self.extra = copy.deepcopy(value)


def load_document(image: Path, label: Path | None = None):
    with Image.open(image) as im:
        width, height = im.size
    doc = Document(image.resolve(), width, height)
    label = label or image.with_suffix(".json")
    if not label.exists():
        return doc
    data = json.loads(label.read_text(encoding="utf-8"))
    if data.get("imageWidth", width) != width or data.get("imageHeight", height) != height:
        raise ValueError("JSON 中的图像尺寸与当前图片不同，已停止加载以保护原标注。")
    doc.shapes = [Shape.from_dict(s) for s in data.get("shapes", [])]
    doc.clinical = copy.deepcopy(data.get("clinical") or {})
    doc.flags = data.get("flags") or {}
    if not isinstance(doc.flags, dict) or not all(isinstance(k, str) and isinstance(v, bool) for k, v in doc.flags.items()):
        raise ValueError("图像 flags 必须是布尔值字典")
    known = {"version", "flags", "shapes", "imagePath", "imageData", "imageHeight", "imageWidth", "clinical"}
    doc.extra = {k: v for k, v in data.items() if k not in known}
    return doc


def polygon_points(shape: Shape):
    if shape.shape_type == "polygon":
        return shape.points
    if shape.shape_type == "rectangle":
        (x1, y1), (x2, y2) = shape.points
        return [[min(x1, x2), min(y1, y2)], [max(x1, x2), min(y1, y2)],
                [max(x1, x2), max(y1, y2)], [min(x1, x2), max(y1, y2)]]
    if shape.shape_type == "circle":
        (cx, cy), edge = shape.points
        r = math.dist([cx, cy], edge)
        return [[cx + r * math.cos(i * math.tau / 96), cy + r * math.sin(i * math.tau / 96)] for i in range(96)]
    return []


def geometry(shape):
    pts = polygon_points(shape)
    return Polygon(pts) if len(pts) >= 3 else Polygon()


def simple_polygons(geom):
    """Partition holes into exact, hole-free polygons understood by Labelme."""
    if geom.is_empty:
        return []
    if geom.geom_type != "Polygon":
        return [p for g in getattr(geom, "geoms", []) for p in simple_polygons(g)]
    if not geom.interiors:
        return [geom] if geom.area > 0.01 else []
    result = []
    for triangle in triangulate(geom):
        intersection = triangle.intersection(geom)
        if intersection.geom_type == "Polygon" and not intersection.interiors:
            if intersection.area > 0.01:
                result.append(intersection)
        else:
            result.extend(simple_polygons(intersection))
    return result


def boolean_shapes(originals: list[Shape], cutter: Shape, operation: str, size):
    if not originals:
        raise ValueError("请先选择一个完整区域。")
    if any(s.weak or s.background or not polygon_points(s) for s in originals):
        raise ValueError("此操作只适用于完整区域，不能用于弱提示。")
    if len({s.label for s in originals}) != 1:
        raise ValueError("请先把要合并的区域改为相同类别。")
    base = unary_union([geometry(s) for s in originals])
    change = geometry(cutter)
    if not base.is_valid or not change.is_valid:
        raise ValueError("轮廓存在自交，请调整节点后再执行。")
    result = base.union(change) if operation == "add" else base.difference(change)
    result = result.intersection(box(0, 0, *size))
    group = originals[0].group_id if originals[0].group_id is not None else int(uuid.uuid4().hex[:12], 16)
    extra = copy.deepcopy(originals[0].extra)
    description = originals[0].description
    if any(s.extra != extra or s.description != description or s.flags != originals[0].flags for s in originals[1:]):
        extra["contour_note_sources"] = [s.to_dict() for s in originals]
    return [Shape(originals[0].label, [list(p) for p in list(g.exterior.coords)[:-1]],
                  group_id=group, flags=dict(originals[0].flags), description=description,
                  extra=copy.deepcopy(extra)) for g in simple_polygons(result)]


def draw_shape(draw, shape, value, point_radius=4, line_width=5):
    pts = [tuple(p) for p in shape.points]
    polygon = polygon_points(shape)
    if polygon:
        draw.polygon([tuple(p) for p in polygon], fill=value)
    elif shape.shape_type == "point":
        x, y = pts[0]
        draw.ellipse((x-point_radius, y-point_radius, x+point_radius, y+point_radius), fill=value)
    else:
        draw.line(pts, fill=value, width=line_width, joint="curve")


def category_map(documents):
    names = sorted({s.label for d in documents for s in d.shapes if not s.background})
    if len(names) > 254:
        raise ValueError("8 位语义 Mask 最多支持 254 类（0 背景，255 未知）。")
    return {name: i+1 for i, name in enumerate(names)}


def masks(doc, categories):
    full = [s for s in doc.shapes if not s.weak and not s.background]
    # A weak-only/unlabeled image must never silently become a negative image.
    initial = 0 if full else 255
    semantic = Image.new("L", (doc.width, doc.height), initial)
    weak = Image.new("L", (doc.width, doc.height), 255)
    for s in full:
        draw_shape(ImageDraw.Draw(semantic), s, categories[s.label])
    for s in [s for s in doc.shapes if s.weak]:
        draw_shape(ImageDraw.Draw(weak), s, 0 if s.background else categories[s.label])
    return semantic, weak


def validate_document(doc):
    issues = []
    for i, s in enumerate(doc.shapes, 1):
        if any(x < 0 or y < 0 or x > doc.width-1 or y > doc.height-1 for x, y in s.points):
            issues.append(f"标记 {i} 存在越界节点")
        if polygon_points(s):
            g = geometry(s)
            if not g.is_valid or g.area < 1:
                issues.append(f"标记 {i} 自交或面积过小")
    return issues


def export_dataset(documents: list[Document], destination: Path):
    """COCO instances + complete Labelme JSON + dense and sparse masks."""
    categories = category_map(documents)
    result = {"info": {"description": "ContourNote manual annotations", "version": "0.3.0"},
              "licenses": [], "images": [], "annotations": [],
              "categories": [{"id": cid, "name": name, "supercategory": "clinical"}
                             for name, cid in categories.items()]}
    weak_rows = []
    # Validate everything before creating a partial export.
    for doc in documents:
        issues = validate_document(doc)
        if issues:
            raise ValueError(f"{doc.image.name}: " + "；".join(issues))
    for image_id, doc in enumerate(documents, 1):
        stem = f"{image_id:05d}_{doc.image.stem}"
        image_name = f"{stem}{doc.image.suffix.lower()}"
        image_target = destination / "images" / image_name
        image_target.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(doc.image, image_target)
        label_target = destination / "labelme" / f"{stem}.json"
        clone = copy.deepcopy(doc)
        clone.image = image_target.resolve()
        atomic_json(label_target, clone.to_dict(label_target))
        result["images"].append({"id": image_id, "file_name": f"images/{image_name}",
                                 "width": doc.width, "height": doc.height})
        semantic, weak = masks(doc, categories)
        for folder, im in [("masks", semantic), ("weak_masks", weak)]:
            directory = destination / folder
            directory.mkdir(exist_ok=True)
            im.save(directory / f"{stem}.png")
        groups = {}
        for i, s in enumerate(doc.shapes):
            if s.weak:
                weak_rows.append({"image_id": image_id, **s.to_dict()})
            if s.background or s.shape_type in {"point", "line", "linestrip"}:
                continue
            if s.weak and s.shape_type != "rectangle":
                continue
            key = (s.label, str(s.group_id) if s.group_id is not None else f"shape-{i}", s.weak)
            groups.setdefault(key, []).append(s)
        for (label, _, is_weak), group in groups.items():
            geoms = [geometry(s).intersection(box(0, 0, doc.width, doc.height)) for s in group]
            combined = unary_union(geoms)
            if combined.is_empty or combined.area <= 0:
                continue
            x1, y1, x2, y2 = combined.bounds
            polygons = simple_polygons(combined)
            result["annotations"].append({
                "id": len(result["annotations"])+1, "image_id": image_id,
                "category_id": categories[label], "iscrowd": 0,
                "bbox": [x1, y1, x2-x1, y2-y1], "area": combined.area,
                "segmentation": [] if is_weak else [[c for p in list(g.exterior.coords)[:-1] for c in p] for g in polygons],
                "supervision": "bbox" if is_weak else "full"})
    atomic_json(destination / "annotations.json", result)
    atomic_json(destination / "weak_annotations.json", {"annotations": weak_rows})
    atomic_json(destination / "classes.json", {"background": 0, "ignore": 255, "classes": categories})
    return result
