# juling-local-renderer

Local FFmpeg renderer for Juling translation/dubbing packages.

## Requirements

- Python 3.10+
- FFmpeg available in `PATH`

## Local development install

This project is independent from `juling-ai-agent`. Do not install it into the website backend virtual environment.

Windows:

```powershell
cd D:\juling\juling-local-renderer
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\juling-render.exe --help
```

Development test dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest tests -q
```

macOS/Linux:

```bash
cd ~/juling-local-renderer
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e .
./.venv/bin/juling-render --help
```

Optional Windows convenience for the current terminal:

```powershell
$env:PATH = "D:\juling\juling-local-renderer\.venv\Scripts;$env:PATH"
juling-render --help
```

## Usage

Check a downloaded Juling package:

```bash
juling-render inspect shortdrama_xxx_package.zip
juling-render doctor shortdrama_xxx_package.zip
```

Render one language:

```bash
juling-render render input.zip --lang en --output result_en.mp4
```

Render all languages in the package:

```bash
juling-render render input.zip --all --output-dir ./exports
```

Disable hard subtitles:

```bash
juling-render render input.zip --lang en --output result_en.mp4 --no-subtitles
```

Older command format is still supported:

```bash
juling-render input.zip --all --output-dir ./exports
```

## Package contract

The ZIP must contain:

- `juling_package.json`
- `manifest.json`
- `source/source.mp4`
- `audio/{lang}/segment_001.mp3`
- `subtitles/{lang}.srt`
- `segments.json`

The renderer validates the package, removes source audio, places TTS segments on the manifest timeline, optionally burns subtitles, and exports MP4.

Downloaded packages from Juling are designed to work directly with this CLI. Do not unzip or rename internal files.
