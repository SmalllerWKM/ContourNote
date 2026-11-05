import copy
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from pycocotools.coco import COCO
from shapely.ops import unary_union

from clinical_annotator.data import (Document, Shape, atomic_json, boolean_shapes,
    category_map, export_dataset, geometry, load_document, masks, validate_document)


def document(tmp_path, name="病例.png"):
    path = tmp_path / name
    Image.new("RGB", (100, 80), "#53667a").save(path)
    return Document(path, 100, 80)


def square(label="神经", weak=False):
    return Shape(label, [[10, 10], [70, 10], [70, 60], [10, 60]], flags={"weak": weak})


def test_labelme_roundtrip_preserves_metadata_and_unknown_fields(tmp_path):
    doc = document(tmp_path)
    doc.shapes = [square(), Shape("神经", [[15, 20]], "point", flags={"weak": True})]
    doc.shapes[0].extra["custom_source"] = "manual"
    doc.extra["legacy_project"] = "example"
    doc.clinical.update(presence="present", risks=["边界不清"], note="复核")
    path = tmp_path / "labels" / "病例.json"
    atomic_json(path, doc.to_dict(path))
    raw = json.loads(path.read_text())
    assert (path.parent / raw["imagePath"]).resolve() == doc.image.resolve()
    loaded = load_document(doc.image, path)
    assert loaded.snapshot() == doc.snapshot()
    assert loaded.extra["legacy_project"] == "example"
    assert raw["imageData"] is None and raw["version"] == "5.5.0"


def test_atomic_failure_keeps_previous_file(tmp_path, monkeypatch):
    import clinical_annotator.data as module
    target = tmp_path / "label.json"
    atomic_json(target, {"value": 1})
    monkeypatch.setattr(module.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        atomic_json(target, {"value": 2})
    assert json.loads(target.read_text()) == {"value": 1}
    assert not list(tmp_path.glob("*.tmp"))


def test_backup_and_nonfinite_values(tmp_path):
    path = tmp_path / "case.json"
    atomic_json(path, {"old": True})
    atomic_json(path, {"new": True}, backup=True)
    assert json.loads(path.with_suffix(".json.bak").read_text()) == {"old": True}
    with pytest.raises(ValueError):
        atomic_json(path, {"bad": float("nan")})
    assert json.loads(path.read_text()) == {"new": True}


@pytest.mark.parametrize("kind,pts", [("mask", [[0, 0], [2, 2]]), ("point", []),
    ("polygon", [[1, 2], [3, 4]]), ("line", [[1, 1], [2, 2], [3, 3]]),
    ("point", [[float("inf"), 2]])])
def test_rejects_unsupported_or_invalid_shapes(kind, pts):
    with pytest.raises(ValueError):
        Shape.from_dict({"shape_type": kind, "label": "a", "points": pts})


def test_size_mismatch_does_not_overwrite(tmp_path):
    doc = document(tmp_path)
    target = doc.image.with_suffix(".json")
    raw = doc.to_dict()
    raw["imageWidth"] = 200
    atomic_json(target, raw)
    with pytest.raises(ValueError):
        load_document(doc.image)
    assert json.loads(target.read_text())["imageWidth"] == 200


def test_sparse_prompts_never_become_dense_gt(tmp_path):
    doc = document(tmp_path)
    doc.shapes = [Shape("神经", [[20, 20]], "point", flags={"weak": False}),
                  Shape("神经", [[30, 30], [60, 60]], "rectangle", flags={"weak": True})]
    semantic, weak = masks(doc, category_map([doc]))
    assert np.all(np.asarray(semantic) == 255)
    assert np.asarray(weak)[20, 20] == 1
    assert np.asarray(weak)[0, 0] == 255
    doc.clinical["presence"] = "absent"
    doc.shapes.clear()
    semantic, _ = masks(doc, {})
    assert np.all(np.asarray(semantic) == 255)  # Removed record fields no longer define a negative image.


def test_foreground_and_background_prompts(tmp_path):
    doc = document(tmp_path)
    doc.shapes = [Shape("神经", [[10, 10], [60, 60]], "rectangle", flags={"weak": True}),
                  Shape("背景", [[30, 30]], "point", flags={"weak": True, "background": True})]
    _, weak = masks(doc, category_map([doc]))
    assert np.asarray(weak)[30, 30] == 0
    assert np.asarray(weak)[20, 20] == 1


def test_subtract_hole_has_exact_geometry_and_remains_labelme_polygons(tmp_path):
    doc = document(tmp_path)
    outer = square()
    inner = Shape("神经", [[25, 25], [45, 25], [45, 45], [25, 45]])
    result = boolean_shapes([outer], inner, "subtract", (99, 79))
    assert all(s.shape_type == "polygon" for s in result)
    assert len({s.group_id for s in result}) == 1
    union = unary_union([geometry(s) for s in result])
    assert union.area == pytest.approx(2600)
    assert union.symmetric_difference(geometry(outer).difference(geometry(inner))).area < 1e-8
    doc.shapes = result
    semantic, _ = masks(doc, category_map([doc]))
    assert np.asarray(semantic)[35, 35] == 0
    assert np.asarray(semantic)[15, 15] == 1


def test_coco_export_loads_with_official_api(tmp_path):
    doc = document(tmp_path)
    doc.shapes = [square(), Shape("器械", [[75, 10], [95, 40]], "rectangle", flags={"weak": True}),
                  Shape("神经", [[40, 40]], "point", flags={"weak": True}),
                  Shape("神经", [[20, 20], [35, 30], [50, 40]], "linestrip", flags={"weak": True})]
    doc.clinical["presence"] = "present"
    dest = tmp_path / "export"
    result = export_dataset([doc], dest)
    coco = COCO(str(dest / "annotations.json"))
    assert len(coco.imgs) == 1 and len(coco.anns) == 2
    full = next(a for a in result["annotations"] if a["supervision"] == "full")
    sparse = next(a for a in result["annotations"] if a["supervision"] == "bbox")
    assert coco.annToMask(full).shape == (80, 100)
    assert coco.annToMask(full).sum() == 3000
    assert full["area"] == 3000
    assert sparse["segmentation"] == [] and sparse["bbox"] == [75, 10, 20, 30]
    assert len(json.loads((dest / "weak_annotations.json").read_text())["annotations"]) == 3
    label = next((dest / "labelme").glob("*.json"))
    assert (label.parent / json.loads(label.read_text())["imagePath"]).exists()
    assert len(load_document(next((dest / "images").iterdir()), label).shapes) == 4


def test_same_stems_export_to_distinct_names(tmp_path):
    first = document(tmp_path, "case.png")
    second = document(tmp_path, "case.jpg")
    export_dataset([first, second], tmp_path / "out")
    assert len(list((tmp_path / "out" / "images").iterdir())) == 2


def test_grouped_fragments_form_one_coco_instance(tmp_path):
    doc = document(tmp_path)
    a = square(); a.group_id = 1
    b = Shape("神经", [[75, 10], [90, 10], [90, 25], [75, 25]], group_id=1)
    doc.shapes = [a, b]
    result = export_dataset([doc], tmp_path / "out")
    assert len(result["annotations"]) == 1
    assert len(result["annotations"][0]["segmentation"]) == 2


def test_geometry_validation_ignores_removed_record_controls(tmp_path):
    doc = document(tmp_path)
    doc.clinical["presence"] = "absent"  # Opaque legacy metadata cannot block edits.
    doc.shapes = [square()]
    assert not validate_document(doc)
    doc.clinical["presence"] = "present"
    doc.shapes = [Shape("神经", [[0, 0], [50, 50], [0, 50], [50, 0]])]
    assert validate_document(doc)
