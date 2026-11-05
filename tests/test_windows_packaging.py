"""Regression guard for Explorer extraction, independent of a Windows host."""
import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "windows_package", Path(__file__).resolve().parents[1] / "tools" / "build_windows_portable.py"
)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


def test_archive_path_budget_reserves_destination():
    paths = ["CN/临绘.exe", "CN/" + "a" * 117]
    audit = package.archive_path_audit(paths)
    assert audit["max_relative_utf16_units"] == 120
    assert audit["legacy_max_destination_utf16_units"] == 138


def test_long_path_fails_before_publication():
    with pytest.raises(RuntimeError, match="too long"):
        package.archive_path_audit(["CN/" + "a" * 118])


def test_windows_counts_non_bmp_characters_as_two_units():
    with pytest.raises(RuntimeError, match="too long"):
        package.archive_path_audit(["CN/" + "\U0001f600" * 59])
