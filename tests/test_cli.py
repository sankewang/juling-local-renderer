import json
import zipfile

from juling_local_renderer.cli import default_output_path, manifest_languages, package_summary, target_size, validate_package


def test_target_size_vertical():
    assert target_size("720P", "9:16") == (404, 720)


def test_target_size_horizontal():
    assert target_size("1080P", "16:9") == (1920, 1080)


def make_package(path):
    manifest = {
        "schema_version": "1.0",
        "package_type": "juling-shortdrama-local-render",
        "job_id": "job-1",
        "name": "Demo Task",
        "source_video": {"path": "source/source.mp4"},
        "resolution": "720P",
        "aspect_ratio": "16:9",
        "tracks": [
            {
                "language": "en",
                "segments": [
                    {"index": 0, "audio_path": "audio/en/segment_001.mp3", "start_sec": 0.5}
                ],
            }
        ],
        "subtitles": [{"language": "en", "path": "subtitles/en.srt", "format": "srt"}],
    }
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("juling_package.json", json.dumps({"manifest_path": "manifest.json"}))
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("segments.json", "[]")
        zf.writestr("source/source.mp4", b"video")
        zf.writestr("audio/en/segment_001.mp3", b"audio")
        zf.writestr("subtitles/en.srt", "1\n00:00:00,000 --> 00:00:01,000\nhello\n")


def test_package_summary_and_languages(tmp_path):
    package = tmp_path / "package.zip"
    make_package(package)
    assert manifest_languages(package) == ["en"]
    summary = package_summary(package)
    assert summary["valid_package_type"] is True
    assert summary["languages"] == ["en"]


def test_validate_package_without_ffmpeg(tmp_path):
    package = tmp_path / "package.zip"
    make_package(package)
    result = validate_package(package, require_ffmpeg_check=False)
    assert result["ok"] is True
    assert result["errors"] == []


def test_default_output_path_uses_job_name(tmp_path):
    package = tmp_path / "package.zip"
    make_package(package)
    assert default_output_path(package, "en").name == "Demo_Task_en.mp4"
