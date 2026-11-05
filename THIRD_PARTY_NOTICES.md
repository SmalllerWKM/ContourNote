# Third-party components / 第三方组件

ContourNote's independently written application code is MIT-licensed. This does
not relicense bundled libraries. Their original copyright notices, licenses,
exceptions, and third-party attributions remain applicable.

临绘的独立应用源码采用 MIT；下列依赖、字体/编解码等附属组件保留各自许可证。
`licenses/manifest.json` 将短文件名映射到上游原始路径；许可证内容保持原文。

| Component | Distributed version | License / source |
|---|---|---|
| PySide6 Essentials, Shiboken6 | 6.12.0 | LGPL-3.0; alternative licenses retained in upstream notices. `pyside-setup` source archive |
| Qt Core, GUI, Widgets and retained supporting libraries | 6.12.0 | LGPL-3.0; third-party notices and exceptions apply. `qtbase`, `qtsvg`, `qtimageformats` source archives |
| Shapely | 2.2.0 | BSD-3-Clause; https://github.com/shapely/shapely/tree/2.2.0 |
| GEOS, bundled by Shapely | 3.14.1 | LGPL-2.1; `geos-3.14.1.tar.bz2` |
| NumPy | 2.5.4 | BSD-3-Clause and bundled component licenses; https://github.com/numpy/numpy/tree/v2.5.4 |
| Pillow | 13.0.0 | MIT-CMU and bundled component notices; https://github.com/python-pillow/Pillow/tree/13.0.0 |
| CPython (Mac / Windows) | 3.12.16 / 3.13.17 | PSF and included licenses; https://github.com/python/cpython |
| PyInstaller bootloader (Mac) | 6.22.3 | GPL-2.0-or-later with bootloader exception; see bundled license |

## Corresponding source / 对应源码

The `v0.5.2-licensefix1` release provides
`ContourNote-third-party-sources-v0.5.2-licensefix1.zip` alongside the application
downloads, without an access charge. It contains the original Qt/PySide6/GEOS
source archives, the origin URLs and SHA-256 hashes in `sources.json`, and build
and library replacement instructions. The distributed libraries are unmodified
upstream binaries; this package revision removes unused modules/plugins.

在与应用相同的 [GitHub Releases 页面](https://github.com/SmalllerWKM/ContourNote/releases/tag/v0.5.2-licensefix1)
免费提供对应源码附件。`licenses/sources.json` 记录版本、官方来源和校验值。
临绘自身源码和构建脚本位于同版本源码附件及仓库标签。

## User rights / 用户权利

Recipients may modify and replace the LGPL libraries, rebuild/relink the
application with compatible replacements, and reverse-engineer the application
for debugging those modifications, as allowed by the applicable licenses.
ContourNote imposes no additional restriction on those rights. See
`licenses/LGPL-3.0-only.txt`, `licenses/GPL-3.0-only.txt`, the included GEOS
license, and `licenses/REPLACING-LIBRARIES.md`.

用户可以依照相应许可证修改、替换和重新链接 LGPL 库，并为调试这些修改进行
必要的逆向工程。临绘不附加限制这些权利的条款。

## Labelme reference / Labelme 参考

Labelme is an external interaction and JSON-format reference. It is not a
runtime dependency and its application code/icons are not included in these
packages. An optional development test reads validators from a separately
obtained local Labelme checkout; that checkout retains its GPLv3 license.
See `NOTICE.md`. This notice is not a claim that Labelme endorses ContourNote.

## Scope

This file documents the inspected release components; it is not a legal opinion
or a claim that all future dependency combinations are compliant. Re-run the
package inventory and preserve the corresponding source when rebuilding.
