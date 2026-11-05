# 临绘 · ContourNote

本地人工图像标注工具，当前版本 **0.5.2**。支持完整轮廓与点、框、线、涂鸦等弱提示，自动保存 Labelme 兼容 JSON，并导出 COCO、语义 Mask 和弱提示 Mask。没有 AI 模型或云端推理。

[English](README.md) · [完整更新日志](CHANGELOG.md) · [当前版本说明](docs/releases/v0.5.2.md) · [各版 Release 文案](docs/releases/README.md) · [已知问题](docs/KNOWN-ISSUES.md) · [验证范围](docs/VALIDATION.md) · [MIT](LICENSE)

> 当前作为试用版本提供。跨项目自定义保存目录和 Windows 跨盘保存存在已知问题；Windows 包尚未实机验收。中英文文档不代表英文界面，软件界面目前为中文。

![0.5.2 工作台：已移除记录页，示例为合成图像中的边界重画草稿](docs/images/workspace-v0.5.2.png)

## 下载与启动

请在项目 [Releases 页面](https://github.com/SmalllerWKM/ContourNote/releases) 查看维护者实际已发布的附件；本地构建记录不代表附件已上传。

| 平台 | 当前运行包 | 启动方式 |
|---|---|---|
| Mac Apple 芯片 arm64 | 临绘-macOS-Apple芯片-v0.5.2.zip | 解压后双击“临绘 0.5.2.app” |
| Windows x64 | ContourNote-Windows-x64-v0.5.2.zip | 完整解压，进入 CN，双击“临绘.exe” |
| 开发源码 | ContourNote-GitHub-source-v0.5.2.zip | 创建 Python 环境后运行 |

运行包包含 Python、Qt 和依赖，无需自行创建 .venv。Windows 请保留 EXE 旁边的 runtime 和 app 文件夹，避免深层解压路径。Mac 包为本地 ad-hoc 签名，未做 Apple 开发者证书签名或公证。目前没有 Intel Mac、Windows ARM64 或 Linux 独立运行包。

## 五步开始

1. 打开图片目录、单张图片或已有 Labelme JSON。目录不递归扫描，支持 PNG、JPEG、BMP、TIFF、WebP。
2. 输入自己的类别并回车，或点击“＋”。不预设前景类别，导入时收集已有类别。
3. A 绘制多边形，B 画框，P 标点；右侧区分完整区域与弱提示、前景与背景。
4. 左键逐点点击，或 Shift＋左键拖动采点。新建多边形支持接近起点自动闭合，也可右键或 Enter 完成。
5. 检查保存状态与修改时间，然后导出。demo/ 是合成演示，不是真实病例。

## 选择编辑与边界重画

- E 进入选择编辑；单击节点拖动，单击边线可添加并拖动节点。
- 双击已有完整多边形节点或边线开始重画，逐点或 Shift＋左键描绘新边界。
- **点击原轮廓另一处边线才确认终点**，随后按蓝、橙预览选择保留区域。仅靠近、悬停、经过或拖动经过不会自动弹窗。
- 无效路径会保留草稿并说明原因；黄色提示条可“关闭提示”，不会丢弃草稿。Esc 取消，绘制中 Ctrl＋Z 撤回一点。
- Tab 在画布内切换选择编辑与多边形；输入框内保留正常 Tab 行为。

补画/合并/扣除入口和“折线切分”开关已在 0.5.0 移除。0.5.2 没有“记录”页面，也不再生成判断、置信度、审核、质量或备注。历史行为查阅更新日志。

## 有效视野边界

针对圆形等带暗色填充的视野，使用径向亮度、渐变阈值及角向稳健处理。默认内收 4 原图像素、剔除强度 35%，绘制设置可调整或关闭。青色虚线表示检测结果。

吸附开启且检测成功时，无效区落点投影到最近有效边线；有效区内距边缘 10 屏幕像素内也可吸附。该约束不等于裁剪整个形状面积，已有轮廓仍需人工核对。偏心、多个视野、遮挡或极暗图像可能检测不准。

采样间距默认 8 屏幕像素，可调 2-40 px。**实际接受的标注顶点逐点保存，不做多项式拟合或轮廓简化。** 视野检测结果会复用，改变设置或切图时重新计算。

## 保存、图片列表与连续帧

自动保存默认开启，可关闭；手动保存为 Ctrl＋S。显示真实文件修改时间，内容未变时不重写 JSON。绘制/拖动保存约 220 ms 节流，未完成路径保存在 .contour-drafts/；覆盖保存保留上一版 .json.bak。实时保存不保证断电零丢失。

外部修改会提示冲突，需重新载入或确认覆盖。已标注图片显示勾选，但勾选不代替磁盘保存状态；0.5.2 以形状或 Labelme flags 判定，不再以旧记录字段判定。

大项目的类别和勾选后台索引，切帧不全量重扫。上一帧、下一帧、复制和向后 N 帧传播在顶部；帧复用只复制坐标，不跟踪运动，来源与目标尺寸需一致。图片放映在菜单中，可设 0.1-120 秒/张，F5 开始/暂停。

## 数据兼容与导出

Labelme 兼容类型：polygon、rectangle、circle、point、line、linestrip。未支持 mask、oriented_rectangle 等扩展形状；Labelme 不会自动理解临绘的弱提示语义。

| 文件/目录 | 含义 |
|---|---|
| images/、labelme/ | 图片副本与可继续编辑的 Labelme JSON |
| annotations.json | COCO 完整区域或弱检测框，附加 supervision 字段 |
| weak_annotations.json | 点、线、涂鸦及其他弱提示 |
| masks/、weak_masks/ | 完整区域语义 Mask 与弱提示 Mask |
| classes.json | 本次导出的类别映射 |

Mask 约定：0 背景，1-254 前景类别，255 未知/忽略。没有完整区域时语义 Mask 为 255，弱标注不等于负样本。旧 clinical 字段原样透传，但 0.5.2 不再用其中“无目标”自动生成全背景 Mask。类别编号可能随类别集合改变，始终读取同次 classes.json。

弱框 COCO segmentation 为空，只能作为检测提示；点、线等在独立弱提示文件中，不冒充精确分割真值。

## 快捷键

| 操作 | 快捷键 |
|---|---|
| 编辑 / 多边形 / 框 / 点 | E / A / B / P |
| 线 / 涂鸦 / 圆 / 小手 | L / G / C / H |
| 编辑与多边形切换 | Tab（画布有焦点时） |
| 采点 / 完成 / 取消 | Shift＋左键 / 右键或 Enter / Esc |
| 上一帧 / 下一帧 | W 或方向左/上 / D 或方向右/下 |
| 适应 / 100% / 全屏 | F / 1 / F11 |
| 保存 / 撤销 / 重做 | Ctrl＋S / Ctrl＋Z / Ctrl＋Y 或 Ctrl＋Shift＋Z |
| 放映开始或暂停 | F5 |

Mac 的 Ctrl 组合通常对应 Command，Alt 对应 Option。更多按键按 F1 查阅。

## 开发与验证

需要 Python 3.10+，在项目根目录执行：

```sh
python -m venv .venv
# macOS / Linux
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python run.py
# Windows
.venv\Scripts\python.exe -m pip install -e ".[test]"
.venv\Scripts\python.exe run.py
```

```sh
# macOS 开发环境中的无窗口测试
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

本地 0.5.2 测试记录为 75 项通过，Mac 独立应用保存/导出/渲染通过；Windows 仅静态包与依赖检查。外部 Labelme 对照测试在没有参考仓库时会跳过，数量可能不同。详见 [验证说明](docs/VALIDATION.md)。

## 发布与许可证

[手动上传步骤](docs/GITHUB-MANUAL-UPLOAD.zh-CN.md)说明仓库文件与 Release 附件如何放置。历史日志不表示历史版本已在 GitHub 发布。

独立源码采用 MIT，依赖遵循各自许可证。Labelme 为交互与格式参考，没有将其应用源码或图标复制进本项目。见 [NOTICE](NOTICE.md)。
