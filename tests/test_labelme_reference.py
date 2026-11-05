"""Execute the upstream validators in place; no upstream code is vendored."""
import ast
import math
from pathlib import Path
import typing

import numpy as np
import pytest

from clinical_annotator.data import Shape


def test_output_shapes_pass_original_labelme_validators():
    upstream = Path(__file__).resolve().parents[2] / "labelme" / "labelme"
    source = upstream / "_label_file.py"
    model = upstream / "_shape" / "_model.py"
    if not source.exists():
        pytest.skip("Optional external Labelme reference repository is unavailable")
    namespace = {"typing": typing, "math": math, "np": np, "cast": typing.cast,
                 "Literal": typing.Literal, "TypeAlias": typing.TypeAlias, "ShapeDict": dict,
                 "Final": typing.Final, "_SINGLE_CHANNEL_NDIM": 2}
    alias = next(n for n in ast.parse(model.read_text()).body if isinstance(n, ast.AnnAssign) and getattr(n.target, "id", "") == "ShapeType")
    names = {"_validate_flags", "_validate_shape_semantics", "_load_shape_json_obj"}
    funcs = [n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name in names]
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), alias] + funcs, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(source), "exec"), namespace)
    for shape in [Shape("神经", [[1, 1], [5, 1], [5, 5]], group_id=2),
                  Shape("神经", [[1, 1], [5, 5]], "rectangle", flags={"weak": True}),
                  Shape("神经", [[3, 3]], "point", flags={"weak": True}),
                  Shape("神经", [[1, 1], [5, 5]], "line"),
                  Shape("神经", [[1, 1], [3, 3], [5, 5]], "linestrip"),
                  Shape("血管", [[5, 5], [8, 8]], "circle")]:
        loaded = namespace["_load_shape_json_obj"](shape_json_obj=shape.to_dict())
        assert loaded["shape_type"] == shape.shape_type
