# Juling 本地渲染器

Juling 本地渲染器用于把“翻译配音智能体”导出的本地渲染素材包，转换成可播放的 MP4 视频。

你不需要把视频上传到服务器渲染。下载素材包后，在自己的电脑上运行本工具即可生成配音版视频。

## 普通用户请先看这里

如果你是从 GitHub 页面右上角 `Code -> Download ZIP` 下载的文件夹，例如：

```text
juling-local-renderer-main
```

这只是源码包，不是普通用户直接使用的版本。

Windows 普通用户请到 Releases 下载 `juling-render-gui.exe`：

[下载 Windows 图形版渲染器](https://github.com/sankewang/juling-local-renderer/releases/latest)

不要下载 GitHub 自动生成的 `Source code (zip)` 或 `Source code (tar.gz)`。

下载后，双击打开 `juling-render-gui.exe`：

1. 点击“选择素材包”，选择剧灵绘AI漫剧平台导出的“本地渲染素材包 ZIP”
2. 选择输出文件夹
3. 点击“检查素材包”
4. 点击“开始渲染”
5. 渲染完成后点击“打开输出文件夹”查看 MP4

如果你更熟悉命令行，也可以下载 `juling-render.exe` 使用 CLI：

```powershell
.\juling-render.exe doctor .\package.zip
.\juling-render.exe render .\package.zip --all --output-dir .\exports
```

## 适用场景

- 从剧灵绘AI漫剧平台网站（[www.julinghui.com](https://www.julinghui.com)）下载了“本地渲染素材包 ZIP”
- 想在本地电脑生成最终 MP4
- 想按不同语言分别导出视频
- 想静音源视频原声，只保留目标语言 TTS 配音
- 想把字幕烧录进视频

## 使用前准备

### 1. 下载本工具

到 GitHub Releases 页面下载与你电脑系统匹配的文件：

- Windows 普通用户：下载 `juling-render-gui.exe`
- Windows 命令行用户：下载 `juling-render.exe`
- macOS：下载 `juling-render`
- Linux：下载 `juling-render`

如果暂时没有 Releases，可以从 GitHub Actions 的构建产物里下载对应系统的 artifact。

### 2. 安装 FFmpeg

本工具依赖 FFmpeg 处理视频和音频。

Windows 用户建议下载 `ffmpeg-master-latest-win64-gpl.zip` 或稳定版 `ffmpeg-release-full.7z`，解压后把 `bin` 目录加入系统 `PATH`。

安装完成后，在命令行检查：

```bash
ffmpeg -version
```

如果能看到版本号，说明 FFmpeg 已经可用。

## Windows 图形界面使用

适合大多数用户，不需要输入命令。

### 1. 打开工具

双击 `juling-render-gui.exe`。

### 2. 选择素材包

点击“选择素材包”，选择从剧灵绘AI漫剧平台网站（[www.julinghui.com](https://www.julinghui.com)）下载的“本地渲染素材包 ZIP”。

素材包不需要解压。

### 3. 选择输出文件夹

默认会输出到素材包旁边的 `exports` 文件夹，也可以手动选择其他文件夹。

### 4. 开始渲染

点击“检查素材包”，确认通过后点击“开始渲染”。

如果素材包有多个目标语言，可以保持“渲染全部语言”勾选；如果只想渲染一个语言，取消勾选后选择指定语言。

## 命令行使用

假设你已经从剧灵绘AI漫剧平台网站（[www.julinghui.com](https://www.julinghui.com)）下载了素材包：

```text
shortdrama_xxx_package.zip
```

### 检查素材包

```bash
juling-render doctor shortdrama_xxx_package.zip
```

这个命令会检查素材包里是否包含源视频、音频、字幕和时间轴文件。

### 渲染单个语言

例如渲染英文版本：

```bash
juling-render render shortdrama_xxx_package.zip --lang en --output result_en.mp4
```

常见语言代码：

- `zh`：中文
- `en`：英语
- `ja`：日语
- `ko`：韩语
- `fr`：法语
- `de`：德语
- `it`：意大利语
- `es`：西班牙语
- `pt`：葡萄牙语
- `ru`：俄语

### 渲染全部语言

如果素材包里有多个目标语言，可以一次性全部导出：

```bash
juling-render render shortdrama_xxx_package.zip --all --output-dir ./exports
```

生成的视频会放到 `exports` 文件夹里。

### 不烧录字幕

如果只想生成配音版，不想把字幕压到画面里：

```bash
juling-render render shortdrama_xxx_package.zip --lang en --output result_en.mp4 --no-subtitles
```

## Windows 使用说明

如果你下载的是 `juling-render.exe`，可以把素材包和 exe 放在同一个文件夹里，然后在该文件夹打开 PowerShell：

```powershell
.\juling-render.exe doctor .\shortdrama_xxx_package.zip
.\juling-render.exe render .\shortdrama_xxx_package.zip --lang en --output .\result_en.mp4
```

如果你已经把 `juling-render.exe` 所在目录加入系统 `PATH`，就可以直接使用：

```powershell
juling-render render shortdrama_xxx_package.zip --lang en --output result_en.mp4
```

## 素材包要求

Juling 网站下载的素材包可以直接使用，不需要解压，也不要修改里面的文件名。

素材包内通常包含：

- `juling_package.json`
- `manifest.json`
- `source/source.mp4`
- `audio/{语言}/segment_001.mp3`
- `subtitles/{语言}.srt`
- `segments.json`

本工具会根据素材包里的时间轴，把每一句 TTS 配音放到对应位置，并导出最终 MP4。

## 常见问题

### 提示找不到 `ffmpeg`

说明 FFmpeg 没有安装，或者没有加入系统 `PATH`。请先执行：

```bash
ffmpeg -version
```

确认命令可用后再重新渲染。

### 提示找不到 `juling-render`

说明当前命令行找不到本工具。

Windows 可以使用完整文件名运行：

```powershell
.\juling-render.exe --help
```

macOS/Linux 可以使用：

```bash
./juling-render --help
```

### 渲染后没有声音

请先检查素材包：

```bash
juling-render doctor shortdrama_xxx_package.zip
```

如果提示缺少音频文件，需要回到 Juling 网站重新生成本地渲染素材包。

### 字幕没有显示

确认没有使用 `--no-subtitles`。如果素材包缺少对应语言的 SRT 文件，也不会烧录字幕。

## 给开发者

普通用户不需要阅读本节。

如果你要从源码运行：

```bash
git clone https://github.com/sankewang/juling-local-renderer.git
cd juling-local-renderer
python -m pip install -e .
juling-render --help
```

运行测试：

```bash
python -m pip install -e ".[dev]"
python -m pytest tests -q
```

