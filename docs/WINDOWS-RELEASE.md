# Windows x64 便携包

当前：0.5.2。文件 `ContourNote-Windows-x64-v0.5.2.zip`，完整解压后进入 `CN` 文件夹，双击 `临绘.exe`。保留旁边的 `runtime` 和 `app`，不要单独复制 EXE。无需另装 Python。

内置 CPython 3.13.17、PySide6 Essentials、shiboken6、NumPy、Pillow、Shapely；版本和原始依赖校验和见运行包中的 build-manifest.json。启动器是实际 x64 GUI EXE，使用随包解释器。

自 0.3.0-winfix1 起移除未使用的 QML 深层资源，顶层目录缩为 CN，最长包内路径从 192 降至 108 UTF-16 单位；构建器限制相对路径不超过 120 单位。仍应避免特别深的解压目录。

包已进行 ZIP、短路径和 123 项 PE 递归依赖审计，**尚未 Windows 实机启动验收**。跨盘符保存仍有已知异常，不能将静态检查写作 Windows 运行成功。

Python 层启动错误日志位于 `%LOCALAPPDATA%\ContourNote\startup.log`。可选运行 `临绘.exe --self-test 输出目录` 做本机自检；未实际运行前不要预先标记成功。

重建参考 `tools/build_windows_portable.py`，需准备其中固定的官方 Python ZIP 和五个 Windows wheel，以及 ziglang、pefile。功能变化见 [日志](../CHANGELOG.md)，当前限制见 [已知问题](KNOWN-ISSUES.md)。
