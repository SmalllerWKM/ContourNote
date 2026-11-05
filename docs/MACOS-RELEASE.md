# macOS Apple 芯片运行包

当前：0.5.2。文件 `临绘-macOS-Apple芯片-v0.5.2.zip`，解压后双击 `临绘 0.5.2.app`。内置 Python、Qt、NumPy、Pillow、Shapely，无需创建 .venv。

仅提供 arm64。包经过本地 ad-hoc 签名完整性检查及原生启动、JSON 保存、COCO 导出、窗口渲染检查，未使用 Apple 开发者证书签名或公证。不要将其描述为经过临床验证或稳定性完整验收。

工具 `tools/build_macos.py` 用于从 Mac 重建应用；`--self-test OUTPUT` 是可选自检参数，常规启动不执行测试。

历史版本的功能变化见 [更新日志](../CHANGELOG.md)，当前操作见 [0.5.2 说明](releases/v0.5.2.md)，风险见 [已知问题](KNOWN-ISSUES.md)。
