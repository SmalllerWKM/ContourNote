# ContourNote · 临绘

An offline manual image annotation workspace. Current version: **0.5.2**. Supports full regions, weak point/box/line/scribble cues, live Labelme-compatible JSON saving, COCO, and masks. No AI models or cloud inference are included.

[简体中文](README.zh-CN.md) · [Changelog (Chinese)](CHANGELOG.md) · [Current release notes](docs/releases/v0.5.2.md) · [Known issues](docs/KNOWN-ISSUES.md) · [Validation](docs/VALIDATION.md) · [MIT license](LICENSE)

> This is a trial build. Custom annotation directories can carry over between projects, and Windows cross-drive saving has a known path issue. Windows has not undergone native runtime acceptance testing. The application UI is Chinese; English documentation is not an English language pack.

![v0.5.2 workspace with a synthetic boundary-redraw draft; the record tab has been removed](docs/images/workspace-v0.5.2.png)

## Download and run

Check the repository's [Releases page](https://github.com/SmalllerWKM/ContourNote/releases) for assets actually published by the maintainer. Local build records do not imply that release assets have been uploaded.

| Platform | Runtime archive | Launch |
|---|---|---|
| macOS Apple Silicon arm64 | 临绘-macOS-Apple芯片-v0.5.2.zip | Extract and open 临绘 0.5.2.app |
| Windows x64 | ContourNote-Windows-x64-v0.5.2.zip | Extract everything, open CN, run 临绘.exe |
| Developer source | ContourNote-GitHub-source-v0.5.2.zip | Create an environment and install dependencies |

Runtime packages include Python and Qt. Keep the Windows runtime and app directories beside the EXE. The Mac package is ad-hoc signed, not Apple Developer signed or notarized. No Intel Mac, Windows ARM64, or Linux standalone package is provided.

## Current workflow

1. Open an image directory, image, or supported Labelme JSON. Add your own labels; none are predefined.
2. Use A for a polygon, B for a box, or P for a point. Choose full regions or weak foreground/background cues as appropriate.
3. Click vertices or hold Shift and drag with the left mouse button. New polygons can close near their start, with right-click, or with Enter.
4. Use E to edit. Drag a node, or click an edge to add and drag a node. Double-click an existing polygon node/edge to start redrawing.
5. **Click another point on the original boundary to confirm the redraw.** Hovering or dragging near it does not confirm. Select the retained region from the blue/orange preview.
6. A notice can be dismissed without discarding the draft. Esc cancels; Ctrl+Z undoes. Tab toggles Edit/Polygon while the canvas has focus.

The old add/merge/subtract controls and cut-mode checkbox were removed in 0.5.0. The record page and generated judgment, confidence, review, quality, and note fields were removed in 0.5.2.

## Field of view and persistence

The optional view detector uses radial luminance profiles, adaptive fade rejection, robust angular processing, and an inset. Defaults are 4 original-image pixels and 35% rejection strength. A cyan dashed contour previews the result. Out-of-view samples project to the nearest contour segment; nearby interior samples can also snap. Detection can be inaccurate under unusual optics, occlusion, or very dark images; inspect the preview or disable it.

Accepted annotation vertices are stored individually without polynomial fitting or contour simplification. Default spacing is 8 screen pixels, adjustable from 2 to 40.

Autosave is enabled by default and can be disabled. Complete edits save immediately; draft/drag writes are throttled at approximately 220 ms. Actual modification times, external-change notices, previous-version .json.bak files, and draft recovery are provided. A completion checkmark does not prove the latest changes are on disk.

Large-project label/status indexing runs in the background. Frame-copy tools only copy coordinates between equal-sized images and require manual review. F5 controls an optional 0.1-120 second/image slideshow.

## Formats

Supported Labelme shapes: polygon, rectangle, circle, point, line, and linestrip. Other extensions such as mask and oriented_rectangle are not supported.

Exports contain image copies, editable Labelme JSON, annotations.json for COCO regions/detection boxes, weak_annotations.json, masks/, weak_masks/, and classes.json. Weak boxes have empty COCO segmentation arrays and a custom supervision field; points and lines are stored separately from COCO instances.

Masks use 0 for background, 1-254 for foreground classes, and 255 for unknown/ignore. With no full region, the semantic mask is unknown. In 0.5.2, legacy clinical metadata is preserved opaquely and no longer controls validation or background-mask generation. Always read the mapping from the same export.

## Shortcuts

E Edit · A Polygon · B Box · P Point · L Line · G Scribble · C Circle · H Pan · Tab Edit/Polygon · F Fit · 1 100% · F11 Fullscreen · W/D Previous/Next · F5 Slideshow · Ctrl+S Save · Ctrl+Z Undo.

On macOS, Ctrl combinations normally map to Command. Input fields keep their editing behavior. Press F1 for more shortcuts.

## Development and verification

Python 3.10+ is required. From the project root:

```sh
python -m venv .venv
# macOS / Linux
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python run.py
# Windows
.venv\Scripts\python.exe -m pip install -e ".[test]"
.venv\Scripts\python.exe run.py
```

The local v0.5.2 record is 75 passing tests plus a native frozen Mac startup/save/export/render check. Windows validation is static. An optional upstream Labelme reference test is skipped when that external checkout is absent. These checks do not establish clinical accuracy or quantified annotation efficiency.

For manual GitHub publication, see the [upload guide (Chinese)](docs/GITHUB-MANUAL-UPLOAD.zh-CN.md). Original source is MIT-licensed; dependencies retain their own licenses. Labelme is an external interaction/format reference; see [NOTICE](NOTICE.md).
