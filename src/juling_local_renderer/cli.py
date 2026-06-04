from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


class RenderError(RuntimeError):
    pass


PACKAGE_TYPE = "juling-shortdrama-local-render"
CLI_VERSION = "0.2.0"


def require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError("FFmpeg was not found. Install FFmpeg and make sure it is available in PATH.")
    return ffmpeg


def safe_extract(zf: zipfile.ZipFile, work_dir: Path) -> None:
    root = work_dir.resolve()
    for member in zf.infolist():
        target = (work_dir / member.filename).resolve()
        if root != target and root not in target.parents:
            raise RenderError(f"Unsafe ZIP path: {member.filename}")
    zf.extractall(work_dir)


def load_package(zip_path: Path, work_dir: Path) -> dict:
    if not zip_path.exists():
        raise RenderError(f"Package not found: {zip_path}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        safe_extract(zf, work_dir)
    manifest_path = work_dir / "manifest.json"
    if not manifest_path.exists():
        raise RenderError("manifest.json is missing from the package")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def read_manifest(package_zip: Path) -> dict:
    if not package_zip.exists():
        raise RenderError(f"Package not found: {package_zip}")
    with zipfile.ZipFile(package_zip, "r") as zf:
        if "manifest.json" not in zf.namelist():
            raise RenderError("manifest.json is missing from the package")
        return json.loads(zf.read("manifest.json").decode("utf-8"))


def safe_filename(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip()).strip("._-")
    return text or "juling_render"


def package_summary(package_zip: Path) -> dict:
    manifest = read_manifest(package_zip)
    tracks = manifest.get("tracks") or []
    subtitles = manifest.get("subtitles") or []
    return {
        "package": str(package_zip),
        "valid_package_type": manifest.get("package_type") == PACKAGE_TYPE,
        "package_type": manifest.get("package_type") or "",
        "schema_version": manifest.get("schema_version") or "",
        "job_id": manifest.get("job_id") or "",
        "name": manifest.get("name") or "",
        "resolution": manifest.get("resolution") or "",
        "aspect_ratio": manifest.get("aspect_ratio") or "",
        "languages": [str(item.get("language")) for item in tracks if item.get("language")],
        "subtitle_languages": [str(item.get("language")) for item in subtitles if item.get("language")],
        "source_video": (manifest.get("source_video") or {}).get("path") or "source/source.mp4",
        "renderer_min_version": ((manifest.get("renderer") or {}).get("min_version") or ""),
    }


def validate_package(package_zip: Path, require_ffmpeg_check: bool = True) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    ffmpeg_path = ""
    if require_ffmpeg_check:
        ffmpeg_path = shutil.which("ffmpeg") or ""
        if not ffmpeg_path:
            errors.append("FFmpeg was not found in PATH")
    if not package_zip.exists():
        errors.append(f"Package not found: {package_zip}")
        return {"ok": False, "errors": errors, "warnings": warnings, "ffmpeg": ffmpeg_path}
    try:
        with zipfile.ZipFile(package_zip, "r") as zf:
            names = set(zf.namelist())
            if "juling_package.json" not in names:
                warnings.append("juling_package.json is missing; falling back to manifest.json")
            if "manifest.json" not in names:
                errors.append("manifest.json is missing")
                return {"ok": False, "errors": errors, "warnings": warnings, "ffmpeg": ffmpeg_path}
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            if manifest.get("package_type") and manifest.get("package_type") != PACKAGE_TYPE:
                errors.append(f"Unsupported package_type: {manifest.get('package_type')}")
            source_path = (manifest.get("source_video") or {}).get("path") or "source/source.mp4"
            if source_path not in names:
                errors.append(f"Source video is missing: {source_path}")
            tracks = manifest.get("tracks") or []
            if not tracks:
                errors.append("No language tracks found in manifest")
            for track in tracks:
                lang = str(track.get("language") or "")
                segments = track.get("segments") or []
                if not lang:
                    errors.append("A track is missing language")
                if not segments:
                    errors.append(f"No TTS audio segments found for language: {lang or 'unknown'}")
                for segment in segments:
                    audio_path = str(segment.get("audio_path") or "")
                    if not audio_path:
                        errors.append(f"Audio path is empty for language: {lang or 'unknown'}")
                    elif audio_path not in names:
                        errors.append(f"Audio segment is missing: {audio_path}")
            for item in manifest.get("subtitles") or []:
                subtitle = str(item.get("path") or "")
                if subtitle and subtitle not in names:
                    warnings.append(f"Subtitle file is missing: {subtitle}")
    except zipfile.BadZipFile:
        errors.append("Package is not a valid ZIP file")
    except json.JSONDecodeError as exc:
        errors.append(f"manifest.json is invalid JSON: {exc}")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "ffmpeg": ffmpeg_path}


def parse_resolution(value: str) -> tuple[int, int]:
    text = str(value or "720P").upper()
    if text == "1080P":
        return 1920, 1080
    return 1280, 720


def ratio_pair(value: str) -> tuple[int, int]:
    try:
        left, right = str(value or "16:9").split(":", 1)
        return max(int(left), 1), max(int(right), 1)
    except Exception:
        return 16, 9


def target_size(resolution: str, aspect_ratio: str) -> tuple[int, int]:
    base_w, base_h = parse_resolution(resolution)
    rw, rh = ratio_pair(aspect_ratio)
    if rw >= rh:
        width = base_w
        height = int(round(width * rh / rw))
    else:
        height = base_h
        width = int(round(height * rw / rh))
    width -= width % 2
    height -= height % 2
    return max(width, 2), max(height, 2)


def ffmpeg_escape(path: Path) -> str:
    text = path.as_posix().replace("'", "\\'")
    if sys.platform.startswith("win"):
        text = text.replace(":", "\\:")
    return text


def language_manifest(manifest: dict, lang: str) -> dict:
    for track in manifest.get("tracks") or []:
        if str(track.get("language") or "").lower() == lang.lower():
            return track
    raise RenderError(f"Language track not found: {lang}")


def subtitle_path(manifest: dict, lang: str, work_dir: Path) -> Path | None:
    for item in manifest.get("subtitles") or []:
        if str(item.get("language") or "").lower() == lang.lower():
            path = work_dir / str(item.get("path") or "")
            return path if path.exists() else None
    return None


def render_language(package_zip: Path, lang: str, output: Path, burn_subtitles: bool = True) -> None:
    ffmpeg = require_ffmpeg()
    with tempfile.TemporaryDirectory(prefix="juling_render_") as temp:
        work_dir = Path(temp)
        manifest = load_package(package_zip, work_dir)
        source_rel = manifest.get("source_video", {}).get("path") or "source/source.mp4"
        source = work_dir / source_rel
        if not source.exists():
            raise RenderError(f"Source video is missing: {source_rel}")
        track = language_manifest(manifest, lang)
        segments = track.get("segments") or []
        if not segments:
            raise RenderError(f"No TTS audio segments found for language: {lang}")

        inputs = ["-i", str(source)]
        audio_filters = []
        mix_labels = []
        for idx, segment in enumerate(segments, start=1):
            audio_path = work_dir / str(segment.get("audio_path") or "")
            if not audio_path.exists():
                raise RenderError(f"Audio segment is missing: {segment.get('audio_path')}")
            inputs.extend(["-i", str(audio_path)])
            delay_ms = max(int(round(float(segment.get("start_sec") or 0) * 1000)), 0)
            label = f"a{idx}"
            audio_filters.append(f"[{idx}:a]adelay={delay_ms}:all=1[{label}]")
            mix_labels.append(f"[{label}]")

        width, height = target_size(manifest.get("resolution"), manifest.get("aspect_ratio"))
        video_filter = f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1"
        sub_path = subtitle_path(manifest, lang, work_dir) if burn_subtitles else None
        if sub_path:
            video_filter += f",subtitles='{ffmpeg_escape(sub_path)}'"
        video_filter += "[v]"
        audio_filter = "".join(mix_labels) + f"amix=inputs={len(mix_labels)}:duration=longest:normalize=0[a]"
        filter_complex = ";".join(audio_filters + [audio_filter, video_filter])

        output.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            ffmpeg,
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output),
        ]
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise RenderError(proc.stderr.strip() or "FFmpeg render failed")


def manifest_languages(package_zip: Path) -> list[str]:
    manifest = read_manifest(package_zip)
    return [str(item.get("language")) for item in manifest.get("tracks") or [] if item.get("language")]


def default_output_path(package_zip: Path, lang: str, output_dir: Path | None = None) -> Path:
    manifest = read_manifest(package_zip)
    base = safe_filename(str(manifest.get("name") or manifest.get("job_id") or package_zip.stem))
    directory = output_dir or package_zip.parent
    return directory / f"{base}_{safe_filename(lang)}.mp4"


def print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_doctor(args: argparse.Namespace) -> int:
    package = Path(args.package).resolve() if args.package else None
    payload = {
        "cli_version": CLI_VERSION,
        "ffmpeg": shutil.which("ffmpeg") or "",
    }
    if package:
        payload["package"] = validate_package(package, require_ffmpeg_check=True)
        try:
            payload["summary"] = package_summary(package)
        except RenderError:
            payload["summary"] = {}
    payload["ok"] = bool(payload["ffmpeg"]) and (not package or payload["package"]["ok"])
    print_json(payload)
    return 0 if payload["ok"] else 2


def run_inspect(args: argparse.Namespace) -> int:
    package = Path(args.package).resolve()
    payload = package_summary(package)
    payload["validation"] = validate_package(package, require_ffmpeg_check=False)
    print_json(payload)
    return 0 if payload["validation"]["ok"] else 2


def run_render(args: argparse.Namespace) -> int:
    package_zip = Path(args.package).resolve()
    validation = validate_package(package_zip, require_ffmpeg_check=True)
    if not validation["ok"]:
        raise RenderError("; ".join(validation["errors"]))
    if args.all:
        output_dir = Path(args.output_dir).resolve()
        for lang in manifest_languages(package_zip):
            output = default_output_path(package_zip, lang, output_dir)
            render_language(package_zip, lang, output, burn_subtitles=not args.no_subtitles)
            print(f"Rendered {lang}: {output}")
        return 0
    if args.output:
        output = Path(args.output).resolve()
    else:
        output = default_output_path(package_zip, args.lang)
    render_language(package_zip, args.lang, output, burn_subtitles=not args.no_subtitles)
    print(f"Rendered {args.lang}: {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    command_names = {"doctor", "inspect", "render"}
    if raw_argv and raw_argv[0] not in command_names and not raw_argv[0].startswith("-"):
        legacy_parser = argparse.ArgumentParser(description="Render Juling local package to MP4")
        legacy_parser.add_argument("package", help="Path to local render package ZIP")
        legacy_group = legacy_parser.add_mutually_exclusive_group(required=True)
        legacy_group.add_argument("--lang", help="Language code to render, e.g. en")
        legacy_group.add_argument("--all", action="store_true", help="Render all languages")
        legacy_parser.add_argument("--output", help="Output MP4 path for --lang")
        legacy_parser.add_argument("--output-dir", default="exports", help="Output directory for --all")
        legacy_parser.add_argument("--no-subtitles", action="store_true", help="Do not burn subtitles")
        args = legacy_parser.parse_args(raw_argv)
        args.func = run_render
        try:
            return args.func(args)
        except RenderError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    parser = argparse.ArgumentParser(description="Render Juling local package to MP4")
    parser.add_argument("--version", action="version", version=f"juling-render {CLI_VERSION}")
    subparsers = parser.add_subparsers(dest="command")

    doctor_parser = subparsers.add_parser("doctor", help="Check FFmpeg and optionally validate a package")
    doctor_parser.add_argument("package", nargs="?", help="Optional local render package ZIP")
    doctor_parser.set_defaults(func=run_doctor)

    inspect_parser = subparsers.add_parser("inspect", help="Show package metadata and validation result")
    inspect_parser.add_argument("package", help="Path to local render package ZIP")
    inspect_parser.set_defaults(func=run_inspect)

    render_parser = subparsers.add_parser("render", help="Render package to MP4")
    render_parser.add_argument("package", help="Path to local render package ZIP")
    group = render_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--lang", help="Language code to render, e.g. en")
    group.add_argument("--all", action="store_true", help="Render all languages")
    render_parser.add_argument("--output", help="Output MP4 path for --lang; defaults to <job>_<lang>.mp4")
    render_parser.add_argument("--output-dir", default="exports", help="Output directory for --all")
    render_parser.add_argument("--no-subtitles", action="store_true", help="Do not burn subtitles")
    render_parser.set_defaults(func=run_render)

    args = parser.parse_args(raw_argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    try:
        return args.func(args)
    except RenderError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
