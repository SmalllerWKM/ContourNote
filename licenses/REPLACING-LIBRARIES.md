# Library replacement and rebuilding / 替换库与重新构建

Package revision: v0.5.2-licensefix1. Application version: 0.5.2.

## Obtain source

Download the application source and `ContourNote-third-party-sources-v0.5.2-licensefix1.zip`
from the same GitHub Release. Verify each archive against `sources.json`.
The source bundle contains complete upstream release archives for PySide6 /
Shiboken6 6.12.0, Qt Base / SVG / Image Formats 6.12.0 and GEOS 3.14.1.
The archives include upstream build scripts, documentation and license notices.
No library source patches are applied by ContourNote.

## Preferred route: run or rebuild from source

1. Extract the ContourNote source and create a Python virtual environment
   (Mac arm64: Python 3.12; Windows x64: Python 3.13 for the supplied runtime).
2. Build the desired compatible Qt 6.12 libraries using their included CMake
   instructions. Use the same OS, architecture and compiler ABI as your runtime.
3. Build PySide6 / Shiboken6 from the supplied `pyside-setup` archive against
   your Qt installation, following that archive's README and build instructions.
   Install those bindings into the virtual environment. Build/install compatible
   GEOS and Shapely if replacing the geometry library as well.
4. Install the remaining project dependencies and run `python run.py`. The
   application source does not restrict loading compatible replacement libraries.
5. To make a standalone Mac app, run `python tools/build_macos.py` in that
   environment. For Windows, place compatible wheels and the embedded Python
   archive in `build/windows`, update the pinned build inputs, and run
   `python tools/build_windows_portable.py` on an appropriate build environment.
   The Windows cross-build launcher additionally needs the documented Zig and
   pefile build dependencies. Runtime validation must be performed on Windows.

## Direct replacement in portable packages

- Windows: keep a backup; replace the relevant ABI-compatible DLLs/PYDs in
  `CN/runtime/Lib/site-packages/PySide6`, `shiboken6` or `shapely.libs` together.
  Keep plugin versions compatible with the Qt libraries. Python remains at
  `CN/runtime`; the application source is in `CN/app`.
- Mac: Qt frameworks and extension modules are inside the app's
  `Contents/Frameworks/PySide6` and related directories; resources may contain
  symlinks to them. Keep their install names and relative paths compatible.
  Changing a signed bundle invalidates its existing signature. Rebuild from
  source, or sign your own modified copy with your own valid signing setup;
  the local build script uses `codesign --sign -` for an ad-hoc signature.
  Do not disable system security protections to run a modified app.

The source/rebuild route is recommended when changing Qt/Python ABI. These are
instructions for exercising library replacement rights, not a promise that an
arbitrary binary replacement will work.

## 中文说明

对应源码随同一 Release 免费提供，源文件、官方来源和哈希见 `sources.json`。
可以在自己的开发环境重新编译 Qt、PySide6/Shiboken6、GEOS，并让临绘使用兼容的
替换库；也可以先直接运行公开的临绘 Python 源码。Windows 为便携目录，Mac 为
应用包内的动态库；替换时需保持平台、架构、ABI、插件版本及相对路径一致。
修改 Mac 应用包会使原签名失效，需重新构建或自行签名，不需要关闭系统安全机制。
保留一份原应用副本，并用合成图像验证打开、绘制、JSON 保存及导出。

上述修改、替换、重新链接和相应调试逆向权利，以适用 LGPL 条文为准，临绘不额外限制。
