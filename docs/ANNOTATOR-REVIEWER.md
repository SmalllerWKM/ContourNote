# 标注者与审查修改者 / Annotator and reviewing editor

临绘将初次标注与审查修改视为两类使用流程，使用同一套图像坐标和 Labelme JSON。
“选择编辑”让审查者沿用已完成的标注，直接修正局部；不必为了一个错误节点删除整个区域。

| 使用者 | 主要操作 | 已有结果如何处理 |
|---|---|---|
| 标注者 | A 画完整多边形；B/P/L/G 添加框、点、线或涂鸦弱提示；Shift＋左键连续采点 | 建立初始标注，自定义类别，保存 JSON 后交接 |
| 审查修改者 | E 选择编辑，拖动已有节点；单击边线增加节点；双击节点或边线开始局部重画 | 在原轮廓上修正，保留所选区域与其他未修改标注 |

## 审查修改的操作

1. 点击“打开标注”，读取标注者交接的 JSON 和对应图像。
2. 按 E 进入“选择编辑”，选中需要修正的已有多边形。
3. 小范围修正：拖动节点；需要增加控制点时单击边线。
4. 更换一段边界：双击原节点或边线开始，逐点或 Shift＋左键画新边界。
5. **单击原轮廓另一处边线确认终点**，按蓝/橙预览选择需要保留的区域。
6. 检查保存状态及文件修改时间，再交接或导出。

这里的“保留”指选择重画后的候选区域，不是自动为初标和复核保存两个历史版本。
自动保存默认写入当前 JSON，`.json.bak` 只保留上一版；如需同时保留初标与复核成果，
请在交接前复制完整项目到独立工作目录，并保持图像与 JSON 的相对位置。

当前没有账户登录、人员权限、审查通过状态、人员追溯或多人同时编辑合并系统。
两类使用者是操作分工，不是新增“记录”页面，也不重新加入已删除的审核表单。

## English

ContourNote supports an initial annotator and a reviewing editor through a shared
image coordinate system and editable Labelme JSON. These are workflow roles,
not accounts or permission levels.

The annotator creates polygons or weak box/point/line/scribble cues. The reviewer
opens the existing JSON and presses **E** to adjust nodes or redraw part of an
existing boundary. Double-click a node/edge to start, draw the replacement path,
then **click another point on the original boundary** and choose the retained
region from the two previews. Other annotations remain available for editing.

Autosave updates the current JSON; one `.json.bak` is a previous-file backup,
not a review history. Duplicate the complete project into a separate working
directory before handoff if both the initial and reviewed datasets must be kept.
There is no user identity, approval status, audit trail or simultaneous-edit merge.
