#!/bin/zsh
set -e
cd -- "$(dirname -- "$0")"
for bundle in "./临绘 0.5.2.app" "../临绘 0.5.2.app" "./临绘 0.5.1.app" "../临绘 0.5.1.app" "./临绘 0.5.app" "../临绘 0.5.app" "./临绘 0.4.1.app" "../临绘 0.4.1.app" "./临绘 0.4.app" "../临绘 0.4.app" "./临绘 0.3.app" "../临绘 0.3.app" "./临绘.app" "../临绘.app" "./dist/ContourNote.app"; do
  if [[ -d "$bundle" ]]; then
    bundle_path="${bundle:A}"
    exec /usr/bin/open -n -a "$bundle_path" --args "$@"
  fi
done
if [[ -x .venv/bin/python ]]; then
  exec .venv/bin/python run.py "$@"
fi
if [[ -x ../clinical-annotator/.venv/bin/python ]]; then
  exec ../clinical-annotator/.venv/bin/python run.py "$@"
fi
echo '此目录是源码。请下载 macOS 直接运行版，解压后双击「临绘.app」。'
read -r '?按回车退出…'
exit 1
