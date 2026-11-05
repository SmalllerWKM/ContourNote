# 参考来源

ContourNote 的交互需求来自本工作区提供的医生标注功能梳理，以及 Labelme 的公开交互设计和文件格式：

- Labelme：https://github.com/wkentaro/labelme
- 本地对照提交：df1abb53226f9a5b3b0d45b28e5211d81ffbc6ce
- Labelme 上游许可证：GPL-3.0-only。其仓库作为外部参考保留在上级目录，没有打包进本项目。
- Qt 文档：https://doc.qt.io/qtforpython-6/
- COCO 数据约定：https://cocodataset.org/#format-data

本项目的画布、数据模型、导出器、界面与测试为独立编写，没有复制 Labelme 的应用源码、图标、布局资源；MIT 许可证仅覆盖本项目独立源码。

可选的参考兼容性测试从本机 Labelme 仓库临时读取校验函数执行，不将该函数源代码复制到发布包。

运行依赖为 PySide6、Pillow、NumPy、Shapely；验证依赖包括 pytest 和 pycocotools。各依赖的许可证由其发行包提供，未包含 AI 模型或权重。

许可证修订版的完整第三方说明见 THIRD_PARTY_NOTICES.md；许可证全文、对应源码来源和替换库说明位于 licenses/，应用内“开源许可”可读取。独立源码的 MIT 不覆盖第三方库。
