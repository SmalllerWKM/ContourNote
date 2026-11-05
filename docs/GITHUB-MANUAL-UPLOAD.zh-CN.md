# 手动上传 GitHub

目标项目：https://github.com/SmalllerWKM/ContourNote

本资料只在本地整理，没有自动上传或创建 GitHub Release。推荐先发布当前 **0.5.2 试用版**；十个历史节点先通过 CHANGELOG 展示即可。

## 1. 上传仓库文件

1. 解压 `ContourNote-GitHub-upload-v0.5.2.zip`，进入其中的 `仓库文件`。
2. GitHub 仓库点击 **Add file → Upload files**。
3. 拖入 `仓库文件`里面的内容，保留 clinical_annotator、tests、tools、docs、demo 的目录结构。根目录应直接有 README.md、README.zh-CN.md、CHANGELOG.md、pyproject.toml，不要额外套一层“仓库文件”。
4. 注意隐藏的 `.gitignore` 也要上传；Finder 可用 Command＋Shift＋句号显示隐藏文件。没有带上时可从“Add file → Create new file”创建同名文件并复制内容。
5. 提交标题可写：`Prepare ContourNote v0.5.2 source and changelog`。
6. 提交后打开 CHANGELOG.md 和 docs/images/workspace-v0.5.2.png，确认日志与配图可读。

仓库文件均按普通网页上传大小准备。GitHub 当前网页上传限制是单文件 25 MiB、一次最多 100 个文件，超出数量时分批；不要把 Mac/Windows 运行 ZIP 放进此处。[官方上传说明](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)

若远端已有改动，请先比对再替换；网页上传同名文件会产生覆盖提交。本地整理没有读取或合并远端的新改动。

## 2. 发布 0.5.2 Release

1. 仓库进入 **Releases → Draft a new release / Create a new release**。
2. 新建标签 `v0.5.2`，Target 选择刚才上传源码的 main 提交。
3. 标题使用 `Release文案/v0.5.2.md` 第一行；正文复制该文件第一行之后的内容。
4. 当前仍有已知问题且 Windows 未实机验收，建议勾选 **Pre-release**。Git 标签仍可使用 v0.5.2，无需修改应用版本。
5. 在 **Attach binaries / 上传附件** 区域上传 `发布附件/v0.5.2` 中的四个文件：Mac ZIP、Windows ZIP、GitHub 源码 ZIP、SHA256SUMS.txt。
6. 检查附件已完成上传，再发布。发布后确认两个运行包可以下载；Windows 需要在实机补验，不能仅凭上传成功改写验证状态。

运行包应使用 Releases 分发，避免将大型二进制作为普通仓库文件跟踪。[官方大文件说明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)

GitHub 自动生成的“Source code”ZIP是标签对应仓库的源码，不是包含 Python/Qt 的可直接运行应用。手动附加的运行包应保留明确平台名称。

## 3. 历史版本怎么放

CHANGELOG.md 已包含 0.1.0、0.2.0、0.2.1、0.3.0、0.3.0-winfix1、0.4.0、0.4.1、0.5.0、0.5.1、0.5.2。

每版有独立 Markdown 文案，在 `Release文案` 和仓库的 `docs/releases`。历史资产位置/大小/哈希见 `历史资产清单.csv`，不必把所有旧运行包都重新上传。

若确实要创建历史 Releases，先把相应历史源码作为独立提交导入，再为那个提交建对应标签。**不要把所有旧标签都指向最新 main**，否则 GitHub 自动生成的旧版源码会错误地变成 0.5.2。

0.2.1 目前只核实到 Mac 运行包，没有单独源码包；不伪造历史源码提交。0.3.0-winfix1 是 Windows 包修订，应用版本仍为 0.3.0，标签可用 `v0.3.0-winfix1`。

## 4. 上传前最后核对

- README 显示 0.5.2、没有记录页和已删除运算入口的现用说明。
- 已知跨项目保存目录和 Windows 跨盘问题如实保留。
- Windows 写为“尚未实机验收”，不改成“验证通过”。
- 本地完成日期和 GitHub 实际发布日期分开，不把 CHANGELOG 日期当作已公开发布证明。
- 不上传 .venv、build、dist、.app 文件夹、运行日志或真实标注数据；提供的仓库文件已排除这些内容。

本地校验和可在 Mac 用 `shasum -a 256 文件名`，Windows PowerShell 用 `Get-FileHash -Algorithm SHA256 文件名`，再与 SHA256SUMS.txt 比对。
