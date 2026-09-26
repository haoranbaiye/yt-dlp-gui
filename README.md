# yt-dlp GUI

基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp 的图形界面视频下载器。推送代码到 GitHub 后自动构建 Windows 单文件 EXE，下载后双击即可运行，**无需安装 Python、FFmpeg 或任何依赖**。

## 功能

- 支持 YouTube 及数千个视频网站
- 多种画质选择：最佳画质 / 1080p / 720p / 480p / 仅音频 MP3
- 实时下载进度条 + 速度 + 剩余时间
- 自定义保存目录，一键打开下载文件夹
- 内置 FFmpeg，自动合并音视频、转码 MP3
- 下载在后台线程运行，界面不卡顿

## 如何获取 EXE（零开发环境）

### 方式一：推送到 GitHub 自动构建（推荐）

1. 在 GitHub 新建一个仓库（比如叫 `yt-dlp-gui`）
2. 把本项目所有文件上传到该仓库
3. 推送后，GitHub Actions 会自动开始构建（约 3-5 分钟）
4. 构建完成后：
   - 每次 push 到 `main`：在 Actions 页面的 Artifacts 里下载 `yt-dlp-GUI-windows`
   - 打 tag（如 `v1.0.0`）：自动创建 GitHub Release，EXE 直接附在 Release 里

### 触发 Release 版本

在本地或 GitHub 网页上打一个 tag：

```bash
git tag v1.0.0
git push origin v1.0.0
```

或者在 GitHub 仓库的 **Releases → Draft a new release** 里创建，tag 填 `v1.0.0`。

## 使用方法

1. 双击 `yt-dlp-GUI.exe`
2. 粘贴视频链接
3. 选择画质和保存目录
4. 点击「开始下载」

## 项目结构

```
├── main.py                  # GUI 主程序（tkinter + yt-dlp API）
├── requirements.txt         # Python 依赖
├── .gitignore
├── README.md
└── .github/
    └── workflows/
        └── build.yml        # GitHub Actions 自动构建配置
```

## 技术说明

- **GUI**: Python tkinter（Python 内置，无需额外依赖）
- **下载核心**: yt-dlp Python 库嵌入
- **打包**: PyInstaller --onefile --noconsole
- **FFmpeg**: CI 构建时自动下载并打包进 EXE，运行时自动解压
- **构建环境**: GitHub Actions windows-latest + Python 3.11

## 本地开发（可选）

```bash
pip install -r requirements.txt
pip install pyinstaller
python main.py
```

## License

本项目 GUI 代码为 MIT License。yt-dlp 为 Unlicense，FFmpeg 为 LGPL/GPL。
