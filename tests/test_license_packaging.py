"""Guard actual license payloads and the release's Qt runtime boundary."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_licenses", ROOT / "tools/package_licenses.py")
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


def test_copyleft_license_texts_and_original_attributions_are_available():
    licenses = ROOT / "licenses"
    assert "GNU LESSER GENERAL PUBLIC LICENSE" in (licenses / "LGPL-3.0-only.txt").read_text()
    assert "GNU GENERAL PUBLIC LICENSE" in (licenses / "GPL-3.0-only.txt").read_text()
    for item in json.loads((licenses / "manifest.json").read_text()):
        path = licenses / item["file"]
        assert path.is_relative_to(licenses)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]


def test_license_bundle_is_copied_into_portable_distribution(tmp_path):
    package.copy_licenses(tmp_path)
    assert (tmp_path / "THIRD_PARTY_NOTICES.md").is_file()
    assert (tmp_path / "licenses/LGPL-3.0-only.txt").is_file()
    assert (tmp_path / "licenses/REPLACING-LIBRARIES.md").is_file()
    assert (tmp_path / "licenses/sources.json").is_file()


def test_mac_pruning_removes_unused_plugin_and_framework_but_preserves_widgets(tmp_path):
    framework = tmp_path / "Contents/Frameworks"
    framework.mkdir(parents=True)
    (framework / "QtWidgets").write_text("retained")
    removed = framework / "QtPdf.framework/Versions/A"
    removed.mkdir(parents=True)
    (removed / "QtPdf").write_text("unused")
    (framework / "QtPdf").symlink_to("QtPdf.framework/Versions/A/QtPdf")
    (framework / "libqpdf.dylib").write_text("unused")
    package.prune_macos(tmp_path)
    assert (framework / "QtWidgets").read_text() == "retained"
    assert not (framework / "QtPdf.framework").exists()
    assert not (framework / "QtPdf").is_symlink()
    assert not (framework / "libqpdf.dylib").exists()


def test_in_app_license_viewer_can_display_lgpl_text(qt_app, monkeypatch):
    from PySide6.QtWidgets import QComboBox, QDialog, QTextBrowser
    from clinical_annotator.app import MainWindow
    observed = []
    def inspect(dialog):
        choices = dialog.findChild(QComboBox)
        choices.setCurrentIndex(choices.findText("LGPL-3.0-only.txt"))
        observed.extend(widget.toPlainText() for widget in dialog.findChildren(QTextBrowser))
        return 0
    monkeypatch.setattr(QDialog, "exec", inspect)
    window = MainWindow()
    try:
        window.licenses_button.click()
    finally:
        window.close()
    assert any("GNU LESSER GENERAL PUBLIC LICENSE" in value for value in observed)
