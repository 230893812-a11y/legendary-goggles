# 坦克大战小游戏（GitHub Pages 网页版）

## 上传位置

将本文件夹内的全部文件直接上传到 GitHub 仓库根目录，必须能在根目录看到 `index.html`。

## GitHub Pages 设置

进入仓库 **Settings → Pages**，选择 **Deploy from a branch**，分支选 `main`，目录选 `/ (root)`，点击 **Save**。

发布地址通常为：

`https://230893812-a11y.github.io/expert-octo-carnival/`

## 文件说明

- `index.html`：网页启动入口
- `web_build.apk`：网页运行所需的游戏资源包（内含射击、爆炸音效）
- `web_build.tar.gz`：备用资源包
- `browserfs.min.js`：浏览器运行组件
- `favicon.png`：网页图标
- `.nojekyll`：避免 GitHub Pages 忽略资源文件

GitHub Pages 只能运行网页版本，不能直接运行 Windows 的 `.exe` 文件。
